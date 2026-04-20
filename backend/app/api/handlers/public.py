from __future__ import annotations

from .common import *
from ...verticals import get_vertical_profile, list_vertical_profiles
from ...vertical_10x import build_strongest_verticals, get_subvertical_profile
from ...world_class_ext import authenticate_public_api_credential, public_sdk_manifest, register_channel_event
from ...rate_limiter import public_ingest_rate_limit
from ...world_class_plus import append_immutable_audit_event, module_health_checks

def root() -> str:
    return f"<html><body style='font-family:Arial,sans-serif;background:#0A0A0A;color:#F5F2EE;padding:32px'><h1>WAOS API {settings.app_version}</h1><p>Runtime listo para operación productiva con PostgreSQL, Business Hub, Customer Preview y Launch Center.</p><ul><li><a style='color:#00E676' href='/app'>Abrir consola WAOS</a></li><li><a style='color:#00E676' href='/docs'>OpenAPI docs</a></li><li><a style='color:#00E676' href='/healthz'>Health</a></li><li><a style='color:#00E676' href='/readyz'>Readiness</a></li></ul></body></html>"

def app_console() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")

def health() -> dict:
    try:
        with get_connection() as conn:
            db_ok = fetch_one(conn, "SELECT 1 as ok") is not None
            queue = queue_overview(conn)
            scheduler = scheduler_overview(conn)
    except Exception as exc:
        return {"status": "degraded", "app": settings.app_name, "database": False, "queue": {}, "scheduler": {}, "error": str(exc)}
    degraded = not db_ok or any(item.get("status") == "dead_letter" and int(item.get("count") or 0) > 0 for item in queue.get("automation_jobs", []) + queue.get("outbox", []))
    return {"status": "degraded" if degraded else "ok", "app": settings.app_name, "database": db_ok, "queue": queue, "scheduler": scheduler}

def health_live() -> dict:
    return {"status": "alive", "app": settings.app_name, "time": utcnow_iso()}

def health_ready() -> dict:
    try:
        with get_connection() as conn:
            db_ok = fetch_one(conn, "SELECT 1 as ok") is not None
            queue = queue_overview(conn)
            scheduler = scheduler_overview(conn)
            dead_letters = sum(int(item.get("count") or 0) for item in queue.get("automation_jobs", []) if item.get("status") == "dead_letter") + sum(int(item.get("count") or 0) for item in queue.get("outbox", []) if item.get("status") == "dead_letter")
            modules = module_health_checks(conn)
    except Exception as exc:
        return {"status": "not_ready", "database": False, "app": settings.app_name, "queue": {}, "scheduler": {}, "dead_letters": None, "modules": {"status": "error"}, "error": str(exc)}
    ready = db_ok and dead_letters < 25 and modules.get("status") != "error"
    return {"status": "ready" if ready else "not_ready", "database": db_ok, "app": settings.app_name, "queue": queue, "scheduler": scheduler, "dead_letters": dead_letters, "modules": modules}



def public_sso_providers(email: str | None = Query(default=None), organization_slug: str | None = Query(default=None)) -> list[dict]:
    with get_connection() as conn:
        clauses: list[str] = ["sp.status = 'active'"]
        params: list[str] = []
        domain = (email or '').split('@', 1)[1].lower().strip() if email and '@' in email else ''
        if organization_slug:
            clauses.append("o.slug = ?")
            params.append(organization_slug)
        rows = fetch_all(conn, f"""
            SELECT sp.id, sp.organization_id, sp.provider, sp.status, sp.issuer, sp.metadata_json, o.name AS organization_name, o.slug AS organization_slug
            FROM sso_providers sp
            JOIN organizations o ON o.id = sp.organization_id
            WHERE {' AND '.join(clauses)}
            ORDER BY o.name ASC, sp.provider ASC
            """, params)
        providers = []
        for row in rows:
            metadata = from_json(row.get('metadata_json'), {})
            allowed_domains = metadata.get('allowed_domains') or ([] if not metadata.get('domain_hint') else [metadata.get('domain_hint')])
            normalized_domains = [str(item).lower().strip() for item in allowed_domains if item]
            if domain and normalized_domains and domain not in normalized_domains:
                continue
            providers.append({'id': row.get('id'), 'organization_id': row.get('organization_id'), 'organization_name': row.get('organization_name'), 'organization_slug': row.get('organization_slug'), 'provider': row.get('provider'), 'issuer': row.get('issuer'), 'domain_hint': metadata.get('domain_hint'), 'allowed_domains': normalized_domains, 'button_label': f"Entrar con {metadata.get('display_name') or row.get('provider')}"})
        return providers


