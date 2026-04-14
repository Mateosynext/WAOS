from __future__ import annotations

from typing import Any

from .utils import from_json


def ok(data: Any, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"ok": True, "data": data, "meta": meta or {}}


def count_row(row: dict[str, Any], *, fallback_kind: str) -> dict[str, Any]:
    kind = str(row.get("kind") or row.get("type") or row.get("status") or fallback_kind)
    status = str(row.get("status") or kind)
    return {**row, "kind": kind, "type": kind, "status": status, "count": int(row.get("count") or 0)}


def runtime_callback_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = from_json(row.get("payload_json"), {})
    response = from_json(row.get("response_json"), {})
    kind = str(row.get("callback_type") or row.get("kind") or row.get("type") or "callback")
    updated_at = row.get("updated_at") or row.get("delivered_at") or row.get("created_at")
    return {
        **row,
        "kind": kind,
        "type": kind,
        "health_status": row.get("health_status") or row.get("status"),
        "updated_at": updated_at,
        "last_run_at": row.get("last_run_at") or updated_at,
        "payload": payload,
        "response": response,
    }


def dead_letter_row(row: dict[str, Any], *, channel: str) -> dict[str, Any]:
    payload = from_json(row.get("payload_json"), {})
    detail = row.get("detail") or row.get("kind") or row.get("type") or row.get("id") or channel
    return {
        **row,
        "kind": channel,
        "type": row.get("kind") or row.get("type") or channel,
        "status": row.get("status") or "dead_letter",
        "detail": detail,
        "payload": payload,
        "error": row.get("last_error") or row.get("error"),
    }


def integration_sync_run_row(row: dict[str, Any]) -> dict[str, Any]:
    summary = from_json(row.get("summary_json"), {})
    error = from_json(row.get("error_json"), {})
    return {
        **row,
        "summary": summary,
        "error": error,
        "detail": row.get("detail") or summary.get("reason") or summary.get("mode") or summary.get("provider") or row.get("status"),
    }


def run_row(row: dict[str, Any]) -> dict[str, Any]:
    error = from_json(row.get("error_json"), {})
    input_data = from_json(row.get("input_json"), {})
    output_data = from_json(row.get("output_json"), {})
    summary = row.get("summary") or row.get("execution_id") or row.get("trace_id") or row.get("id")
    return {
        **row,
        "summary": summary,
        "detail": row.get("detail") or error.get("message") or row.get("source_type") or row.get("status") or summary,
        "input": input_data,
        "output": output_data,
        "error": error,
    }


def audit_log_row(row: dict[str, Any]) -> dict[str, Any]:
    details = from_json(row.get("details_json"), {})
    payload = from_json(row.get("payload_json"), {})
    message = row.get("message") or row.get("summary") or details.get("message") or payload.get("message")
    return {
        **row,
        "kind": row.get("kind") or row.get("event") or row.get("level"),
        "event": row.get("event") or row.get("kind") or row.get("event_type"),
        "summary": row.get("summary") or message,
        "message": message,
        "details": details,
        "payload": payload,
        "timestamp": row.get("timestamp") or row.get("created_at") or row.get("updated_at"),
    }


def build_row(row: dict[str, Any]) -> dict[str, Any]:
    validation = from_json(row.get("validation_json"), {})
    diff_summary = from_json(row.get("diff_summary_json"), {})
    artifact = from_json(row.get("artifact_json"), {})
    summary = row.get("summary") or diff_summary.get("summary") or diff_summary.get("label") or validation.get("summary") or row.get("id")
    return {
        **row,
        "summary": summary,
        "detail": row.get("detail") or row.get("notes") or diff_summary.get("detail") or summary,
        "validation": validation,
        "diff_summary": diff_summary,
        "artifact": artifact,
    }


def release_request_row(row: dict[str, Any]) -> dict[str, Any]:
    validation = from_json(row.get("validation_json"), {})
    diff_summary = from_json(row.get("diff_summary_json"), {})
    checklist = from_json(row.get("checklist_json"), {})
    summary = row.get("summary") or row.get("title") or row.get("notes") or diff_summary.get("summary") or validation.get("summary") or row.get("id")
    return {
        **row,
        "summary": summary,
        "validation": validation,
        "diff_summary": diff_summary,
        "checklist": checklist,
    }


def integration_event_row(row: dict[str, Any]) -> dict[str, Any]:
    request = from_json(row.get("request_json"), {})
    response = from_json(row.get("response_json"), {})
    error = from_json(row.get("error_json"), {})
    summary = row.get("summary") or error.get("message") or row.get("event_type") or row.get("status")
    return {
        **row,
        "kind": row.get("event_type") or row.get("kind") or "provider",
        "summary": summary,
        "detail": row.get("detail") or error.get("message") or response.get("message") or summary,
        "request": request,
        "response": response,
        "error": error,
        "timestamp": row.get("created_at") or row.get("updated_at"),
    }


def payment_row(row: dict[str, Any]) -> dict[str, Any]:
    metadata = from_json(row.get("metadata_json"), {})
    provider_response = from_json(row.get("provider_response_json"), {})
    return {
        **row,
        "reference": row.get("provider_reference") or row.get("external_payment_id") or row.get("id"),
        "metadata": metadata,
        "provider_response": provider_response,
        "checkout_url": row.get("payment_link_url"),
        "checkout_status": row.get("payment_link_status"),
        "provider_health": row.get("provider_status") or row.get("payment_link_status") or row.get("status"),
    }
