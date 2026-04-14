from __future__ import annotations

from .common import *

def root() -> str:
    return f"<html><body style='font-family:Arial,sans-serif;background:#0A0A0A;color:#F5F2EE;padding:32px'><h1>WAOS API {settings.app_version}</h1><p>Runtime listo para operación productiva con PostgreSQL, Business Hub, Customer Preview y Launch Center.</p><ul><li><a style='color:#00E676' href='/app'>Abrir consola WAOS</a></li><li><a style='color:#00E676' href='/docs'>OpenAPI docs</a></li><li><a style='color:#00E676' href='/healthz'>Health</a></li><li><a style='color:#00E676' href='/readyz'>Readiness</a></li></ul></body></html>"

def app_console() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")

def health() -> dict:
    with get_connection() as conn:
        db_ok = fetch_one(conn, "SELECT 1 as ok") is not None
        queue = queue_overview(conn)
        scheduler = scheduler_overview(conn)
    degraded = not db_ok or any(item.get("status") == "dead_letter" and int(item.get("count") or 0) > 0 for item in queue.get("automation_jobs", []) + queue.get("outbox", []))
    return {"status": "degraded" if degraded else "ok", "app": settings.app_name, "database": db_ok, "queue": queue, "scheduler": scheduler}

def health_live() -> dict:
    return {"status": "alive", "app": settings.app_name, "time": utcnow_iso()}

def health_ready() -> dict:
    with get_connection() as conn:
        db_ok = fetch_one(conn, "SELECT 1 as ok") is not None
        queue = queue_overview(conn)
        scheduler = scheduler_overview(conn)
        dead_letters = sum(int(item.get("count") or 0) for item in queue.get("automation_jobs", []) if item.get("status") == "dead_letter") + sum(int(item.get("count") or 0) for item in queue.get("outbox", []) if item.get("status") == "dead_letter")
    ready = db_ok and dead_letters < 25
    return {"status": "ready" if ready else "not_ready", "database": db_ok, "app": settings.app_name, "queue": queue, "scheduler": scheduler, "dead_letters": dead_letters}



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
