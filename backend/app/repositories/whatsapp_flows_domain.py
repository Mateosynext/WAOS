from __future__ import annotations

from typing import Any

from .base import ConnectionLike, execute, fetch_all, fetch_one


def get_whatsapp_flow(conn: ConnectionLike, flow_id: str) -> dict | None:
    return fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,))


def get_whatsapp_flow_version(conn: ConnectionLike, version_id: str) -> dict | None:
    return fetch_one(conn, "SELECT * FROM whatsapp_flow_versions WHERE id = ?", (version_id,))


def list_whatsapp_flow_versions(conn: ConnectionLike, flow_id: str) -> list[dict]:
    return fetch_all(conn, "SELECT * FROM whatsapp_flow_versions WHERE flow_id = ? ORDER BY version_number DESC, created_at DESC", (flow_id,))


def list_whatsapp_flow_publications(conn: ConnectionLike, flow_id: str, limit: int = 20) -> list[dict]:
    return fetch_all(conn, "SELECT * FROM whatsapp_flow_publications WHERE flow_id = ? ORDER BY started_at DESC LIMIT ?", (flow_id, limit))


def get_whatsapp_flow_version_for_flow(conn: ConnectionLike, *, version_id: str, flow_id: str) -> dict | None:
    return fetch_one(conn, "SELECT * FROM whatsapp_flow_versions WHERE id = ? AND flow_id = ?", (version_id, flow_id))


def get_latest_whatsapp_flow_version(conn: ConnectionLike, flow_id: str) -> dict | None:
    return fetch_one(conn, "SELECT * FROM whatsapp_flow_versions WHERE flow_id = ? ORDER BY version_number DESC LIMIT 1", (flow_id,))


def get_whatsapp_flow_experiment(conn: ConnectionLike, experiment_id: str) -> dict | None:
    return fetch_one(conn, "SELECT * FROM whatsapp_flow_experiments WHERE id = ?", (experiment_id,))


def get_active_whatsapp_flow_experiment(conn: ConnectionLike, flow_id: str) -> dict | None:
    return fetch_one(conn, "SELECT * FROM whatsapp_flow_experiments WHERE flow_id = ? AND status = 'active' ORDER BY updated_at DESC LIMIT 1", (flow_id,))


def get_whatsapp_flow_execution(conn: ConnectionLike, execution_id: str, flow_id: str | None = None) -> dict | None:
    if flow_id:
        return fetch_one(conn, "SELECT * FROM whatsapp_flow_executions WHERE id = ? AND flow_id = ?", (execution_id, flow_id))
    return fetch_one(conn, "SELECT * FROM whatsapp_flow_executions WHERE id = ?", (execution_id,))


def count_whatsapp_flow_execution_events(conn: ConnectionLike, execution_id: str) -> int:
    row = fetch_one(conn, "SELECT COUNT(*) AS value FROM whatsapp_flow_events WHERE execution_id = ?", (execution_id,)) or {}
    return int(row.get('value') or 0)


def get_whatsapp_flow_event(conn: ConnectionLike, event_id: str) -> dict | None:
    return fetch_one(conn, "SELECT * FROM whatsapp_flow_events WHERE id = ?", (event_id,))


def summarize_whatsapp_flow_analytics(conn: ConnectionLike, *, flow_id: str, where_clause: str, params: list) -> dict[str, list[dict]]:
    return {
        "events": fetch_all(conn, f"SELECT event_type, screen_id, variant, COUNT(*) AS total FROM whatsapp_flow_events {where_clause} GROUP BY event_type, screen_id, variant ORDER BY total DESC", params),
        "executions": fetch_all(conn, "SELECT status, assigned_variant, fallback_reason, COUNT(*) AS total FROM whatsapp_flow_executions WHERE flow_id = ? GROUP BY status, assigned_variant, fallback_reason ORDER BY total DESC", (flow_id,)),
        "versions": fetch_all(conn, "SELECT version_id, event_type, COUNT(*) AS total FROM whatsapp_flow_events WHERE flow_id = ? GROUP BY version_id, event_type ORDER BY total DESC", (flow_id,)),
    }


def insert_whatsapp_flow(
    conn: ConnectionLike,
    *,
    flow_id: str,
    organization_id: str,
    bot_id: str,
    name: str,
    flow_type: str,
    status: str,
    language: str,
    definition_json: str,
    metadata_json: str,
    fallback_json: str,
    runtime_config_json: str,
    current_version_id: str,
    runtime_endpoint: str,
    created_at: str,
    updated_at: str,
) -> None:
    execute(
        conn,
        """
        INSERT INTO whatsapp_flows (
            id, organization_id, bot_id, name, flow_type, status, language, definition_json, metadata_json,
            remote_flow_id, remote_status, remote_details_json, fallback_json, runtime_config_json,
            current_version_id, published_version_id, runtime_endpoint, remote_last_synced_at, remote_last_published_at,
            last_sync_error, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 'not_synced', '{}', ?, ?, ?, NULL, ?, NULL, NULL, NULL, ?, ?)
        """,
        (
            flow_id, organization_id, bot_id, name, flow_type, status, language, definition_json, metadata_json,
            fallback_json, runtime_config_json, current_version_id, runtime_endpoint, created_at, updated_at,
        ),
    )


