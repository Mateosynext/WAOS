from __future__ import annotations

from typing import Any

from .base import ConnectionLike, execute, fetch_all, fetch_one


def get_whatsapp_template(conn: ConnectionLike, template_id: str) -> dict | None:
    return fetch_one(conn, "SELECT * FROM whatsapp_templates WHERE id = ?", (template_id,))


def get_whatsapp_template_by_name(conn: ConnectionLike, *, organization_id: str, bot_id: str, name: str) -> dict | None:
    return fetch_one(
        conn,
        "SELECT * FROM whatsapp_templates WHERE organization_id = ? AND bot_id = ? AND name = ? ORDER BY updated_at DESC LIMIT 1",
        (organization_id, bot_id, name),
    )


def get_whatsapp_template_version(conn: ConnectionLike, version_id: str, template_id: str | None = None) -> dict | None:
    if template_id:
        return fetch_one(conn, "SELECT * FROM whatsapp_template_versions WHERE id = ? AND template_id = ?", (version_id, template_id))
    return fetch_one(conn, "SELECT * FROM whatsapp_template_versions WHERE id = ?", (version_id,))


def get_max_template_version_number(conn: ConnectionLike, template_id: str) -> dict | None:
    return fetch_one(conn, "SELECT MAX(version_number) AS value FROM whatsapp_template_versions WHERE template_id = ?", (template_id,))


def list_whatsapp_template_versions(conn: ConnectionLike, template_id: str) -> list[dict]:
    return fetch_all(conn, "SELECT * FROM whatsapp_template_versions WHERE template_id = ? ORDER BY version_number DESC, created_at DESC", (template_id,))


def list_whatsapp_template_sync_runs(conn: ConnectionLike, template_id: str, limit: int = 20) -> list[dict]:
    return fetch_all(conn, "SELECT * FROM whatsapp_template_sync_runs WHERE template_id = ? ORDER BY started_at DESC LIMIT ?", (template_id, limit))


def update_whatsapp_template_performance(conn: ConnectionLike, *, template_id: str, performance_score: int | float, updated_at: str) -> None:
    execute(conn, "UPDATE whatsapp_templates SET performance_score = ?, updated_at = ? WHERE id = ?", (performance_score, updated_at, template_id))


def list_template_delivery_projection_rows(conn: ConnectionLike, *, organization_id: str, template_name: str, since: str | None = None, until: str | None = None, limit: int = 500) -> list[dict]:
    sql = "SELECT * FROM whatsapp_delivery_projection WHERE organization_id = ? AND template_name = ?"
    params: list[Any] = [organization_id, template_name]
    if since:
        sql += " AND COALESCE(accepted_at, created_at) >= ?"
        params.append(since)
    if until:
        sql += " AND COALESCE(accepted_at, created_at) <= ?"
        params.append(until)
    sql += " ORDER BY COALESCE(last_event_at, accepted_at, created_at) DESC LIMIT ?"
    params.append(limit)
    return fetch_all(conn, sql, tuple(params))


def insert_whatsapp_template(
    conn: ConnectionLike,
    *,
    template_id: str,
    organization_id: str,
    bot_id: str,
    name: str,
    category: str,
    default_language: str,
    fallback_template_id: str | None,
    metadata_json: str,
    created_at: str,
    updated_at: str,
) -> None:
    execute(
        conn,
        """
        INSERT INTO whatsapp_templates
        (id, organization_id, bot_id, name, category, default_language, status, fallback_template_id, latest_version_id, approved_version_id, remote_template_id, last_sync_status, performance_score, metadata_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'draft', ?, NULL, NULL, NULL, 'draft', 0, ?, ?, ?)
        """,
        (template_id, organization_id, bot_id, name, category, default_language, fallback_template_id, metadata_json, created_at, updated_at),
    )


def approve_whatsapp_template(conn: ConnectionLike, *, template_id: str, version_id: str, updated_at: str) -> None:
    execute(conn, "UPDATE whatsapp_templates SET approved_version_id = ?, status = 'approved', updated_at = ? WHERE id = ?", (version_id, updated_at, template_id))


