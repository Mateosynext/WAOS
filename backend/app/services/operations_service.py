from __future__ import annotations

from ..contracts import ok
from ..performance import TTLCache
from ..config import settings
from ..db import fetch_all
from ..platform import compute_observability_overview, queue_overview, scheduler_overview
from .integrations_service import integration_health_summary
from .reporting_service import list_report_generation_jobs


def runtime_overview(conn, *, organization_id: str | None = None, bot_id: str | None = None) -> dict:
    cache_key = f"runtime:{organization_id or 'all'}:{bot_id or 'all'}"
    cached = _runtime_cache.get(cache_key)
    if cached is not None:
        return cached
    observability = compute_observability_overview(conn, organization_id=organization_id, bot_id=bot_id)
    queue = queue_overview(conn, organization_id=organization_id)
    scheduler = scheduler_overview(conn, organization_id=organization_id)
    report_jobs = list_report_generation_jobs(conn, organization_id=organization_id)
    integrations = integration_health_summary(conn, organization_id=organization_id, bot_id=bot_id) if organization_id else {"items": [], "totals": {"total": 0, "healthy": 0, "degraded": 0, "credential_attention": 0}}
    migrations = fetch_all(conn, "SELECT version, description, applied_at FROM schema_migrations ORDER BY applied_at DESC LIMIT 20")
    return _runtime_cache.set(cache_key, ok({
        "observability": observability,
        "queue": queue,
        "scheduler": scheduler,
        "report_jobs": report_jobs,
        "integrations": integrations,
        "migrations": migrations,
        "cache_ttl_seconds": settings.runtime_cache_ttl_seconds,
    }))


_runtime_cache = TTLCache(ttl_seconds=settings.runtime_cache_ttl_seconds)