def insert_whatsapp_flow_version(
    conn: ConnectionLike,
    *,
    version_id: str,
    flow_id: str,
    organization_id: str,
    bot_id: str,
    version_number: int,
    state: str,
    flow_json: str,
    metadata_json: str,
    compatibility_json: str,
    rollout_json: str,
    cloned_from_version_id: str | None,
    created_at: str,
    updated_at: str,
) -> None:
    execute(
        conn,
        """
        INSERT INTO whatsapp_flow_versions (
            id, flow_id, organization_id, bot_id, version_number, state, flow_json, metadata_json,
            compatibility_json, rollout_json, remote_asset_status, validation_errors_json,
            cloned_from_version_id, created_at, updated_at, published_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', '[]', ?, ?, ?, NULL)
        """,
        (version_id, flow_id, organization_id, bot_id, version_number, state, flow_json, metadata_json, compatibility_json, rollout_json, cloned_from_version_id, created_at, updated_at),
    )


def update_whatsapp_flow_current_version(conn: ConnectionLike, *, flow_id: str, version_id: str, updated_at: str) -> None:
    execute(conn, "UPDATE whatsapp_flows SET current_version_id = ?, updated_at = ? WHERE id = ?", (version_id, updated_at, flow_id))


def insert_whatsapp_flow_experiment(
    conn: ConnectionLike,
    *,
    row_id: str,
    flow_id: str,
    organization_id: str,
    bot_id: str,
    version_a_id: str,
    version_b_id: str,
    rollout_percentage: int,
    status: str,
    note: str | None,
    created_at: str,
    updated_at: str,
) -> None:
    execute(conn, "INSERT INTO whatsapp_flow_experiments (id, flow_id, organization_id, bot_id, version_a_id, version_b_id, rollout_percentage, status, note, metrics_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '{}', ?, ?)", (row_id, flow_id, organization_id, bot_id, version_a_id, version_b_id, rollout_percentage, status, note, created_at, updated_at))


def update_whatsapp_flow_experiment_metrics(conn: ConnectionLike, *, experiment_id: str, metrics_json: str, updated_at: str) -> None:
    execute(conn, "UPDATE whatsapp_flow_experiments SET metrics_json = ?, updated_at = ? WHERE id = ?", (metrics_json, updated_at, experiment_id))


def create_whatsapp_flow_publication(
    conn: ConnectionLike,
    *,
    row_id: str,
    flow_id: str,
    version_id: str,
    organization_id: str,
    bot_id: str,
    action: str,
    remote_flow_id: str | None,
    request_json: str,
    started_at: str,
) -> None:
    execute(conn, "INSERT INTO whatsapp_flow_publications (id, flow_id, version_id, organization_id, bot_id, provider, action, status, remote_flow_id, request_json, response_json, validation_errors_json, started_at, finished_at) VALUES (?, ?, ?, ?, ?, 'meta', ?, 'running', ?, ?, '{}', '[]', ?, NULL)", (row_id, flow_id, version_id, organization_id, bot_id, action, remote_flow_id, request_json, started_at))


def finish_whatsapp_flow_publication(conn: ConnectionLike, *, publication_id: str, status: str, remote_flow_id: str | None, response_json: str, validation_errors_json: str, finished_at: str) -> None:
    execute(conn, "UPDATE whatsapp_flow_publications SET status = ?, remote_flow_id = COALESCE(?, remote_flow_id), response_json = ?, validation_errors_json = ?, finished_at = ? WHERE id = ?", (status, remote_flow_id, response_json, validation_errors_json, finished_at, publication_id))


def set_whatsapp_flow_remote_draft(conn: ConnectionLike, *, flow_id: str, remote_flow_id: str, updated_at: str) -> None:
    execute(conn, "UPDATE whatsapp_flows SET remote_flow_id = ?, remote_status = 'draft', updated_at = ? WHERE id = ?", (remote_flow_id, updated_at, flow_id))


def update_whatsapp_flow_version_validation(conn: ConnectionLike, *, version_id: str, remote_asset_status: str, validation_errors_json: str, updated_at: str) -> None:
    execute(conn, "UPDATE whatsapp_flow_versions SET remote_asset_status = ?, validation_errors_json = ?, updated_at = ? WHERE id = ?", (remote_asset_status, validation_errors_json, updated_at, version_id))