def insert_whatsapp_template_version(
    conn: ConnectionLike,
    *,
    version_id: str,
    template_id: str,
    organization_id: str,
    bot_id: str,
    version_number: int,
    state: str,
    language_code: str,
    category: str,
    body_text: str,
    header_type: str,
    header_text: str,
    footer_text: str,
    buttons_json: str,
    variables_json: str,
    assets_json: str,
    sample_values_json: str,
    lint_report_json: str,
    coverage_json: str,
    approval_status: str,
    fallback_template_id: str | None,
    metadata_json: str,
    created_at: str,
    updated_at: str,
) -> None:
    execute(
        conn,
        """
        INSERT INTO whatsapp_template_versions
        (id, template_id, organization_id, bot_id, version_number, state, language_code, category, body_text, header_type, header_text, footer_text, buttons_json, variables_json, assets_json, sample_values_json, lint_report_json, coverage_json, approval_status, remote_template_id, remote_status, remote_quality_rating, synced_at, published_at, rejection_reason, fallback_template_id, metadata_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, NULL, ?, ?, ?, ?)
        """,
        (
            version_id,
            template_id,
            organization_id,
            bot_id,
            version_number,
            state,
            language_code,
            category,
            body_text,
            header_type,
            header_text,
            footer_text,
            buttons_json,
            variables_json,
            assets_json,
            sample_values_json,
            lint_report_json,
            coverage_json,
            approval_status,
            fallback_template_id,
            metadata_json,
            created_at,
            updated_at,
        ),
    )


def update_whatsapp_template_version_tracking(
    conn: ConnectionLike,
    *,
    template_id: str,
    latest_version_id: str,
    approved_version_id: str | None,
    status: str,
    fallback_template_id: str | None,
    updated_at: str,
) -> None:
    execute(
        conn,
        "UPDATE whatsapp_templates SET latest_version_id = ?, approved_version_id = ?, status = ?, fallback_template_id = COALESCE(?, fallback_template_id), updated_at = ? WHERE id = ?",
        (latest_version_id, approved_version_id, status, fallback_template_id, updated_at, template_id),
    )


def update_whatsapp_template_version_approval(
    conn: ConnectionLike,
    *,
    version_id: str,
    approval_status: str,
    rejection_reason: str | None,
    remote_status: str | None,
    remote_quality_rating: str | None,
    updated_at: str,
    publish_now: bool,
) -> None:
    execute(
        conn,
        "UPDATE whatsapp_template_versions SET approval_status = ?, rejection_reason = ?, remote_status = COALESCE(?, remote_status), remote_quality_rating = COALESCE(?, remote_quality_rating), updated_at = ?, published_at = CASE WHEN ? = 1 THEN COALESCE(published_at, ?) ELSE published_at END WHERE id = ?",
        (approval_status, rejection_reason, remote_status, remote_quality_rating, updated_at, 1 if publish_now else 0, updated_at, version_id),
    )


def update_whatsapp_template_approval_state(
    conn: ConnectionLike,
    *,
    template_id: str,
    approved_version_id: str | None,
    status: str,
    last_sync_status: str | None,
    updated_at: str,
) -> None:
    execute(
        conn,
        "UPDATE whatsapp_templates SET approved_version_id = ?, status = ?, last_sync_status = COALESCE(?, last_sync_status), updated_at = ? WHERE id = ?",
        (approved_version_id, status, last_sync_status, updated_at, template_id),
    )


def create_whatsapp_template_sync_run(
    conn: ConnectionLike,
    *,
    row_id: str,
    template_id: str,
    version_id: str,
    organization_id: str,
    bot_id: str,
    action: str,
    request_json: str,
    started_at: str,
) -> dict:
    execute(
        conn,
        "INSERT INTO whatsapp_template_sync_runs (id, template_id, version_id, organization_id, bot_id, provider, action, status, request_json, response_json, validation_errors_json, started_at, finished_at) VALUES (?, ?, ?, ?, ?, 'meta', ?, 'running', ?, '{}', '[]', ?, NULL)",
        (row_id, template_id, version_id, organization_id, bot_id, action, request_json, started_at),
    )
    return fetch_one(conn, "SELECT * FROM whatsapp_template_sync_runs WHERE id = ?", (row_id,)) or {}


def mark_template_sync_run_lint_failed(conn: ConnectionLike, *, sync_run_id: str, validation_errors_json: str, response_json: str, finished_at: str) -> None:
    execute(conn, "UPDATE whatsapp_template_sync_runs SET status = 'failed', validation_errors_json = ?, finished_at = ?, response_json = ? WHERE id = ?", (validation_errors_json, finished_at, response_json, sync_run_id))