def public_sdk_manifest_handler() -> dict[str, Any]:
    return public_sdk_manifest()


def public_channel_event_ingest(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    organization_id = str(payload.get('organization_id') or '')
    if not organization_id:
        raise HTTPException(status_code=400, detail='organization_id is required')
    token = request.headers.get('X-WAOS-Public-Key') or request.headers.get('x-waos-public-key') or ''
    if not token:
        raise HTTPException(status_code=401, detail='Missing X-WAOS-Public-Key')
    channel = str(payload.get('channel') or 'webchat')
    direction = str(payload.get('direction') or 'inbound')
    identities = list(payload.get('identities') or [])
    identity_fingerprint = '|'.join(sorted(f"{item.get('type') or item.get('identity_type')}:{item.get('value') or item.get('identity_value')}" for item in identities if item))
    rate_scope = f"public:{organization_id}:{channel}:{payload.get('external_user_id') or identity_fingerprint or payload.get('contact_id') or 'anonymous'}"
    with get_connection() as conn:
        auth = authenticate_public_api_credential(conn, organization_id=organization_id, token=token, required_scope='channels.write')
        if not auth:
            raise HTTPException(status_code=403, detail='Invalid public API credential')
        rate_limit = public_ingest_rate_limit(
            conn,
            organization_id=organization_id,
            scope_key=rate_scope,
            channel=channel,
            direction=direction,
            metadata={"path": str(request.url.path), "credential_id": auth.get('id')},
        )
        if not rate_limit.get('allowed'):
            conn.commit()
            raise HTTPException(status_code=429, detail='Rate limit exceeded for public channel ingest')
        row = register_channel_event(
            conn,
            organization_id=organization_id,
            bot_id=payload.get('bot_id'),
            conversation_id=payload.get('conversation_id'),
            contact_id=payload.get('contact_id'),
            channel=channel,
            direction=direction,
            event_type=str(payload.get('event_type') or 'message'),
            body=payload.get('body'),
            external_thread_id=payload.get('external_thread_id'),
            external_user_id=payload.get('external_user_id'),
            identities=identities,
            metadata=dict(payload.get('metadata') or {}),
        )
        append_immutable_audit_event(
            conn,
            organization_id=organization_id,
            event_type='public.channel_event_ingested',
            entity_type='channel_event',
            entity_id=row.get('id'),
            payload={"channel": channel, "direction": direction, "event_type": payload.get('event_type') or 'message', "credential_id": auth.get('id')},
        )
        conn.commit()
        return {'ok': True, 'data': {**row, 'metadata': from_json(row.get('metadata_json'), {}), 'rate_limit': {'remaining': rate_limit.get('remaining')}}, 'request_id': getattr(request.state, 'request_id', None)}

def public_verticals_catalog(top_only: bool = Query(default=False)) -> list[dict]:
    profiles = list_vertical_profiles()
    return build_strongest_verticals(profiles) if top_only else profiles


def public_vertical_profile(vertical: str | None = Query(default=None), subvertical: str | None = Query(default=None)) -> dict:
    profile = get_vertical_profile(vertical)
    if subvertical:
        selected = get_subvertical_profile(profile, subvertical)
        if not selected:
            raise HTTPException(status_code=404, detail='Subvertical not found')
        return {**profile, 'selected_subvertical': selected}
    return profile


def public_subvertical_profile(vertical: str, subvertical: str | None = Query(default=None)) -> dict:
    profile = get_vertical_profile(vertical)
    selected = get_subvertical_profile(profile, subvertical)
    if not selected:
        raise HTTPException(status_code=404, detail='Subvertical not found')
    return {'vertical': profile.get('id'), 'vertical_name': profile.get('name'), 'subvertical_profile': selected}

