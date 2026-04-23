from __future__ import annotations

from .runtime_schema_guards import assert_schema_ready


def ensure_backend_runtime_schema(conn) -> None:
    assert_schema_ready(
        conn,
        owner="backend_runtime",
        tables=("schema_migrations", "job_idempotency_keys", "report_generation_jobs"),
        columns={"schema_migrations": ("metadata_json",), "report_generation_jobs": ("priority", "locked_at")},
    )
