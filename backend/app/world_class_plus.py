from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from .config import settings
from .utils import add_seconds, hash_value, new_id, parse_iso, to_json, utcnow_iso
from .backpressure import graceful_degradation_flags, queue_depth_snapshot
from .world_class import execute, fetch_all, fetch_one, from_json, record_revenue_event, table_exists


def ensure_world_class_plus_schema(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS defensive_rate_limit_windows (
            id TEXT PRIMARY KEY,
            organization_id TEXT,
            scope_key TEXT NOT NULL UNIQUE,
            channel TEXT,
            direction TEXT,
            window_started_at TEXT NOT NULL,
            window_seconds INTEGER NOT NULL,
            max_events INTEGER NOT NULL,
            events_used INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_defensive_rate_limit_org ON defensive_rate_limit_windows(organization_id, channel, updated_at DESC);

        CREATE TABLE IF NOT EXISTS immutable_audit_chain (
            id TEXT PRIMARY KEY,
            organization_id TEXT,
            event_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT,
            payload_json TEXT NOT NULL DEFAULT '{}',
            previous_hash TEXT,
            entry_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_immutable_audit_chain_org ON immutable_audit_chain(organization_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS deletion_workflows (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            subject_type TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            requested_by TEXT,
            reason TEXT,
            target_stores_json TEXT NOT NULL DEFAULT '[]',
            evidence_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'planned',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, subject_type, subject_id)
        );
        CREATE INDEX IF NOT EXISTS idx_deletion_workflows_org ON deletion_workflows(organization_id, status, updated_at DESC);

        CREATE TABLE IF NOT EXISTS compliance_postures (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL UNIQUE,
            data_region TEXT NOT NULL,
            backup_region TEXT NOT NULL,
            residency_mode TEXT NOT NULL DEFAULT 'regional',
            encryption_status TEXT NOT NULL DEFAULT 'enabled',
            encrypted_backups INTEGER NOT NULL DEFAULT 1,
            backup_last_tested_at TEXT,
            soc2_status TEXT NOT NULL DEFAULT 'readiness',
            iso27001_status TEXT NOT NULL DEFAULT 'readiness',
            controls_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_compliance_postures_org ON compliance_postures(organization_id, updated_at DESC);

        CREATE TABLE IF NOT EXISTS prompt_experiments (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            experiment_key TEXT NOT NULL,
            artifact_a_key TEXT NOT NULL,
            artifact_b_key TEXT NOT NULL,
            rollout_percentage INTEGER NOT NULL DEFAULT 50,
            status TEXT NOT NULL DEFAULT 'active',
            winner_variant TEXT,
            metrics_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, experiment_key)
        );
        CREATE INDEX IF NOT EXISTS idx_prompt_experiments_org ON prompt_experiments(organization_id, bot_id, updated_at DESC);

        CREATE TABLE IF NOT EXISTS chaos_test_runs (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            scenario_key TEXT NOT NULL,
            target TEXT NOT NULL,
            blast_radius TEXT NOT NULL DEFAULT 'low',
            status TEXT NOT NULL DEFAULT 'planned',
            findings_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_chaos_test_runs_org ON chaos_test_runs(organization_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS load_test_runs (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            scenario_key TEXT NOT NULL,
            target_rps INTEGER NOT NULL DEFAULT 0,
            peak_rps INTEGER NOT NULL DEFAULT 0,
            p95_ms INTEGER NOT NULL DEFAULT 0,
            error_rate REAL NOT NULL DEFAULT 0,
            queue_depth INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'planned',
            findings_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_load_test_runs_org ON load_test_runs(organization_id, created_at DESC);
        """
    )


def consume_defensive_rate_limit(
    conn,
    *,
    organization_id: str | None,
    scope_key: str,
    channel: str | None = None,
    direction: str | None = None,
    max_events: int = 5,
    window_seconds: int = 60,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = utcnow_iso()
    row = fetch_one(conn, "SELECT * FROM defensive_rate_limit_windows WHERE scope_key = ?", (scope_key,))
    if row:
        started_at = parse_iso(row.get("window_started_at"))
        expired = False
        if started_at is None:
            expired = True
        else:
            expires_at = parse_iso(add_seconds(row.get("window_started_at") or now, int(row.get("window_seconds") or window_seconds)))
            expired = expires_at is not None and expires_at <= parse_iso(now)
        if expired:
            execute(
                conn,
                "UPDATE defensive_rate_limit_windows SET window_started_at = ?, window_seconds = ?, max_events = ?, events_used = 1, metadata_json = ?, updated_at = ? WHERE id = ?",
                (now, window_seconds, max_events, to_json(metadata or {}), now, row["id"]),
            )
            refreshed = fetch_one(conn, "SELECT * FROM defensive_rate_limit_windows WHERE id = ?", (row["id"],)) or {}
            return {**refreshed, "allowed": True, "remaining": max(0, int(refreshed.get("max_events") or max_events) - int(refreshed.get("events_used") or 0))}
        effective_max = min(int(row.get("max_events") or max_events), int(max_events or row.get("max_events") or 1))
        allowed = int(row.get("events_used") or 0) < effective_max
        execute(
            conn,
            "UPDATE defensive_rate_limit_windows SET max_events = ?, events_used = events_used + 1, metadata_json = ?, updated_at = ? WHERE id = ?",
            (effective_max, to_json(metadata or {}), now, row["id"]),
        )
        refreshed = fetch_one(conn, "SELECT * FROM defensive_rate_limit_windows WHERE id = ?", (row["id"],)) or {}
        refreshed_events = int(refreshed.get("events_used") or 0)
        remaining = max(0, effective_max - refreshed_events)
        return {**refreshed, "allowed": allowed, "remaining": remaining}
    row_id = new_id("rl")
    execute(
        conn,
        "INSERT INTO defensive_rate_limit_windows (id, organization_id, scope_key, channel, direction, window_started_at, window_seconds, max_events, events_used, metadata_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (row_id, organization_id, scope_key, channel, direction, now, window_seconds, max_events, 1, to_json(metadata or {}), now, now),
    )
    created = fetch_one(conn, "SELECT * FROM defensive_rate_limit_windows WHERE id = ?", (row_id,)) or {}
    return {**created, "allowed": True, "remaining": max(0, max_events - 1)}



def append_immutable_audit_event(
    conn,
    *,
    organization_id: str | None,
    event_type: str,
    entity_type: str,
    entity_id: str | None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not table_exists(conn, "immutable_audit_chain"):
        return {}
    previous = fetch_one(
        conn,
        "SELECT * FROM immutable_audit_chain WHERE COALESCE(organization_id, '') = COALESCE(?, '') ORDER BY created_at DESC LIMIT 1",
        (organization_id,),
    )
    prev_hash = previous.get("entry_hash") if previous else ""
    created_at = utcnow_iso()
    material = {
        "organization_id": organization_id,
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "payload": payload or {},
        "created_at": created_at,
        "previous_hash": prev_hash,
    }
    entry_hash = hash_value(to_json(material))
    row_id = new_id("ledger")
    execute(
        conn,
        "INSERT INTO immutable_audit_chain (id, organization_id, event_type, entity_type, entity_id, payload_json, previous_hash, entry_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (row_id, organization_id, event_type, entity_type, entity_id, to_json(payload or {}), prev_hash, entry_hash, created_at),
    )
    return fetch_one(conn, "SELECT * FROM immutable_audit_chain WHERE id = ?", (row_id,)) or {}


_DEFAULT_DELETE_TARGETS = [
    "primary_db",
    "semantic_cache",
    "vector_memory",
    "technical_logs",
    "otel_exports",
    "integration_projections",
    "backup_catalog",
]


def create_deletion_workflow(
    conn,
    *,
    organization_id: str,
    subject_type: str,
    subject_id: str,
    requested_by: str | None = None,
    reason: str | None = None,
    target_stores: list[str] | None = None,
) -> dict[str, Any]:
    now = utcnow_iso()
    targets = list(dict.fromkeys(target_stores or _DEFAULT_DELETE_TARGETS))
    existing = fetch_one(
        conn,
        "SELECT * FROM deletion_workflows WHERE organization_id = ? AND subject_type = ? AND subject_id = ?",
        (organization_id, subject_type, subject_id),
    )
    evidence = {
        "planned_at": now,
        "requested_by": requested_by,
        "deletion_mode": "erase_or_anonymize",
        "stores": targets,
    }
    if existing:
        execute(
            conn,
            "UPDATE deletion_workflows SET requested_by = ?, reason = ?, target_stores_json = ?, evidence_json = ?, status = ?, updated_at = ? WHERE id = ?",
            (requested_by, reason, to_json(targets), to_json(evidence), "planned", now, existing["id"]),
        )
        row = fetch_one(conn, "SELECT * FROM deletion_workflows WHERE id = ?", (existing["id"],)) or {}
    else:
        row_id = new_id("delwf")
        execute(
            conn,
            "INSERT INTO deletion_workflows (id, organization_id, subject_type, subject_id, requested_by, reason, target_stores_json, evidence_json, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (row_id, organization_id, subject_type, subject_id, requested_by, reason, to_json(targets), to_json(evidence), "planned", now, now),
        )
        row = fetch_one(conn, "SELECT * FROM deletion_workflows WHERE id = ?", (row_id,)) or {}
    append_immutable_audit_event(
        conn,
        organization_id=organization_id,
        event_type="governance.deletion_workflow_planned",
        entity_type=subject_type,
        entity_id=subject_id,
        payload={"requested_by": requested_by, "targets": targets, "reason": reason},
    )
    return {**row, "target_stores": targets, "evidence": evidence}



def upsert_compliance_posture(
    conn,
    *,
    organization_id: str,
    data_region: str = "mx-central",
    backup_region: str = "mx-secondary",
    residency_mode: str = "regional",
    encryption_status: str = "enabled",
    encrypted_backups: bool = True,
    backup_last_tested_at: str | None = None,
    soc2_status: str = "readiness",
    iso27001_status: str = "readiness",
    controls: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = utcnow_iso()
    default_controls = {
        "lfpdppp": True,
        "consent_ledger": True,
        "retention_policies": True,
        "append_only_audit": True,
        "delete_workflows": True,
        "encrypted_backups": bool(encrypted_backups),
        "data_residency": residency_mode in {"regional", "pinned"},
        "soc2": soc2_status in {"readiness", "in_progress", "ready"},
        "iso27001": iso27001_status in {"readiness", "in_progress", "ready"},
    }
    merged_controls = {**default_controls, **(controls or {})}
    existing = fetch_one(conn, "SELECT * FROM compliance_postures WHERE organization_id = ?", (organization_id,))
    if existing:
        execute(
            conn,
            "UPDATE compliance_postures SET data_region = ?, backup_region = ?, residency_mode = ?, encryption_status = ?, encrypted_backups = ?, backup_last_tested_at = ?, soc2_status = ?, iso27001_status = ?, controls_json = ?, updated_at = ? WHERE id = ?",
            (data_region, backup_region, residency_mode, encryption_status, 1 if encrypted_backups else 0, backup_last_tested_at, soc2_status, iso27001_status, to_json(merged_controls), now, existing["id"]),
        )
        row = fetch_one(conn, "SELECT * FROM compliance_postures WHERE id = ?", (existing["id"],)) or {}
    else:
        row_id = new_id("comp")
        execute(
            conn,
            "INSERT INTO compliance_postures (id, organization_id, data_region, backup_region, residency_mode, encryption_status, encrypted_backups, backup_last_tested_at, soc2_status, iso27001_status, controls_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (row_id, organization_id, data_region, backup_region, residency_mode, encryption_status, 1 if encrypted_backups else 0, backup_last_tested_at, soc2_status, iso27001_status, to_json(merged_controls), now, now),
        )
        row = fetch_one(conn, "SELECT * FROM compliance_postures WHERE id = ?", (row_id,)) or {}
    return {**row, "controls": merged_controls}



def compliance_overview(conn, *, organization_id: str) -> dict[str, Any]:
    posture = fetch_one(conn, "SELECT * FROM compliance_postures WHERE organization_id = ?", (organization_id,)) if table_exists(conn, "compliance_postures") else None
    if not posture:
        posture = upsert_compliance_posture(conn, organization_id=organization_id)
    deletion_rows = fetch_all(conn, "SELECT * FROM deletion_workflows WHERE organization_id = ? ORDER BY updated_at DESC LIMIT 100", (organization_id,)) if table_exists(conn, "deletion_workflows") else []
    audit_rows = fetch_all(conn, "SELECT * FROM immutable_audit_chain WHERE organization_id = ? ORDER BY created_at DESC LIMIT 200", (organization_id,)) if table_exists(conn, "immutable_audit_chain") else []
    controls = from_json(posture.get("controls_json"), {})
    status = "ok"
    if posture.get("encryption_status") != "enabled" or not bool(int(posture.get("encrypted_backups") or 0)):
        status = "degraded"
    return {
        "status": status,
        "posture": {
            **posture,
            "controls": controls,
            "encrypted_backups": bool(int(posture.get("encrypted_backups") or 0)),
        },
        "governance": {
            "immutable_audit_events": len(audit_rows),
            "deletion_workflows": len(deletion_rows),
            "pending_deletions": sum(1 for row in deletion_rows if row.get("status") != "completed"),
            "latest_audit_hash": audit_rows[0].get("entry_hash") if audit_rows else None,
        },
        "deletions": [
            {**row, "target_stores": from_json(row.get("target_stores_json"), []), "evidence": from_json(row.get("evidence_json"), {})}
            for row in deletion_rows[:20]
        ],
    }



def runtime_autoscaling_plan(conn, *, organization_id: str | None = None) -> dict[str, Any]:
    snapshot = queue_depth_snapshot(conn, organization_id=organization_id)
    queue_pressure = int(snapshot.get("queue_pressure") or 0)
    oldest_age_seconds = int(snapshot.get("oldest_age_seconds") or 0)
    latency_boost = min(8, oldest_age_seconds // 120)
    desired_workers = max(1, min(64, math.ceil(queue_pressure / 25) + int(latency_boost)))
    if queue_pressure == 0:
        action = "hold"
    elif desired_workers >= 24 or oldest_age_seconds >= 900:
        action = "scale_up_fast"
    elif desired_workers >= 8:
        action = "scale_up"
    else:
        action = "steady"
    return {
        "organization_id": organization_id,
        "queue": snapshot,
        "autoscaling": {
            "desired_workers": desired_workers,
            "recommended_min_workers": max(1, min(desired_workers, 4)),
            "recommended_max_workers": max(desired_workers, 8),
            "action": action,
        },
        "policy": {
            "driver": ["queue_depth", "oldest_job_age", "outbox_backlog"],
            "notes": "Recommendation derived from backlog pressure; external HPA/worker autoscaler should consume this output.",
        },
    }



def module_health_checks(conn, *, organization_id: str | None = None) -> dict[str, Any]:
    modules: list[dict[str, Any]] = []

    def add(name: str, status: str, detail: Any) -> None:
        modules.append({"module": name, "status": status, "detail": detail})

    try:
        fetch_one(conn, "SELECT 1 AS ok")
        add("database", "ok", {"backend": getattr(conn, "backend", "sqlite")})
    except Exception as exc:  # pragma: no cover
        add("database", "error", str(exc))

    auto = runtime_autoscaling_plan(conn, organization_id=organization_id)
    queue = auto.get("queue") or {}
    add("workers", "warning" if int(queue.get("oldest_age_seconds") or 0) >= 900 else "ok", auto)

    dead_letters = 0
    if table_exists(conn, "dead_letter_events"):
        if organization_id:
            row = fetch_one(conn, "SELECT COUNT(*) AS value FROM dead_letter_events WHERE organization_id = ?", (organization_id,))
        else:
            row = fetch_one(conn, "SELECT COUNT(*) AS value FROM dead_letter_events")
        dead_letters = int((row or {}).get("value") or 0)
    add("dead_letters", "warning" if dead_letters else "ok", {"count": dead_letters})

    open_circuits = 0
    openai_open = 0
    meta_open = 0
    if table_exists(conn, "provider_circuit_breakers"):
        if organization_id:
            query = "SELECT provider, SUM(CASE WHEN state = 'open' THEN 1 ELSE 0 END) AS open_count FROM provider_circuit_breakers GROUP BY provider"
            rows = fetch_all(conn, query)
        else:
            rows = fetch_all(conn, "SELECT provider, SUM(CASE WHEN state = 'open' THEN 1 ELSE 0 END) AS open_count FROM provider_circuit_breakers GROUP BY provider")
        for row in rows:
            count = int(row.get("open_count") or 0)
            open_circuits += count
            provider = str(row.get("provider") or "")
            if provider == "openai":
                openai_open = count
            if provider == "meta_whatsapp":
                meta_open = count
    add("provider_circuits", "warning" if open_circuits else "ok", {"open": open_circuits})
    add("ai", "warning" if openai_open or not settings.openai_api_key else "ok", {"configured": bool(settings.openai_api_key), "open_circuits": openai_open, "provider": "openai" if settings.openai_api_key else "heuristic_only"})
    add("whatsapp", "warning" if meta_open else "ok", {"open_circuits": meta_open, "provider": "meta_whatsapp"})

    payments_detail = {"degraded_integrations": 0, "healthy_integrations": 0}
    payments_status = "warning"
    if table_exists(conn, "integration_connections"):
        params: list[Any] = []
        where = "WHERE provider IN ('stripe', 'mercadopago', 'paypal', 'payments')"
        if organization_id:
            where += " AND organization_id = ?"
            params.append(organization_id)
        rows = fetch_all(conn, f"SELECT provider, health_status, status, last_error FROM integration_connections {where}", tuple(params))
        healthy = sum(1 for row in rows if str(row.get("health_status") or row.get("status") or "").lower() in {"healthy", "ok", "connected", "active", "configured"})
        degraded = max(0, len(rows) - healthy)
        payments_detail = {"degraded_integrations": degraded, "healthy_integrations": healthy, "providers": sorted({str(row.get('provider') or '') for row in rows if row.get('provider')})}
        payments_status = "ok" if healthy and degraded == 0 else ("warning" if rows else "warning")
    add("payments", payments_status, payments_detail)

    otel_pending = 0
    if table_exists(conn, "otel_span_exports"):
        row = fetch_one(conn, "SELECT COUNT(*) AS value FROM otel_span_exports WHERE status IN ('pending','failed')")
        otel_pending = int((row or {}).get("value") or 0)
    add("otel", "warning" if settings.otel_export_enabled and otel_pending > 50 else "ok", {"pending_or_failed": otel_pending, "enabled": settings.otel_export_enabled})

    channel_events = 0
    if table_exists(conn, "channel_events"):
        if organization_id:
            row = fetch_one(conn, "SELECT COUNT(*) AS value FROM channel_events WHERE organization_id = ?", (organization_id,))
        else:
            row = fetch_one(conn, "SELECT COUNT(*) AS value FROM channel_events")
        channel_events = int((row or {}).get("value") or 0)
    add("omnichannel", "ok" if channel_events else "warning", {"events": channel_events})

    memory_rows = 0
    if table_exists(conn, "memory_vectors"):
        if organization_id:
            row = fetch_one(conn, "SELECT COUNT(*) AS value FROM memory_vectors WHERE organization_id = ?", (organization_id,))
        else:
            row = fetch_one(conn, "SELECT COUNT(*) AS value FROM memory_vectors")
        memory_rows = int((row or {}).get("value") or 0)
    add("long_term_memory", "ok" if memory_rows else "warning", {"vectors": memory_rows})

    credentials = 0
    if table_exists(conn, "public_api_credentials"):
        if organization_id:
            row = fetch_one(conn, "SELECT COUNT(*) AS value FROM public_api_credentials WHERE organization_id = ? AND status = 'active'", (organization_id,))
        else:
            row = fetch_one(conn, "SELECT COUNT(*) AS value FROM public_api_credentials WHERE status = 'active'")
        credentials = int((row or {}).get("value") or 0)
    add("public_api", "ok" if credentials else "warning", {"active_credentials": credentials})

    degradation = graceful_degradation_flags(conn, organization_id=organization_id)
    add("graceful_degradation", "warning" if degradation.get("degrade_ai_generation") else "ok", degradation)

    overall = "ok"
    if any(item["status"] == "error" for item in modules):
        overall = "error"
    elif any(item["status"] == "warning" for item in modules):
        overall = "degraded"
    return {"status": overall, "modules": modules}



def unified_inbox_overview(conn, *, organization_id: str, bot_id: str | None = None, limit: int = 50) -> dict[str, Any]:
    if not table_exists(conn, "channel_events"):
        return {"summary": {"threads": 0, "cross_channel_threads": 0, "channels": []}, "threads": []}
    params: list[Any] = [organization_id]
    bot_clause = ""
    if bot_id:
        bot_clause = " AND ce.bot_id = ?"
        params.append(bot_id)
    rows = fetch_all(
        conn,
        f"""
        SELECT ce.*, ct.name AS contact_name, ct.phone AS contact_phone, ct.email AS contact_email,
               c.status AS conversation_status, c.assigned_user_id
        FROM channel_events ce
        LEFT JOIN contacts ct ON ct.id = ce.contact_id
        LEFT JOIN conversations c ON c.id = ce.conversation_id
        WHERE ce.organization_id = ?{bot_clause}
        ORDER BY ce.updated_at DESC
        LIMIT ?
        """,
        (*params, max(limit * 4, 100)),
    )
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        thread_key = str(row.get("contact_id") or row.get("conversation_id") or row.get("external_thread_id") or row.get("external_user_id") or row.get("id"))
        thread = grouped.setdefault(
            thread_key,
            {
                "thread_key": thread_key,
                "contact_id": row.get("contact_id"),
                "conversation_id": row.get("conversation_id"),
                "contact_name": row.get("contact_name") or row.get("external_user_id") or "Unknown",
                "channels": set(),
                "events": 0,
                "last_message_at": row.get("updated_at") or row.get("created_at"),
                "last_body": row.get("body") or "",
                "conversation_status": row.get("conversation_status") or "unknown",
                "assigned_user_id": row.get("assigned_user_id"),
                "identities": set(),
            },
        )
        thread["channels"].add(str(row.get("channel") or "unknown"))
        thread["events"] += 1
        if row.get("updated_at") and row.get("updated_at") >= thread["last_message_at"]:
            thread["last_message_at"] = row.get("updated_at")
            thread["last_body"] = row.get("body") or ""
        metadata = from_json(row.get("metadata_json"), {})
        for identity in metadata.get("identities") or []:
            id_type = identity.get("identity_type") or identity.get("identity_type") or identity.get("type")
            id_value = identity.get("identity_value") or identity.get("value")
            if id_type and id_value:
                thread["identities"].add(f"{id_type}:{id_value}")
    threads = []
    channel_counts: dict[str, int] = defaultdict(int)
    for item in grouped.values():
        channels = sorted(item.pop("channels"))
        for channel in channels:
            channel_counts[channel] += 1
        identities = sorted(item.pop("identities"))
        threads.append({**item, "channels": channels, "cross_channel": len(channels) > 1, "identities": identities, "summary": str(item.get("last_body") or "")[:180]})
    threads.sort(key=lambda entry: (entry.get("last_message_at") or "", entry.get("events") or 0), reverse=True)
    return {
        "summary": {
            "threads": len(threads),
            "cross_channel_threads": sum(1 for item in threads if item["cross_channel"]),
            "channels": [{"channel": key, "threads": value} for key, value in sorted(channel_counts.items(), key=lambda item: (-item[1], item[0]))],
        },
        "threads": threads[:limit],
    }



def create_prompt_experiment(
    conn,
    *,
    organization_id: str,
    experiment_key: str,
    artifact_a_key: str,
    artifact_b_key: str,
    bot_id: str | None = None,
    rollout_percentage: int = 50,
    status: str = "active",
) -> dict[str, Any]:
    rollout_percentage = max(1, min(int(rollout_percentage or 50), 99))
    now = utcnow_iso()
    existing = fetch_one(conn, "SELECT * FROM prompt_experiments WHERE organization_id = ? AND experiment_key = ?", (organization_id, experiment_key))
    metrics = {"assignments": 0, "wins_a": 0, "wins_b": 0}
    if existing:
        current_metrics = from_json(existing.get("metrics_json"), {})
        metrics.update(current_metrics)
        execute(
            conn,
            "UPDATE prompt_experiments SET bot_id = COALESCE(?, bot_id), artifact_a_key = ?, artifact_b_key = ?, rollout_percentage = ?, status = ?, updated_at = ? WHERE id = ?",
            (bot_id, artifact_a_key, artifact_b_key, rollout_percentage, status, now, existing["id"]),
        )
        row = fetch_one(conn, "SELECT * FROM prompt_experiments WHERE id = ?", (existing["id"],)) or {}
    else:
        row_id = new_id("pexp")
        execute(
            conn,
            "INSERT INTO prompt_experiments (id, organization_id, bot_id, experiment_key, artifact_a_key, artifact_b_key, rollout_percentage, status, winner_variant, metrics_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)",
            (row_id, organization_id, bot_id, experiment_key, artifact_a_key, artifact_b_key, rollout_percentage, status, to_json(metrics), now, now),
        )
        row = fetch_one(conn, "SELECT * FROM prompt_experiments WHERE id = ?", (row_id,)) or {}
    append_immutable_audit_event(conn, organization_id=organization_id, event_type="quality.prompt_experiment_upserted", entity_type="prompt_experiment", entity_id=experiment_key, payload={"bot_id": bot_id, "artifact_a_key": artifact_a_key, "artifact_b_key": artifact_b_key, "rollout_percentage": rollout_percentage, "status": status})
    return {**row, "metrics": metrics}



def assign_prompt_experiment_variant(conn, *, organization_id: str, experiment_key: str, conversation_id: str | None = None, contact_id: str | None = None) -> dict[str, Any] | None:
    row = fetch_one(conn, "SELECT * FROM prompt_experiments WHERE organization_id = ? AND experiment_key = ? AND status = 'active'", (organization_id, experiment_key))
    if not row:
        return None
    seed = f"{experiment_key}:{conversation_id or contact_id or new_id('anon')}"
    bucket = int(hash_value(seed)[:8], 16) % 100
    variant = "A" if bucket < int(row.get("rollout_percentage") or 50) else "B"
    metrics = from_json(row.get("metrics_json"), {"assignments": 0, "wins_a": 0, "wins_b": 0})
    metrics["assignments"] = int(metrics.get("assignments") or 0) + 1
    execute(conn, "UPDATE prompt_experiments SET metrics_json = ?, updated_at = ? WHERE id = ?", (to_json(metrics), utcnow_iso(), row["id"]))
    refreshed = fetch_one(conn, "SELECT * FROM prompt_experiments WHERE id = ?", (row["id"],)) or row
    return {**refreshed, "metrics": metrics, "assigned_variant": variant, "assigned_artifact_key": refreshed.get("artifact_a_key") if variant == "A" else refreshed.get("artifact_b_key")}



def list_prompt_experiments(conn, *, organization_id: str, bot_id: str | None = None) -> dict[str, Any]:
    if not table_exists(conn, "prompt_experiments"):
        return {"summary": {"experiments": 0}, "items": []}
    if bot_id:
        rows = fetch_all(conn, "SELECT * FROM prompt_experiments WHERE organization_id = ? AND COALESCE(bot_id, '') IN (?, '') ORDER BY updated_at DESC LIMIT 100", (organization_id, bot_id))
    else:
        rows = fetch_all(conn, "SELECT * FROM prompt_experiments WHERE organization_id = ? ORDER BY updated_at DESC LIMIT 100", (organization_id,))
    items = [{**row, "metrics": from_json(row.get("metrics_json"), {})} for row in rows]
    return {"summary": {"experiments": len(items), "active": sum(1 for item in items if item.get("status") == "active")}, "items": items}



def register_chaos_test_run(conn, *, organization_id: str, scenario_key: str, target: str, blast_radius: str = "low", status: str = "passed", findings: dict[str, Any] | None = None) -> dict[str, Any]:
    row_id = new_id("chaos")
    created_at = utcnow_iso()
    execute(conn, "INSERT INTO chaos_test_runs (id, organization_id, scenario_key, target, blast_radius, status, findings_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (row_id, organization_id, scenario_key, target, blast_radius, status, to_json(findings or {}), created_at))
    append_immutable_audit_event(conn, organization_id=organization_id, event_type="quality.chaos_test_recorded", entity_type="chaos_test", entity_id=row_id, payload={"scenario_key": scenario_key, "target": target, "status": status, "blast_radius": blast_radius})
    return fetch_one(conn, "SELECT * FROM chaos_test_runs WHERE id = ?", (row_id,)) or {}



def chaos_overview(conn, *, organization_id: str) -> dict[str, Any]:
    rows = fetch_all(conn, "SELECT * FROM chaos_test_runs WHERE organization_id = ? ORDER BY created_at DESC LIMIT 100", (organization_id,)) if table_exists(conn, "chaos_test_runs") else []
    return {
        "summary": {
            "runs": len(rows),
            "passed": sum(1 for row in rows if row.get("status") == "passed"),
            "review": sum(1 for row in rows if row.get("status") == "review"),
            "failed": sum(1 for row in rows if row.get("status") == "failed"),
        },
        "recent": [{**row, "findings": from_json(row.get("findings_json"), {})} for row in rows[:20]],
    }



def register_load_test_run(
    conn,
    *,
    organization_id: str,
    scenario_key: str,
    target_rps: int,
    peak_rps: int,
    p95_ms: int,
    error_rate: float,
    queue_depth: int,
    status: str = "passed",
    findings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row_id = new_id("load")
    created_at = utcnow_iso()
    execute(conn, "INSERT INTO load_test_runs (id, organization_id, scenario_key, target_rps, peak_rps, p95_ms, error_rate, queue_depth, status, findings_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (row_id, organization_id, scenario_key, int(target_rps), int(peak_rps), int(p95_ms), float(error_rate), int(queue_depth), status, to_json(findings or {}), created_at))
    append_immutable_audit_event(conn, organization_id=organization_id, event_type="quality.load_test_recorded", entity_type="load_test", entity_id=row_id, payload={"scenario_key": scenario_key, "target_rps": target_rps, "peak_rps": peak_rps, "p95_ms": p95_ms, "error_rate": error_rate, "queue_depth": queue_depth, "status": status})
    return fetch_one(conn, "SELECT * FROM load_test_runs WHERE id = ?", (row_id,)) or {}



def load_test_overview(conn, *, organization_id: str) -> dict[str, Any]:
    rows = fetch_all(conn, "SELECT * FROM load_test_runs WHERE organization_id = ? ORDER BY created_at DESC LIMIT 100", (organization_id,)) if table_exists(conn, "load_test_runs") else []
    latest = rows[0] if rows else {}
    return {
        "summary": {
            "runs": len(rows),
            "best_peak_rps": max((int(row.get("peak_rps") or 0) for row in rows), default=0),
            "latest_p95_ms": int(latest.get("p95_ms") or 0),
            "latest_error_rate": float(latest.get("error_rate") or 0),
        },
        "recent": [{**row, "findings": from_json(row.get("findings_json"), {})} for row in rows[:20]],
    }



def revenue_optimization_world_class(conn, *, organization_id: str, bot_id: str | None = None) -> dict[str, Any]:
    lead_clause = "WHERE organization_id = ?"
    lead_params: list[Any] = [organization_id]
    payment_clause = "WHERE organization_id = ?"
    payment_params: list[Any] = [organization_id]
    convo_clause = "WHERE organization_id = ?"
    convo_params: list[Any] = [organization_id]
    if bot_id:
        lead_clause += " AND bot_id = ?"
        payment_clause += " AND bot_id = ?"
        convo_clause += " AND bot_id = ?"
        lead_params.append(bot_id)
        payment_params.append(bot_id)
        convo_params.append(bot_id)
    leads = fetch_all(conn, f"SELECT * FROM crm_leads {lead_clause} ORDER BY updated_at DESC LIMIT 300", tuple(lead_params)) if table_exists(conn, "crm_leads") else []
    payments = fetch_all(conn, f"SELECT * FROM commerce_payments {payment_clause} ORDER BY updated_at DESC LIMIT 300", tuple(payment_params)) if table_exists(conn, "commerce_payments") else []
    conversations = fetch_all(conn, f"SELECT * FROM conversations {convo_clause} ORDER BY updated_at DESC LIMIT 300", tuple(convo_params)) if table_exists(conn, "conversations") else []
    actions: list[dict[str, Any]] = []
    now_dt = parse_iso(utcnow_iso())

    for lead in leads[:120]:
        followup_at = parse_iso(lead.get("followup_at"))
        close_probability = float(lead.get("close_probability") or 0)
        estimated_amount = float(lead.get("estimated_amount") or 0)
        stage = str(lead.get("stage") or "")
        if estimated_amount <= 0:
            continue
        if followup_at and now_dt and followup_at <= now_dt and close_probability >= 50:
            actions.append({
                "type": "smart_followup",
                "contact_id": lead.get("contact_id"),
                "conversation_id": lead.get("conversation_id"),
                "lead_id": lead.get("id"),
                "score": round(close_probability / 100, 4),
                "expected_value": round(estimated_amount * (close_probability / 100), 2),
                "recommended_action": "send_followup_now",
                "reason": "followup_due_high_probability",
            })
        if stage not in {"cerrado_ganado", "closed_won", "lost"}:
            price_multiplier = 1.0 + (0.08 if close_probability >= 75 else (-0.05 if close_probability <= 35 else 0.0))
            recommended_price = round(max(0, estimated_amount * price_multiplier), 2)
            actions.append({
                "type": "dynamic_pricing",
                "contact_id": lead.get("contact_id"),
                "conversation_id": lead.get("conversation_id"),
                "lead_id": lead.get("id"),
                "score": round(abs(price_multiplier - 1.0), 4),
                "expected_value": round(recommended_price, 2),
                "recommended_action": "quote_adjustment",
                "reason": "probability_based_pricing",
                "pricing": {"base_amount": estimated_amount, "recommended_amount": recommended_price, "multiplier": price_multiplier},
            })
        if close_probability >= 70 and estimated_amount >= 1000:
            actions.append({
                "type": "upsell_intelligence",
                "contact_id": lead.get("contact_id"),
                "conversation_id": lead.get("conversation_id"),
                "lead_id": lead.get("id"),
                "score": round(min(1.0, close_probability / 100 + 0.15), 4),
                "expected_value": round(estimated_amount * 0.2, 2),
                "recommended_action": "offer_premium_package",
                "reason": "high_intent_high_ticket",
            })

    for payment in payments[:120]:
        status = str(payment.get("status") or "")
        amount = float(payment.get("amount") or 0)
        created_dt = parse_iso(payment.get("created_at"))
        age_hours = int((now_dt - created_dt).total_seconds() // 3600) if now_dt and created_dt else 0
        if status in {"pending", "requires_payment", "initiated"} and age_hours >= 6:
            actions.append({
                "type": "payment_recovery",
                "contact_id": payment.get("contact_id"),
                "conversation_id": payment.get("conversation_id"),
                "payment_id": payment.get("id"),
                "score": round(min(1.0, 0.4 + age_hours / 72), 4),
                "expected_value": round(amount, 2),
                "recommended_action": "retry_payment_sequence",
                "reason": "stale_pending_payment",
            })
        if str(payment.get("cart_recovery_status") or "") in {"inactive", "pending"} and age_hours >= 4:
            actions.append({
                "type": "abandoned_cart_recovery",
                "contact_id": payment.get("contact_id"),
                "conversation_id": payment.get("conversation_id"),
                "payment_id": payment.get("id"),
                "score": round(min(1.0, 0.35 + age_hours / 96), 4),
                "expected_value": round(amount, 2),
                "recommended_action": "recover_checkout",
                "reason": "cart_abandoned",
            })

    convo_by_id = {str(row.get("id")): row for row in conversations}
    for lead in leads[:120]:
        convo = convo_by_id.get(str(lead.get("conversation_id")))
        if not convo:
            continue
        updated_dt = parse_iso(convo.get("updated_at") or convo.get("last_message_at"))
        hours_idle = int((now_dt - updated_dt).total_seconds() // 3600) if now_dt and updated_dt else 0
        close_probability = float(lead.get("close_probability") or 0)
        if hours_idle >= 24 and close_probability >= 45:
            actions.append({
                "type": "predictive_churn_prevention",
                "contact_id": lead.get("contact_id"),
                "conversation_id": lead.get("conversation_id"),
                "lead_id": lead.get("id"),
                "score": round(min(1.0, 0.3 + hours_idle / 120), 4),
                "expected_value": round(float(lead.get("estimated_amount") or 0) * max(0.2, close_probability / 100), 2),
                "recommended_action": "reengage_with_offer",
                "reason": "conversation_idle_risk",
            })

    deduped: dict[str, dict[str, Any]] = {}
    for action in actions:
        key = hash_value(f"{action.get('type')}:{action.get('contact_id')}:{action.get('conversation_id')}:{action.get('lead_id')}:{action.get('payment_id')}:{action.get('recommended_action')}")
        current = deduped.get(key)
        if current is None or float(action.get("expected_value") or 0) > float(current.get("expected_value") or 0):
            deduped[key] = action
    ranked = sorted(deduped.values(), key=lambda item: (float(item.get("expected_value") or 0), float(item.get("score") or 0)), reverse=True)

    materialized = 0
    for item in ranked[:20]:
        recent = fetch_one(
            conn,
            "SELECT * FROM revenue_optimization_events WHERE organization_id = ? AND COALESCE(conversation_id, '') = COALESCE(?, '') AND COALESCE(contact_id, '') = COALESCE(?, '') AND event_type = ? ORDER BY created_at DESC LIMIT 1",
            (organization_id, item.get("conversation_id"), item.get("contact_id"), item.get("type")),
        ) if table_exists(conn, "revenue_optimization_events") else None
        should_create = True
        if recent:
            recent_dt = parse_iso(recent.get("created_at"))
            should_create = not (recent_dt and now_dt and (now_dt - recent_dt).total_seconds() < 86400)
        if should_create:
            record_revenue_event(
                conn,
                organization_id=organization_id,
                bot_id=bot_id,
                conversation_id=item.get("conversation_id"),
                contact_id=item.get("contact_id"),
                event_type=str(item.get("type") or "recommendation"),
                recommendation=item,
                expected_value=float(item.get("expected_value") or 0),
            )
            materialized += 1

    commission_by_owner: dict[str, dict[str, Any]] = defaultdict(lambda: {"payments": 0, "revenue": 0.0, "estimated_commission": 0.0})
    roi_by_channel: dict[str, dict[str, Any]] = defaultdict(lambda: {"payments": 0, "revenue": 0.0})
    leads_by_id = {str(row.get("id")): row for row in leads}
    for payment in payments:
        if str(payment.get("status") or "") not in {"paid", "confirmed", "succeeded"}:
            continue
        amount = float(payment.get("amount") or 0)
        lead = leads_by_id.get(str(payment.get("crm_lead_id")))
        owner = str((lead or {}).get("owner_user_id") or "unassigned")
        commission_rate = 0.05 if amount < 3000 else 0.08
        bucket = commission_by_owner[owner]
        bucket["payments"] += 1
        bucket["revenue"] = round(bucket["revenue"] + amount, 2)
        bucket["estimated_commission"] = round(bucket["estimated_commission"] + amount * commission_rate, 2)
        channel = str((lead or {}).get("source_channel") or "unknown")
        channel_bucket = roi_by_channel[channel]
        channel_bucket["payments"] += 1
        channel_bucket["revenue"] = round(channel_bucket["revenue"] + amount, 2)

    return {
        "summary": {
            "recommended_actions": len(ranked),
            "materialized_events": materialized,
            "expected_value": round(sum(float(item.get("expected_value") or 0) for item in ranked[:20]), 2),
        },
        "actions": ranked[:20],
        "commission_tracking": [{"owner_user_id": owner, **data} for owner, data in sorted(commission_by_owner.items(), key=lambda item: (-item[1]["revenue"], item[0]))],
        "roi_attribution": [{"source_channel": channel, **data} for channel, data in sorted(roi_by_channel.items(), key=lambda item: (-item[1]["revenue"], item[0]))],
    }