def update_template_last_sync_status(conn: ConnectionLike, *, template_id: str, last_sync_status: str, updated_at: str) -> None:
    execute(conn, "UPDATE whatsapp_templates SET last_sync_status = ?, updated_at = ? WHERE id = ?", (last_sync_status, updated_at, template_id))


def mark_template_version_sync_success(
    conn: ConnectionLike,
    *,
    version_id: str,
    approval_status: str,
    remote_template_id: str | None,
    remote_status: str,
    remote_quality_rating: str | None,
    synced_at: str,
) -> None:
    execute(
        conn,
        "UPDATE whatsapp_template_versions SET approval_status = ?, remote_template_id = ?, remote_status = ?, remote_quality_rating = COALESCE(?, remote_quality_rating), synced_at = ?, published_at = CASE WHEN ? = 'approved' THEN COALESCE(published_at, ?) ELSE published_at END, updated_at = ? WHERE id = ?",
        (approval_status, remote_template_id, remote_status, remote_quality_rating, synced_at, approval_status, synced_at, synced_at, version_id),
    )


def mark_template_sync_success(
    conn: ConnectionLike,
    *,
    template_id: str,
    remote_template_id: str | None,
    last_sync_status: str,
    approved_version_id: str | None,
    status: str,
    updated_at: str,
) -> None:
    execute(
        conn,
        "UPDATE whatsapp_templates SET remote_template_id = COALESCE(?, remote_template_id), last_sync_status = ?, approved_version_id = ?, status = ?, updated_at = ? WHERE id = ?",
        (remote_template_id, last_sync_status, approved_version_id, status, updated_at, template_id),
    )


def complete_template_sync_run(conn: ConnectionLike, *, sync_run_id: str, status: str, response_json: str, finished_at: str) -> None:
    execute(conn, "UPDATE whatsapp_template_sync_runs SET status = ?, response_json = ?, validation_errors_json = '[]', finished_at = ? WHERE id = ?", (status, response_json, finished_at, sync_run_id))


def mark_template_version_sync_error(conn: ConnectionLike, *, version_id: str, approval_status: str, remote_status: str, rejection_reason: str, updated_at: str) -> None:
    execute(conn, "UPDATE whatsapp_template_versions SET approval_status = ?, remote_status = ?, rejection_reason = ?, updated_at = ? WHERE id = ?", (approval_status, remote_status, rejection_reason, updated_at, version_id))


def fail_template_sync_run(conn: ConnectionLike, *, sync_run_id: str, response_json: str, validation_errors_json: str, finished_at: str) -> None:
    execute(conn, "UPDATE whatsapp_template_sync_runs SET status = 'failed', response_json = ?, validation_errors_json = ?, finished_at = ? WHERE id = ?", (response_json, validation_errors_json, finished_at, sync_run_id))


def list_template_candidate_rows(conn: ConnectionLike, *, organization_id: str, bot_id: str) -> list[dict]:
    return fetch_all(
        conn,
        """
        SELECT t.*, v.id AS version_id, v.version_number, v.language_code, v.category AS version_category, v.header_type, v.coverage_json, v.approval_status, v.fallback_template_id AS version_fallback_template_id, v.remote_status
        FROM whatsapp_templates t
        JOIN whatsapp_template_versions v ON v.id = COALESCE(t.approved_version_id, t.latest_version_id)
        WHERE t.organization_id = ? AND t.bot_id = ?
        ORDER BY COALESCE(t.performance_score, 0) DESC, t.updated_at DESC
        """,
        (organization_id, bot_id),
    )


def create_whatsapp_template_failover(
    conn: ConnectionLike,
    *,
    row_id: str,
    organization_id: str,
    bot_id: str,
    outbox_id: str | None,
    current_template_id: str | None,
    current_version_id: str | None,
    fallback_template_id: str | None,
    fallback_version_id: str,
    reason_code: str,
    source: str,
    payload_json: str,
    created_at: str,
) -> dict:
    execute(
        conn,
        "INSERT INTO whatsapp_template_failovers (id, organization_id, bot_id, outbox_id, current_template_id, current_version_id, fallback_template_id, fallback_version_id, reason_code, source, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (row_id, organization_id, bot_id, outbox_id, current_template_id, current_version_id, fallback_template_id, fallback_version_id, reason_code, source, payload_json, created_at),
    )
    return fetch_one(conn, "SELECT * FROM whatsapp_template_failovers WHERE id = ?", (row_id,)) or {}