def mark_whatsapp_flow_publication_success(
    conn: ConnectionLike,
    *,
    flow_id: str,
    remote_flow_id: str,
    remote_status: str,
    remote_details_json: str,
    current_version_id: str,
    published_version_id: str,
    runtime_endpoint: str | None,
    remote_last_synced_at: str,
    remote_last_published_at: str,
    updated_at: str,
) -> None:
    execute(
        conn,
        """
        UPDATE whatsapp_flows
        SET status = 'active', remote_flow_id = ?, remote_status = ?, remote_details_json = ?,
            current_version_id = ?, published_version_id = ?, runtime_endpoint = ?, remote_last_synced_at = ?,
            remote_last_published_at = ?, last_sync_error = NULL, updated_at = ?
        WHERE id = ?
        """,
        (remote_flow_id, remote_status, remote_details_json, current_version_id, published_version_id, runtime_endpoint, remote_last_synced_at, remote_last_published_at, updated_at, flow_id),
    )


def mark_whatsapp_flow_version_published(conn: ConnectionLike, *, version_id: str, published_at: str, updated_at: str) -> None:
    execute(conn, "UPDATE whatsapp_flow_versions SET state = 'published', remote_asset_status = 'published', published_at = ?, updated_at = ? WHERE id = ?", (published_at, updated_at, version_id))


def update_whatsapp_flow_last_sync_error(conn: ConnectionLike, *, flow_id: str, last_sync_error_json: str, updated_at: str) -> None:
    execute(conn, "UPDATE whatsapp_flows SET last_sync_error = ?, updated_at = ? WHERE id = ?", (last_sync_error_json, updated_at, flow_id))


def update_whatsapp_flow_sync_snapshot(conn: ConnectionLike, *, flow_id: str, remote_status: str, remote_details_json: str, remote_last_synced_at: str, updated_at: str) -> None:
    execute(conn, "UPDATE whatsapp_flows SET remote_status = ?, remote_details_json = ?, remote_last_synced_at = ?, last_sync_error = NULL, updated_at = ? WHERE id = ?", (remote_status, remote_details_json, remote_last_synced_at, updated_at, flow_id))


def mark_whatsapp_flow_version_rollback_candidate(conn: ConnectionLike, *, version_id: str, updated_at: str) -> None:
    execute(conn, "UPDATE whatsapp_flow_versions SET state = 'rollback_candidate', updated_at = ? WHERE id = ?", (updated_at, version_id))


def create_whatsapp_flow_event(
    conn: ConnectionLike,
    *,
    row_id: str,
    flow_id: str,
    version_id: str | None,
    execution_id: str | None,
    organization_id: str,
    bot_id: str,
    event_type: str,
    screen_id: str | None,
    step_index: int | None,
    variant: str | None,
    payload_json: str,
    created_at: str,
) -> dict:
    execute(conn, "INSERT INTO whatsapp_flow_events (id, flow_id, version_id, execution_id, organization_id, bot_id, event_type, screen_id, step_index, variant, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (row_id, flow_id, version_id, execution_id, organization_id, bot_id, event_type, screen_id, step_index, variant, payload_json, created_at))
    return fetch_one(conn, "SELECT * FROM whatsapp_flow_events WHERE id = ?", (row_id,)) or {}


def create_whatsapp_flow_execution(
    conn: ConnectionLike,
    *,
    execution_id: str,
    flow_id: str,
    version_id: str,
    organization_id: str,
    bot_id: str,
    conversation_id: str | None,
    contact_id: str | None,
    flow_token: str,
    assigned_variant: str | None,
    status: str,
    current_screen_id: str | None,
    fallback_reason: str | None,
    fallback_mode: str | None,
    context_json: str,
    started_at: str,
    last_event_at: str,
) -> None:
    execute(
        conn,
        """
        INSERT INTO whatsapp_flow_executions (
            id, flow_id, version_id, organization_id, bot_id, conversation_id, contact_id, flow_token,
            assigned_variant, status, current_screen_id, fallback_reason, fallback_mode, context_json,
            result_json, channel_message_id, started_at, completed_at, last_event_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '{}', NULL, ?, NULL, ?)
        """,
        (execution_id, flow_id, version_id, organization_id, bot_id, conversation_id, contact_id, flow_token, assigned_variant, status, current_screen_id, fallback_reason, fallback_mode, context_json, started_at, last_event_at),
    )


def update_whatsapp_flow_execution_progress(
    conn: ConnectionLike,
    *,
    execution_id: str,
    current_screen_id: str | None,
    status: str,
    result_json: str,
    completed_at: str | None,
    last_event_at: str,
) -> None:
    execute(conn, "UPDATE whatsapp_flow_executions SET current_screen_id = ?, status = ?, result_json = ?, completed_at = ?, last_event_at = ? WHERE id = ?", (current_screen_id, status, result_json, completed_at, last_event_at, execution_id))


def touch_whatsapp_flow_execution(conn: ConnectionLike, *, execution_id: str, last_event_at: str) -> None:
    execute(conn, "UPDATE whatsapp_flow_executions SET last_event_at = ? WHERE id = ?", (last_event_at, execution_id))
