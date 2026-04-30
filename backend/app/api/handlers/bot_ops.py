from __future__ import annotations

from ...contracts import build_row, release_request_row, run_row
from .common import *
from .common import _require_permission
from ...whatsapp import resolve_whatsapp_access_token
from ...whatsapp_connection_state import decorate_whatsapp_number


def _release_security_ready(release: dict, policy: dict) -> bool:
    checklist = from_json(release.get("checklist_json"), {})
    required = ["validation_ok", "diff_reviewed", "observability_ready", "rollback_ready", "security_reviewed", "authz_tests_passed", "secrets_hardened", "audit_ready"]
    return all(bool(checklist.get(key)) for key in required)

def validate_bot_draft(bot_id: str, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        bot = get_bot(conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        ensure_bot_access(user, bot)
        _require_permission(user, bot["organization_id"], "release.request")
        config = from_json(bot["config_draft_json"], {})
        current_version = fetch_one(conn, "SELECT * FROM bot_versions WHERE id = ?", (bot.get("published_version_id"),)) if bot.get("published_version_id") else None
        return {
            "bot_id": bot_id,
            "validation": validate_bot_config(config),
            "against_published": diff_configs(from_json(current_version["config_json"], {}) if current_version else {}, config),
        }

def bot_versions_diff(
    bot_id: str,
    left_version_id: str | None = Query(default=None),
    right_version_id: str | None = Query(default=None),
    compare_to: str = Query(default="draft"),
    user: dict = Depends(get_current_user),
) -> dict:
    with get_connection() as conn:
        bot = get_bot(conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        ensure_bot_access(user, bot)
        left_version = fetch_one(conn, "SELECT * FROM bot_versions WHERE id = ? AND bot_id = ?", (left_version_id, bot_id)) if left_version_id else fetch_one(conn, "SELECT * FROM bot_versions WHERE id = ?", (bot.get("published_version_id"),)) if bot.get("published_version_id") else None
        if compare_to == "draft":
            right_config = from_json(bot["config_draft_json"], {})
            right_label = "draft"
        else:
            if not right_version_id:
                raise HTTPException(status_code=400, detail="right_version_id is required when compare_to=version")
            right_version = fetch_one(conn, "SELECT * FROM bot_versions WHERE id = ? AND bot_id = ?", (right_version_id, bot_id))
            if not right_version:
                raise HTTPException(status_code=404, detail="Right version not found")
            right_config = from_json(right_version["config_json"], {})
            right_label = right_version_id
        return {
            "bot_id": bot_id,
            "left_version_id": left_version["id"] if left_version else None,
            "right_label": right_label,
            "diff": diff_configs(from_json(left_version["config_json"], {}) if left_version else {}, right_config),
        }

def list_bot_builds(bot_id: str, user: dict = Depends(get_current_user)) -> list[dict]:
    with get_connection() as conn:
        bot = get_bot(conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        ensure_bot_access(user, bot)
        rows = fetch_all(conn, "SELECT * FROM bot_builds WHERE bot_id = ? ORDER BY created_at DESC", (bot_id,))
        return [build_row(row) for row in rows]

def get_release_requests(bot_id: str, user: dict = Depends(get_current_user)) -> list[dict]:
    with get_connection() as conn:
        bot = get_bot(conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        ensure_bot_access(user, bot)
        return [release_request_row(row) for row in list_release_requests(conn, bot_id=bot_id)]

def create_release_request_route(bot_id: str, payload: ReleaseRequestCreate, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        bot = get_bot(conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        ensure_bot_access(user, bot)
        _require_permission(user, bot["organization_id"], "release.request")
        config = from_json(bot["config_draft_json"], {})
        validation = validate_bot_config(config)
        readiness = release_readiness(conn, organization_id=bot["organization_id"], bot_id=bot["id"])
        if not bool(((readiness or {}).get("summary") or {}).get("can_publish_release")):
            raise HTTPException(status_code=400, detail={"message": "Release readiness blocked publish", "readiness": readiness})
        previous_version = fetch_one(conn, "SELECT * FROM bot_versions WHERE id = ?", (bot.get("published_version_id"),)) if bot.get("published_version_id") else None
        diff_summary = diff_configs(from_json(previous_version["config_json"], {}) if previous_version else {}, config)
        release = create_release_request(
            conn,
            organization_id=bot["organization_id"],
            bot_id=bot_id,
            requested_by=user["id"],
            title=payload.title or f"Release for {bot['name']}",
            notes=payload.notes,
            validation=validation,
            diff_summary=diff_summary,
        )
        create_audit_log(conn, organization_id=bot["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="release_request", entity_id=release["id"], action="release.requested", metadata={"bot_id": bot_id, "validation_ok": validation["ok"]})
        return release_request_row(release)

def approve_release_request_route(release_id: str, payload: ReleaseApprovalRequest, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        row = fetch_one(conn, "SELECT * FROM release_requests WHERE id = ?", (release_id,))
        if not row:
            raise HTTPException(status_code=404, detail="Release request not found")
        ensure_org_access(user, row["organization_id"])
        _require_permission(user, row["organization_id"], "release.approve")
        policy = get_security_policy(conn, organization_id=row["organization_id"])
        if bool(int(policy.get("require_dual_approval_releases", 1))) and row.get("requested_by") == user["id"]:
            raise HTTPException(status_code=403, detail="Requester cannot approve their own release")
        if not _release_security_ready(row, policy):
            raise HTTPException(status_code=400, detail="Security checklist must be complete before approval")
        approved = approve_release_request(conn, release_id=release_id, approved_by=user["id"], note=payload.note)
        create_audit_log(conn, organization_id=row["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="release_request", entity_id=release_id, action="release.approved", metadata={"note": payload.note, "dual_approval_required": bool(int(policy.get("require_dual_approval_releases", 1)))})
        return release_request_row(approved)

def publish_release_request_route(release_id: str, payload: PublishRequest, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        release = fetch_one(conn, "SELECT * FROM release_requests WHERE id = ?", (release_id,))
        if not release:
            raise HTTPException(status_code=404, detail="Release request not found")
        ensure_org_access(user, release["organization_id"])
        _require_permission(user, release["organization_id"], "release.publish")
        if release["status"] != "approved":
            raise HTTPException(status_code=400, detail="Release must be approved before publish")
        policy = get_security_policy(conn, organization_id=release["organization_id"])
        if not _release_security_ready(release, policy):
            raise HTTPException(status_code=400, detail="Release security gates are incomplete")
        bot = get_bot(conn, release["bot_id"])
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        config = from_json(bot["config_draft_json"], {})
        validation = validate_bot_config(config)
        if not validation["ok"]:
            raise HTTPException(status_code=400, detail={"message": "Draft validation failed", "validation": validation})
        previous_version = fetch_one(conn, "SELECT * FROM bot_versions WHERE id = ?", (bot.get("published_version_id"),)) if bot.get("published_version_id") else None
        version = publish_version(conn, bot_id=bot["id"], actor_user=user, notes=payload.notes or release.get("notes") or "Published from approved release")
        diff_summary = diff_configs(from_json(previous_version["config_json"], {}) if previous_version else {}, config)
        build = record_bot_build(conn, organization_id=bot["organization_id"], bot_id=bot["id"], version_id=version["id"], validation=validation, diff_summary=diff_summary, config=config)
        published_release = publish_release_request(conn, release_id=release_id, version_id=version["id"])
        create_audit_log(conn, organization_id=bot["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="release_request", entity_id=release_id, action="release.published", metadata={"version_id": version["id"], "security_gates": from_json(release.get("checklist_json"), {})})
        return {"release": release_request_row(published_release), "version": version, "build": build_row(build), "bot": _bot_payload(conn, get_bot(conn, bot["id"]))}

def bot_release_readiness(bot_id: str, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        bot = get_bot(conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        ensure_bot_access(user, bot)
        return release_readiness(conn, organization_id=bot["organization_id"], bot_id=bot_id)

def bot_traceability(bot_id: str, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        bot = get_bot(conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        ensure_bot_access(user, bot)
        versions = list_bot_versions(conn, bot_id)
        builds = fetch_all(conn, "SELECT * FROM bot_builds WHERE bot_id = ? ORDER BY created_at DESC LIMIT 20", (bot_id,))
        releases = list_release_requests(conn, bot_id=bot_id)
        runs = fetch_all(conn, "SELECT id, version_id, status, trace_id, execution_id, created_at FROM execution_runs WHERE bot_id = ? ORDER BY created_at DESC LIMIT 20", (bot_id,))
        return {
            "bot": {"id": bot["id"], "name": bot["name"], "published_version_id": bot.get("published_version_id")},
            "versions": versions,
            "builds": [build_row(row) for row in builds],
            "releases": [release_request_row(row) for row in releases],
            "runs": [run_row(row) for row in runs],
        }


def _simulation_predict(config: dict, scenario_text: str) -> dict:
    scenario = str(scenario_text or '').lower()
    objective = str((((config or {}).get('identity') or {}).get('primary_objective') or '')).lower()
    forbidden_topics = [str(item).lower() for item in (((config or {}).get('behavior') or {}).get('forbidden_topics') or [])]
    tone = str((((config or {}).get('behavior') or {}).get('tone') or '')).lower() or str((((config or {}).get('identity') or {}).get('tone') or '')).lower()
    action = 'reply'
    queue = 'soporte'
    must_escalate = False
    confidence = 55
    why = []
    if any(keyword in scenario for keyword in ['humano', 'asesor', 'persona', 'queja', 'reclamo', 'demanda']):
        action = 'handoff'
        queue = 'soporte'
        must_escalate = True
        confidence = 88
        why.append('Se detectó solicitud de humano o queja explícita.')
    elif any(keyword in scenario for keyword in ['cita', 'agenda', 'agendar', 'reprogram', 'consulta']):
        action = 'schedule'
        queue = 'agenda'
        confidence = 84
        why.append('El escenario contiene intención de agenda o cita.')
    elif any(keyword in scenario for keyword in ['pagar', 'pago', 'anticipo', 'factura', 'cobro']):
        action = 'payment'
        queue = 'cobranza'
        confidence = 82
        why.append('El escenario toca cobro o pago.')
    elif any(keyword in scenario for keyword in ['precio', 'promocion', 'promo', 'cotizacion', 'comprar', 'plan']):
        action = 'sell'
        queue = 'ventas'
        confidence = 78
        why.append('El escenario contiene señal comercial.')
    elif objective in {'vender', 'calificar', 'reactivar'}:
        action = 'sell'
        queue = 'ventas'
        confidence = 66
        why.append('Se usó el objetivo principal del bot para inclinar la acción.')
    if any(topic and topic in scenario for topic in forbidden_topics):
        must_escalate = True
        action = 'handoff'
        queue = 'soporte'
        confidence = min(confidence, 72)
        why.append('El escenario toca un tema prohibido del bot.')
    return {
        'predicted_action': action,
        'predicted_queue': queue,
        'must_escalate': must_escalate,
        'confidence_score': confidence,
        'tone': tone or 'neutral',
        'why': why,
    }


def create_draft_snapshot(bot_id: str, payload: BotDraftSnapshotRequest, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        bot = get_bot(conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail='Bot not found')
        ensure_bot_access(user, bot)
        _require_permission(user, bot['organization_id'], 'release.request')
        versions = list_bot_versions(conn, bot_id)
        next_number = 1 if not versions else max(int(item.get('version_number') or 0) for item in versions) + 1
        snapshot_id = new_id('bver')
        execute(conn, 'INSERT INTO bot_versions (id, organization_id, bot_id, version_number, status, config_json, created_by, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', (snapshot_id, bot['organization_id'], bot_id, next_number, 'draft_snapshot', bot['config_draft_json'], user['id'], payload.notes or 'Draft snapshot', utcnow_iso()))
        create_audit_log(conn, organization_id=bot['organization_id'], actor_user_id=user['id'], actor_type='user', entity_type='bot', entity_id=bot_id, action='bot.draft_snapshot_created', metadata={'version_id': snapshot_id, 'version_number': next_number})
        return fetch_one(conn, 'SELECT * FROM bot_versions WHERE id = ?', (snapshot_id,)) or {}


def list_bot_simulation_cases(bot_id: str, user: dict = Depends(get_current_user)) -> list[dict]:
    with get_connection() as conn:
        bot = get_bot(conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail='Bot not found')
        ensure_bot_access(user, bot)
        rows = fetch_all(conn, 'SELECT * FROM bot_simulation_cases WHERE bot_id = ? ORDER BY updated_at DESC, created_at DESC', (bot_id,))
        return [{**row, 'expected_outcome': from_json(row.get('expected_outcome_json'), {}), 'tags': from_json(row.get('tags_json'), [])} for row in rows]


def create_bot_simulation_case(bot_id: str, payload: BotSimulationCaseRequest, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        bot = get_bot(conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail='Bot not found')
        ensure_bot_access(user, bot)
        _require_permission(user, bot['organization_id'], 'release.request')
        if payload.organization_id != bot['organization_id']:
            raise HTTPException(status_code=400, detail='organization_mismatch')
        row_id = new_id('bsc')
        now = utcnow_iso()
        execute(conn, 'INSERT INTO bot_simulation_cases (id, organization_id, bot_id, title, scenario_text, expected_outcome_json, tags_json, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (row_id, payload.organization_id, bot_id, payload.title, payload.scenario_text, to_json({'expected_action': payload.expected_action, 'expected_queue': payload.expected_queue, 'expected_must_escalate': payload.expected_must_escalate}), to_json(payload.tags), user['id'], now, now))
        create_audit_log(conn, organization_id=bot['organization_id'], actor_user_id=user['id'], actor_type='user', entity_type='bot_simulation_case', entity_id=row_id, action='bot.simulation_case_created', metadata={'bot_id': bot_id})
        row = fetch_one(conn, 'SELECT * FROM bot_simulation_cases WHERE id = ?', (row_id,)) or {}
        return {**row, 'expected_outcome': from_json(row.get('expected_outcome_json'), {}), 'tags': from_json(row.get('tags_json'), [])}


def list_bot_simulation_runs(bot_id: str, user: dict = Depends(get_current_user)) -> list[dict]:
    with get_connection() as conn:
        bot = get_bot(conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail='Bot not found')
        ensure_bot_access(user, bot)
        runs = fetch_all(conn, 'SELECT * FROM bot_simulation_runs WHERE bot_id = ? ORDER BY created_at DESC LIMIT 20', (bot_id,))
        payload = []
        for row in runs:
            results = fetch_all(conn, 'SELECT * FROM bot_simulation_run_results WHERE simulation_run_id = ? ORDER BY created_at ASC', (row['id'],))
            payload.append({**row, 'summary': from_json(row.get('summary_json'), {}), 'results': [{**item, 'result': from_json(item.get('result_json'), {})} for item in results]})
        return payload


def run_bot_simulation(bot_id: str, payload: BotSimulationRunRequest, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        bot = get_bot(conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail='Bot not found')
        ensure_bot_access(user, bot)
        _require_permission(user, bot['organization_id'], 'release.request')
        draft_config = from_json(bot.get('config_draft_json'), {})
        published_version = fetch_one(conn, 'SELECT * FROM bot_versions WHERE id = ?', (bot.get('published_version_id'),)) if bot.get('published_version_id') else None
        if payload.compare_target == 'version' and not payload.right_version_id:
            raise HTTPException(status_code=400, detail='right_version_id is required when compare_target=version')
        baseline_version = None
        if payload.compare_target == 'version':
            baseline_version = fetch_one(conn, 'SELECT * FROM bot_versions WHERE id = ? AND bot_id = ?', (payload.right_version_id, bot_id))
            if not baseline_version:
                raise HTTPException(status_code=404, detail='comparison version not found')
        elif payload.compare_target == 'published':
            baseline_version = published_version
        baseline_config = from_json((baseline_version or {}).get('config_json'), {}) if baseline_version else {}
        cases = fetch_all(conn, 'SELECT * FROM bot_simulation_cases WHERE bot_id = ? ORDER BY updated_at DESC', (bot_id,))
        if payload.case_ids:
            selected = set(payload.case_ids)
            cases = [row for row in cases if row['id'] in selected]
        if not cases:
            raise HTTPException(status_code=400, detail='No simulation cases available')
        run_id = new_id('bsr')
        now = utcnow_iso()
        execute(conn, 'INSERT INTO bot_simulation_runs (id, organization_id, bot_id, compare_target, left_version_id, right_version_id, status, summary_json, cases_total, passed_count, failed_count, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (run_id, bot['organization_id'], bot_id, payload.compare_target, bot.get('published_version_id'), (baseline_version or {}).get('id'), 'running', '{}', len(cases), 0, 0, user['id'], now))
        results = []
        passed = 0
        for case in cases:
            expected = from_json(case.get('expected_outcome_json'), {})
            predicted = _simulation_predict(draft_config, case.get('scenario_text'))
            baseline_predicted = _simulation_predict(baseline_config, case.get('scenario_text')) if baseline_config else None
            checks = []
            if expected.get('expected_action'):
                checks.append(predicted['predicted_action'] == expected.get('expected_action'))
            if expected.get('expected_queue'):
                checks.append(predicted['predicted_queue'] == expected.get('expected_queue'))
            if expected.get('expected_must_escalate') is not None:
                checks.append(bool(predicted['must_escalate']) == bool(expected.get('expected_must_escalate')))
            case_passed = True if not checks else all(checks)
            if case_passed:
                passed += 1
            result = {
                'case_id': case['id'],
                'title': case['title'],
                'scenario_text': case['scenario_text'],
                'expected': expected,
                'draft_prediction': predicted,
                'baseline_prediction': baseline_predicted,
                'changed_vs_baseline': baseline_predicted != predicted if baseline_predicted else False,
            }
            execute(conn, 'INSERT INTO bot_simulation_run_results (id, simulation_run_id, simulation_case_id, passed, result_json, created_at) VALUES (?, ?, ?, ?, ?, ?)', (new_id('bsrr'), run_id, case['id'], 1 if case_passed else 0, to_json(result), now))
            results.append({**result, 'passed': case_passed})
        summary = {
            'pass_rate': round((passed / len(cases)) * 100, 2) if cases else 0,
            'compare_target': payload.compare_target,
            'cases_total': len(cases),
            'changed_vs_baseline': len([item for item in results if item.get('changed_vs_baseline')]),
        }
        execute(conn, 'UPDATE bot_simulation_runs SET status = ?, summary_json = ?, passed_count = ?, failed_count = ? WHERE id = ?', ('completed', to_json(summary), passed, len(cases) - passed, run_id))
        create_audit_log(conn, organization_id=bot['organization_id'], actor_user_id=user['id'], actor_type='user', entity_type='bot_simulation_run', entity_id=run_id, action='bot.simulation_run_completed', metadata=summary)
        row = fetch_one(conn, 'SELECT * FROM bot_simulation_runs WHERE id = ?', (run_id,)) or {}
        return {**row, 'summary': from_json(row.get('summary_json'), {}), 'results': results}

def bot_library_templates(vertical: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> list[dict]:
    _ = user
    if vertical:
        return [item for item in V14_TEMPLATE_LIBRARY if item["vertical"] == vertical]
    return V14_TEMPLATE_LIBRARY

def whatsapp_numbers_status(organization_id: str | None = Query(default=None), bot_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "wn.organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if bot_id:
            where_sql += " AND wn.bot_id = ? "
            params.append(bot_id)
        rows = fetch_all(
            conn,
            f"""
            SELECT wn.*, b.name AS bot_name,
                   (SELECT MAX(created_at) FROM webhook_event_receipts wr WHERE wr.organization_id = wn.organization_id AND wr.channel = 'whatsapp_message') AS last_message_webhook_at,
                   (SELECT MAX(created_at) FROM webhook_event_receipts wr WHERE wr.organization_id = wn.organization_id AND wr.channel = 'whatsapp_status') AS last_status_webhook_at
            FROM whatsapp_numbers wn
            JOIN bots b ON b.id = wn.bot_id
            {where_sql}
            ORDER BY wn.updated_at DESC
            """,
            params,
        )
        return [
            decorate_whatsapp_number(
                row,
                access_token_present=bool(resolve_whatsapp_access_token(conn, organization_id=row["organization_id"], bot_id=row.get("bot_id"))),
            )
            for row in rows
        ]

def publish_schedules_list(organization_id: str | None = Query(default=None), bot_id: str | None = Query(default=None), limit: int = Query(default=settings.default_page_size), offset: int = Query(default=0), user: dict = Depends(get_current_user)) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if bot_id:
            where_sql += " AND bot_id = ? "
            params.append(bot_id)
        return fetch_all(conn, f"SELECT * FROM publish_schedules {where_sql} ORDER BY scheduled_for ASC LIMIT ? OFFSET ?", params + [clamp_limit(limit), clamp_offset(offset)])

def publish_schedules_create(payload: PublishScheduleRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    with get_connection() as conn:
        bot = get_bot(conn, payload.bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        ensure_bot_access(user, bot)
        version_id = payload.version_id or bot.get("published_version_id")
        row_id = new_id("psch")
        execute(conn, "INSERT INTO publish_schedules (id, organization_id, bot_id, version_id, scheduled_for, status, notes, created_by, created_at) VALUES (?, ?, ?, ?, ?, 'scheduled', ?, ?, ?)", (row_id, payload.organization_id, payload.bot_id, version_id, payload.scheduled_for, payload.notes, user["id"], utcnow_iso()))
        return fetch_one(conn, "SELECT * FROM publish_schedules WHERE id = ?", (row_id,))

def publish_schedule_runs_all(organization_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        rows = fetch_all(conn, f"SELECT * FROM publish_schedule_runs {where_sql} ORDER BY created_at DESC LIMIT 100", params)
        return [{**row, "metadata": from_json(row.get("metadata_json"), {})} for row in rows]

def publish_schedule_runs_list(schedule_id: str, user: dict = Depends(get_current_user)) -> list[dict]:
    with get_connection() as conn:
        schedule = fetch_one(conn, "SELECT * FROM publish_schedules WHERE id = ?", (schedule_id,))
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        ensure_org_access(user, schedule["organization_id"])
        rows = fetch_all(conn, "SELECT * FROM publish_schedule_runs WHERE schedule_id = ? ORDER BY created_at DESC", (schedule_id,))
        return [{**row, "metadata": from_json(row.get("metadata_json"), {})} for row in rows]
