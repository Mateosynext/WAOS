from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx

from ..config import settings
from ..db import table_exists
from ..platform import store_secret
from ..repositories import get_whatsapp_number_for_bot
from ..repositories.whatsapp_flows_domain import (
    count_whatsapp_flow_execution_events,
    create_whatsapp_flow_event,
    create_whatsapp_flow_execution,
    create_whatsapp_flow_publication,
    get_active_whatsapp_flow_experiment,
    get_latest_whatsapp_flow_version,
    get_whatsapp_flow,
    get_whatsapp_flow_event,
    get_whatsapp_flow_execution,
    get_whatsapp_flow_experiment,
    get_whatsapp_flow_version,
    get_whatsapp_flow_version_for_flow,
    insert_whatsapp_flow,
    insert_whatsapp_flow_experiment,
    insert_whatsapp_flow_version,
    list_whatsapp_flow_publications,
    list_whatsapp_flow_versions,
    mark_whatsapp_flow_publication_success,
    mark_whatsapp_flow_version_published,
    mark_whatsapp_flow_version_rollback_candidate,
    set_whatsapp_flow_remote_draft,
    summarize_whatsapp_flow_analytics,
    touch_whatsapp_flow_execution,
    update_whatsapp_flow_current_version,
    update_whatsapp_flow_execution_progress,
    update_whatsapp_flow_experiment_metrics,
    update_whatsapp_flow_last_sync_error,
    update_whatsapp_flow_sync_snapshot,
    update_whatsapp_flow_version_validation,
    finish_whatsapp_flow_publication,
)
from ..utils import from_json, new_id, to_json, utcnow_iso
from ..whatsapp import resolve_whatsapp_access_token

FLOW_DETAIL_FIELDS = "id,name,categories,preview,status,validation_errors,json_version,data_api_version,data_channel_uri,whatsapp_business_account,application"

DEFAULT_FALLBACK = {
    "mode": "human_handoff",
    "message": "Tu app de WhatsApp no soporta este flow. Te conectáremos con una persona para continuar.",
}


def _json(row: dict[str, Any] | None, key: str, default: Any) -> Any:
    if not row:
        return default
    return from_json(row.get(key), default)


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(to_json(value).encode("utf-8")).hexdigest()


class MetaFlowAPIError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


class MetaFlowClient:
    def __init__(self, conn, *, organization_id: str, bot_id: str, waba_id: str | None = None, phone_number_id: str | None = None):
        number = get_whatsapp_number_for_bot(conn, bot_id)
        if not number:
            raise ValueError("whatsapp_number_not_configured")
        access_token = resolve_whatsapp_access_token(conn, organization_id=organization_id, bot_id=bot_id)
        if not access_token:
            raise ValueError("missing_whatsapp_access_token")
        self.organization_id = organization_id
        self.bot_id = bot_id
        self.number = number
        self.access_token = access_token
        self.waba_id = waba_id or number.get("waba_id")
        self.phone_number_id = phone_number_id or number.get("phone_number_id")
        if not self.waba_id:
            raise ValueError("whatsapp_waba_id_required")
        if not self.phone_number_id:
            raise ValueError("whatsapp_phone_number_id_required")

    def _request(self, method: str, path: str, *, json_body: dict[str, Any] | None = None, params: dict[str, Any] | None = None, files: Any = None, data: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{settings.meta_graph_api_base.rstrip('/')}/{path.lstrip('/')}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        if files is None:
            headers["Content-Type"] = "application/json"
        response = httpx.request(method, url, headers=headers, json=json_body if files is None else None, params=params, files=files, data=data, timeout=30.0)
        try:
            payload = response.json()
        except Exception:
            payload = {"raw_text": response.text}
        if response.status_code >= 400:
            raise MetaFlowAPIError("meta_flow_provider_error", status_code=response.status_code, payload=payload)
        return payload

    def create_flow(self, *, name: str, categories: list[str], endpoint_uri: str | None = None, clone_flow_id: str | None = None) -> dict[str, Any]:
        body = {"name": name, "categories": categories or ["OTHER"]}
        if endpoint_uri:
            body["endpoint_uri"] = endpoint_uri
        if clone_flow_id:
            body["clone_flow_id"] = clone_flow_id
        return self._request("POST", f"{self.waba_id}/flows", json_body=body)

    def list_flows(self) -> dict[str, Any]:
        return self._request("GET", f"{self.waba_id}/flows")

    def get_flow(self, remote_flow_id: str) -> dict[str, Any]:
        return self._request("GET", remote_flow_id, params={"fields": FLOW_DETAIL_FIELDS})

    def get_preview(self, remote_flow_id: str) -> dict[str, Any]:
        return self._request("GET", remote_flow_id, params={"fields": "preview.invalidate(false)"})

    def upload_flow_json(self, remote_flow_id: str, *, flow_json: dict[str, Any]) -> dict[str, Any]:
        serialized = json.dumps(flow_json, ensure_ascii=False).encode("utf-8")
        files = {"file": ("flow.json", serialized, "application/json")}
        return self._request("POST", f"{remote_flow_id}/assets", files=files, data={"name": "flow.json", "asset_type": "FLOW_JSON"})

    def publish_flow(self, remote_flow_id: str) -> dict[str, Any]:
        return self._request("POST", f"{remote_flow_id}/publish", json_body={})

    def update_metadata(self, remote_flow_id: str, *, name: str | None = None, categories: list[str] | None = None, endpoint_uri: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if name:
            body["name"] = name
        if categories:
            body["categories"] = categories
        if endpoint_uri:
            body["endpoint_uri"] = endpoint_uri
        return self._request("POST", remote_flow_id, json_body=body)

    def deprecate_flow(self, remote_flow_id: str) -> dict[str, Any]:
        return self._request("POST", f"{remote_flow_id}/deprecate", json_body={})

    def set_encryption_public_key(self, *, business_public_key: str) -> dict[str, Any]:
        return self._request("POST", f"{self.phone_number_id}/whatsapp_business_encryption", json_body={"business_public_key": business_public_key})

    def get_endpoint_metric(self, remote_flow_id: str, *, since: str, until: str, granularity: str = "DAY") -> dict[str, Any]:
        fields = f"metric.name(ENDPOINT_AVAILABILITY).granularity({granularity}).since({since}).until({until})"
        return self._request("GET", remote_flow_id, params={"fields": fields})


def _default_flow_json(name: str, screens: list[dict[str, Any]]) -> dict[str, Any]:
    normalized_screens: list[dict[str, Any]] = []
    for index, screen in enumerate(screens or [], start=1):
        screen_id = screen.get("id") or f"SCREEN_{index}"
        title = screen.get("title") or f"Pantalla {index}"
        components = list(screen.get("components") or [])
        normalized_screens.append(
            {
                "id": screen_id,
                "title": title,
                "data": screen.get("data") or {},
                "layout": screen.get("layout") or {"type": "SingleColumnLayout", "children": [{"type": "TextHeading", "text": title}, {"type": "TextBody", "text": ", ".join(components) if components else "Completa el flujo."}]},
                "terminal": bool(screen.get("terminal") or index == len(screens or [])),
            }
        )
    if not normalized_screens:
        normalized_screens = [
            {
                "id": "SCREEN_START",
                "title": name,
                "data": {},
                "layout": {"type": "SingleColumnLayout", "children": [{"type": "TextHeading", "text": name}, {"type": "TextBody", "text": "Flow draft generado por WAOS. Sustituye este JSON por uno compatible con Meta antes de publicar en producción."}]},
                "terminal": True,
            }
        ]
    return {
        "version": "7.1",
        "data_api_version": "3.0",
        "routing_model": {screen["id"]: [] for screen in normalized_screens},
        "screens": normalized_screens,
    }


def _serialize_flow_version(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "flow_json": _json(row, "flow_json", {}),
        "metadata": _json(row, "metadata_json", {}),
        "compatibility": _json(row, "compatibility_json", {}),
        "rollout": _json(row, "rollout_json", {}),
        "validation_errors": _json(row, "validation_errors_json", []),
    }


def _serialize_publication(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "request": _json(row, "request_json", {}),
        "response": _json(row, "response_json", {}),
        "validation_errors": _json(row, "validation_errors_json", []),
    }


def serialize_flow(conn, row: dict[str, Any], *, include_versions: bool = False, include_publications: bool = False) -> dict[str, Any]:
    payload = {
        **row,
        "definition": _json(row, "definition_json", {}),
        "metadata": _json(row, "metadata_json", {}),
        "fallback": _json(row, "fallback_json", DEFAULT_FALLBACK),
        "remote_details": _json(row, "remote_details_json", {}),
        "runtime_config": _json(row, "runtime_config_json", {}),
    }
    if include_versions and table_exists(conn, "whatsapp_flow_versions"):
        versions = list_whatsapp_flow_versions(conn, row["id"])
        payload["versions"] = [_serialize_flow_version(item) for item in versions]
    if include_publications and table_exists(conn, "whatsapp_flow_publications"):
        publications = list_whatsapp_flow_publications(conn, row["id"], limit=20)
        payload["publications"] = [_serialize_publication(item) for item in publications]
    return payload


def create_whatsapp_flow(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    name: str,
    flow_type: str,
    language: str = "es",
    status: str = "draft",
    screens: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
    flow_json: dict[str, Any] | None = None,
    categories: list[str] | None = None,
    endpoint_uri: str | None = None,
    fallback: dict[str, Any] | None = None,
    runtime_config: dict[str, Any] | None = None,
    compatibility: dict[str, Any] | None = None,
) -> dict[str, Any]:
    flow_id = new_id("flow")
    version_id = new_id("flowv")
    now = utcnow_iso()
    categories = categories or [flow_type.upper() if flow_type else "OTHER"]
    runtime_endpoint = endpoint_uri or f"{settings.api_base_url.rstrip('/')}/api/v1/whatsapp/flows/{flow_id}/runtime"
    definition = {
        "type": flow_type,
        "screens": screens or [
            {"id": "screen_1", "title": "Inicio", "components": ["text", "input", "cta"]},
            {"id": "screen_2", "title": "Confirmación", "components": ["summary", "submit"], "terminal": True},
        ],
        "categories": categories,
        "endpoint_uri": runtime_endpoint,
    }
    insert_whatsapp_flow(
        conn,
        flow_id=flow_id,
        organization_id=organization_id,
        bot_id=bot_id,
        name=name,
        flow_type=flow_type,
        status=status,
        language=language,
        definition_json=to_json(definition),
        metadata_json=to_json(metadata or {}),
        fallback_json=to_json(fallback or DEFAULT_FALLBACK),
        runtime_config_json=to_json(runtime_config or {}),
        current_version_id=version_id,
        runtime_endpoint=runtime_endpoint,
        created_at=now,
        updated_at=now,
    )
    version_flow_json = flow_json or _default_flow_json(name, definition["screens"])
    insert_whatsapp_flow_version(
        conn,
        version_id=version_id,
        flow_id=flow_id,
        organization_id=organization_id,
        bot_id=bot_id,
        version_number=1,
        state="draft",
        flow_json=to_json(version_flow_json),
        metadata_json=to_json({"categories": categories, "endpoint_uri": runtime_endpoint}),
        compatibility_json=to_json(compatibility or {}),
        rollout_json=to_json({}),
        cloned_from_version_id=None,
        created_at=now,
        updated_at=now,
    )
    row = get_whatsapp_flow(conn, flow_id) or {}
    return serialize_flow(conn, row, include_versions=True)


def create_whatsapp_flow_version(
    conn,
    *,
    flow_id: str,
    actor_user_id: str | None = None,
    flow_json: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    compatibility: dict[str, Any] | None = None,
    cloned_from_version_id: str | None = None,
) -> dict[str, Any]:
    flow = get_whatsapp_flow(conn, flow_id)
    if not flow:
        raise ValueError("whatsapp_flow_not_found")
    current = get_latest_whatsapp_flow_version(conn, flow_id)
    next_version = int(current.get("version_number") or 0) + 1 if current else 1
    version_id = new_id("flowv")
    now = utcnow_iso()
    base_json = flow_json or _json(current, "flow_json", _json(flow, "definition_json", {}))
    insert_whatsapp_flow_version(
        conn,
        version_id=version_id,
        flow_id=flow_id,
        organization_id=flow["organization_id"],
        bot_id=flow["bot_id"],
        version_number=next_version,
        state="draft",
        flow_json=to_json(base_json),
        metadata_json=to_json(metadata or _json(current, "metadata_json", {})),
        compatibility_json=to_json(compatibility or _json(current, "compatibility_json", {})),
        rollout_json=to_json({}),
        cloned_from_version_id=cloned_from_version_id,
        created_at=now,
        updated_at=now,
    )
    update_whatsapp_flow_current_version(conn, flow_id=flow_id, version_id=version_id, updated_at=now)
    return _serialize_flow_version(get_whatsapp_flow_version(conn, version_id) or {})


def create_flow_experiment(
    conn,
    *,
    flow_id: str,
    version_a_id: str,
    version_b_id: str,
    rollout_percentage: int = 50,
    status: str = "active",
    note: str | None = None,
) -> dict[str, Any]:
    flow = get_whatsapp_flow(conn, flow_id)
    if not flow:
        raise ValueError("whatsapp_flow_not_found")
    row_id = new_id("flowexp")
    now = utcnow_iso()
    insert_whatsapp_flow_experiment(
        conn,
        row_id=row_id,
        flow_id=flow_id,
        organization_id=flow["organization_id"],
        bot_id=flow["bot_id"],
        version_a_id=version_a_id,
        version_b_id=version_b_id,
        rollout_percentage=max(1, min(99, rollout_percentage)),
        status=status,
        note=note,
        created_at=now,
        updated_at=now,
    )
    return get_whatsapp_flow_experiment(conn, row_id) or {}


def _get_active_experiment(conn, *, flow_id: str) -> dict[str, Any] | None:
    if not table_exists(conn, "whatsapp_flow_experiments"):
        return None
    return get_active_whatsapp_flow_experiment(conn, flow_id)


def _assign_experiment_variant(conn, *, flow: dict[str, Any], conversation_id: str | None, contact_id: str | None, flow_token: str | None) -> tuple[str | None, str | None]:
    experiment = _get_active_experiment(conn, flow_id=flow["id"])
    if not experiment:
        return None, flow.get("published_version_id") or flow.get("current_version_id")
    subject = conversation_id or contact_id or flow_token or flow["id"]
    bucket = int(hashlib.sha256(subject.encode("utf-8")).hexdigest(), 16) % 100
    variant = "A" if bucket < int(experiment.get("rollout_percentage") or 50) else "B"
    version_id = experiment.get("version_a_id") if variant == "A" else experiment.get("version_b_id")
    metrics = _json(experiment, "metrics_json", {})
    bucket_key = "a_assignments" if variant == "A" else "b_assignments"
    metrics[bucket_key] = int(metrics.get(bucket_key) or 0) + 1
    update_whatsapp_flow_experiment_metrics(conn, experiment_id=experiment["id"], metrics_json=to_json(metrics), updated_at=utcnow_iso())
    return variant, version_id


def _create_publication_run(conn, *, flow: dict[str, Any], version_id: str, action: str, request_payload: dict[str, Any] | None = None) -> str:
    row_id = new_id("flowpub")
    create_whatsapp_flow_publication(
        conn,
        row_id=row_id,
        flow_id=flow["id"],
        version_id=version_id,
        organization_id=flow["organization_id"],
        bot_id=flow["bot_id"],
        action=action,
        remote_flow_id=flow.get("remote_flow_id"),
        request_json=to_json(request_payload or {}),
        started_at=utcnow_iso(),
    )
    return row_id


def _finish_publication_run(conn, *, publication_id: str, status: str, remote_flow_id: str | None = None, response_payload: dict[str, Any] | None = None, validation_errors: list[dict[str, Any]] | None = None) -> None:
    finish_whatsapp_flow_publication(conn, publication_id=publication_id, status=status, remote_flow_id=remote_flow_id, response_json=to_json(response_payload or {}), validation_errors_json=to_json(validation_errors or []), finished_at=utcnow_iso())


def publish_whatsapp_flow(
    conn,
    *,
    flow_id: str,
    version_id: str | None = None,
    actor_user_id: str | None = None,
    register_encryption_public_key: str | None = None,
) -> dict[str, Any]:
    flow = get_whatsapp_flow(conn, flow_id)
    if not flow:
        raise ValueError("whatsapp_flow_not_found")
    version = get_whatsapp_flow_version_for_flow(conn, version_id=version_id or flow.get("current_version_id"), flow_id=flow_id)
    if not version:
        raise ValueError("whatsapp_flow_version_not_found")
    flow_json = _json(version, "flow_json", {})
    publication_id = _create_publication_run(conn, flow=flow, version_id=version["id"], action="publish", request_payload={"register_encryption": bool(register_encryption_public_key)})
    client = MetaFlowClient(conn, organization_id=flow["organization_id"], bot_id=flow["bot_id"])
    remote_flow_id = flow.get("remote_flow_id")
    metadata = _json(version, "metadata_json", {})
    categories = metadata.get("categories") or [flow["flow_type"].upper()]
    endpoint_uri = metadata.get("endpoint_uri") or flow.get("runtime_endpoint")
    try:
        if register_encryption_public_key:
            client.set_encryption_public_key(business_public_key=register_encryption_public_key)
            store_secret(conn, organization_id=flow["organization_id"], bot_id=flow["bot_id"], scope="bot", key_name="META_FLOW_PUBLIC_KEY", secret_value=register_encryption_public_key)
        if not remote_flow_id:
            created = client.create_flow(name=flow["name"], categories=categories, endpoint_uri=endpoint_uri)
            remote_flow_id = str(created.get("id") or "")
            if not remote_flow_id:
                raise MetaFlowAPIError("meta_flow_create_missing_id", payload=created)
            set_whatsapp_flow_remote_draft(conn, flow_id=flow_id, remote_flow_id=remote_flow_id, updated_at=utcnow_iso())
        asset_result = client.upload_flow_json(remote_flow_id, flow_json=flow_json)
        validation_errors = asset_result.get("validation_errors") or []
        update_whatsapp_flow_version_validation(conn, version_id=version["id"], remote_asset_status="validated" if not validation_errors else "validation_failed", validation_errors_json=to_json(validation_errors), updated_at=utcnow_iso())
        if validation_errors:
            _finish_publication_run(conn, publication_id=publication_id, status="validation_failed", remote_flow_id=remote_flow_id, response_payload=asset_result, validation_errors=validation_errors)
            raise MetaFlowAPIError("meta_flow_validation_failed", payload=asset_result)
        publish_result = client.publish_flow(remote_flow_id)
        remote_details = client.get_flow(remote_flow_id)
        preview = client.get_preview(remote_flow_id)
        now = utcnow_iso()
        mark_whatsapp_flow_publication_success(
            conn,
            flow_id=flow_id,
            remote_flow_id=remote_flow_id,
            remote_status=remote_details.get("status") or "published",
            remote_details_json=to_json({"detail": remote_details, "preview": preview}),
            current_version_id=version["id"],
            published_version_id=version["id"],
            runtime_endpoint=endpoint_uri,
            remote_last_synced_at=now,
            remote_last_published_at=now,
            updated_at=now,
        )
        mark_whatsapp_flow_version_published(conn, version_id=version["id"], published_at=now, updated_at=now)
        _finish_publication_run(conn, publication_id=publication_id, status="published", remote_flow_id=remote_flow_id, response_payload={"asset": asset_result, "publish": publish_result, "detail": remote_details, "preview": preview})
    except MetaFlowAPIError as exc:
        _finish_publication_run(conn, publication_id=publication_id, status="failed", remote_flow_id=remote_flow_id, response_payload=exc.payload)
        update_whatsapp_flow_last_sync_error(conn, flow_id=flow_id, last_sync_error_json=to_json({"status_code": exc.status_code, "payload": exc.payload}), updated_at=utcnow_iso())
        raise
    row = get_whatsapp_flow(conn, flow_id) or flow
    return serialize_flow(conn, row, include_versions=True, include_publications=True)


def sync_whatsapp_flow(conn, *, flow_id: str) -> dict[str, Any]:
    flow = get_whatsapp_flow(conn, flow_id)
    if not flow:
        raise ValueError("whatsapp_flow_not_found")
    if not flow.get("remote_flow_id"):
        raise ValueError("whatsapp_flow_not_published")
    client = MetaFlowClient(conn, organization_id=flow["organization_id"], bot_id=flow["bot_id"])
    publication_id = _create_publication_run(conn, flow=flow, version_id=flow.get("published_version_id") or flow.get("current_version_id"), action="sync")
    try:
        remote_details = client.get_flow(flow["remote_flow_id"])
        preview = client.get_preview(flow["remote_flow_id"])
        update_whatsapp_flow_sync_snapshot(
            conn,
            flow_id=flow_id,
            remote_status=remote_details.get("status") or flow.get("remote_status") or "unknown",
            remote_details_json=to_json({"detail": remote_details, "preview": preview}),
            remote_last_synced_at=utcnow_iso(),
            updated_at=utcnow_iso(),
        )
        _finish_publication_run(conn, publication_id=publication_id, status="synced", remote_flow_id=flow["remote_flow_id"], response_payload={"detail": remote_details, "preview": preview})
    except MetaFlowAPIError as exc:
        _finish_publication_run(conn, publication_id=publication_id, status="failed", remote_flow_id=flow["remote_flow_id"], response_payload=exc.payload)
        update_whatsapp_flow_last_sync_error(conn, flow_id=flow_id, last_sync_error_json=to_json({"status_code": exc.status_code, "payload": exc.payload}), updated_at=utcnow_iso())
        raise
    refreshed = get_whatsapp_flow(conn, flow_id) or flow
    return serialize_flow(conn, refreshed, include_versions=True, include_publications=True)


def rollback_whatsapp_flow(conn, *, flow_id: str, target_version_id: str, register_encryption_public_key: str | None = None) -> dict[str, Any]:
    flow = get_whatsapp_flow(conn, flow_id)
    if not flow:
        raise ValueError("whatsapp_flow_not_found")
    target = get_whatsapp_flow_version_for_flow(conn, version_id=target_version_id, flow_id=flow_id)
    if not target:
        raise ValueError("whatsapp_flow_version_not_found")
    cloned = create_whatsapp_flow_version(
        conn,
        flow_id=flow_id,
        flow_json=_json(target, "flow_json", {}),
        metadata=_json(target, "metadata_json", {}),
        compatibility=_json(target, "compatibility_json", {}),
        cloned_from_version_id=target_version_id,
    )
    mark_whatsapp_flow_version_rollback_candidate(conn, version_id=cloned["id"], updated_at=utcnow_iso())
    return publish_whatsapp_flow(conn, flow_id=flow_id, version_id=cloned["id"], register_encryption_public_key=register_encryption_public_key)


def _record_flow_event(
    conn,
    *,
    flow: dict[str, Any],
    version_id: str | None,
    execution_id: str | None,
    event_type: str,
    screen_id: str | None = None,
    step_index: int | None = None,
    variant: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row_id = new_id("flowevt")
    return create_whatsapp_flow_event(
        conn,
        row_id=row_id,
        flow_id=flow["id"],
        version_id=version_id,
        execution_id=execution_id,
        organization_id=flow["organization_id"],
        bot_id=flow["bot_id"],
        event_type=event_type,
        screen_id=screen_id,
        step_index=step_index,
        variant=variant,
        payload_json=to_json(payload or {}),
        created_at=utcnow_iso(),
    )


def execute_whatsapp_flow(
    conn,
    *,
    flow_id: str,
    conversation_id: str | None,
    contact_id: str | None,
    flow_token: str | None = None,
    version_id: str | None = None,
    client_capabilities: dict[str, Any] | None = None,
    source: str = "api",
    send_message: bool = False,
) -> dict[str, Any]:
    flow = get_whatsapp_flow(conn, flow_id)
    if not flow:
        raise ValueError("whatsapp_flow_not_found")
    assigned_variant, experiment_version_id = _assign_experiment_variant(conn, flow=flow, conversation_id=conversation_id, contact_id=contact_id, flow_token=flow_token)
    selected_version_id = version_id or experiment_version_id or flow.get("published_version_id") or flow.get("current_version_id")
    version = get_whatsapp_flow_version_for_flow(conn, version_id=selected_version_id, flow_id=flow_id)
    if not version:
        raise ValueError("whatsapp_flow_version_not_found")
    capabilities = client_capabilities or {}
    compatibility = _json(version, "compatibility_json", {})
    flow_message_version = int(capabilities.get("flow_message_version") or 3)
    min_supported = int(compatibility.get("min_flow_message_version") or 3)
    supports_flows = capabilities.get("supports_flows", True)
    fallback = _json(flow, "fallback_json", DEFAULT_FALLBACK)
    execution_id = new_id("flowrun")
    now = utcnow_iso()
    current_screen_id = None
    status = "started"
    fallback_reason = None
    flow_json = _json(version, "flow_json", {})
    screens = flow_json.get("screens") or []
    if screens:
        current_screen_id = screens[0].get("id")
    if (not supports_flows) or flow_message_version < min_supported:
        status = "fallback"
        fallback_reason = "unsupported_client_version"
    create_whatsapp_flow_execution(
        conn,
        execution_id=execution_id,
        flow_id=flow_id,
        version_id=version["id"],
        organization_id=flow["organization_id"],
        bot_id=flow["bot_id"],
        conversation_id=conversation_id,
        contact_id=contact_id,
        flow_token=flow_token or new_id("flowtok"),
        assigned_variant=assigned_variant,
        status=status,
        current_screen_id=current_screen_id,
        fallback_reason=fallback_reason,
        fallback_mode=fallback.get("mode"),
        context_json=to_json({"source": source, "client_capabilities": capabilities}),
        started_at=now,
        last_event_at=now,
    )
    _record_flow_event(conn, flow=flow, version_id=version["id"], execution_id=execution_id, event_type="execution_started" if status == "started" else "fallback_triggered", screen_id=current_screen_id, step_index=1, variant=assigned_variant, payload={"source": source, "client_capabilities": capabilities, "selected_version_id": version["id"]})
    provider_payload = None
    if status != "fallback":
        provider_payload = {
            "message_type": "flow_entrypoint",
            "flow": {
                "flow_id": flow.get("remote_flow_id") or flow_id,
                "flow_token": flow_token or execution_id,
                "flow_cta": (flow_json.get("cta") or flow.get("name") or "Abrir")[:20],
                "body": {"text": flow.get("name") or "Completa el flujo"},
                "flow_action": "navigate",
                "flow_action_payload": {"screen": current_screen_id} if current_screen_id else None,
                "mode": "published" if flow.get("remote_flow_id") else "draft",
                "flow_message_version": str(max(flow_message_version, min_supported)),
            },
            "body": flow.get("name") or "Completa el flujo",
        }
    return {
        "execution_id": execution_id,
        "status": status,
        "selected_version_id": version["id"],
        "assigned_variant": assigned_variant,
        "current_screen_id": current_screen_id,
        "provider_payload": provider_payload,
        "fallback": fallback if status == "fallback" else None,
        "send_message": send_message,
    }


def runtime_step(
    conn,
    *,
    flow_id: str,
    execution_id: str | None,
    action: str,
    screen_id: str | None,
    submitted_data: dict[str, Any] | None = None,
    client_capabilities: dict[str, Any] | None = None,
) -> dict[str, Any]:
    flow = get_whatsapp_flow(conn, flow_id)
    if not flow:
        raise ValueError("whatsapp_flow_not_found")
    execution = get_whatsapp_flow_execution(conn, execution_id, flow_id=flow_id) if execution_id else None
    if not execution:
        raise ValueError("whatsapp_flow_execution_not_found")
    version = get_whatsapp_flow_version(conn, execution["version_id"])
    if not version:
        raise ValueError("whatsapp_flow_version_not_found")
    flow_json = _json(version, "flow_json", {})
    screens = flow_json.get("screens") or []
    screen_lookup = {item.get("id"): item for item in screens}
    current_id = screen_id or execution.get("current_screen_id") or (screens[0].get("id") if screens else None)
    current_screen = screen_lookup.get(current_id) if current_id else None
    if execution.get("status") == "fallback":
        return {"execution_id": execution["id"], "status": "fallback", "fallback": _json(flow, "fallback_json", DEFAULT_FALLBACK)}
    step_index = count_whatsapp_flow_execution_events(conn, execution["id"]) + 1
    next_screen_id = current_id
    completed = False
    if action in {"submit", "complete"}:
        completed = True
    elif action in {"next", "navigate"} and current_id:
        ids = [item.get("id") for item in screens if item.get("id")]
        if current_id in ids:
            idx = ids.index(current_id)
            if idx + 1 < len(ids):
                next_screen_id = ids[idx + 1]
            else:
                completed = True
    now = utcnow_iso()
    update_whatsapp_flow_execution_progress(
        conn,
        execution_id=execution["id"],
        current_screen_id=None if completed else next_screen_id,
        status="completed" if completed else "running",
        result_json=to_json({"last_action": action, "submitted_data": submitted_data or {}, "client_capabilities": client_capabilities or {}}),
        completed_at=now if completed else None,
        last_event_at=now,
    )
    _record_flow_event(conn, flow=flow, version_id=version["id"], execution_id=execution["id"], event_type="step_completed" if completed else "screen_view", screen_id=current_id, step_index=step_index, variant=execution.get("assigned_variant"), payload={"action": action, "submitted_data": submitted_data or {}, "next_screen_id": next_screen_id, "client_capabilities": client_capabilities or {}})
    response_screen = None if completed else screen_lookup.get(next_screen_id)
    return {
        "execution_id": execution["id"],
        "status": "completed" if completed else "running",
        "current_screen": response_screen,
        "next_screen_id": None if completed else next_screen_id,
        "completed": completed,
    }


def record_whatsapp_flow_event(
    conn,
    *,
    flow_id: str,
    execution_id: str | None,
    event_type: str,
    screen_id: str | None,
    step_index: int | None,
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    flow = get_whatsapp_flow(conn, flow_id)
    if not flow:
        raise ValueError("whatsapp_flow_not_found")
    execution = get_whatsapp_flow_execution(conn, execution_id) if execution_id else None
    row = _record_flow_event(conn, flow=flow, version_id=execution.get("version_id") if execution else flow.get("published_version_id"), execution_id=execution_id, event_type=event_type, screen_id=screen_id, step_index=step_index, variant=execution.get("assigned_variant") if execution else None, payload=payload)
    if execution:
        touch_whatsapp_flow_execution(conn, execution_id=execution_id, last_event_at=utcnow_iso())
    return {**row, "payload": _json(row, "payload_json", {})}


def whatsapp_flow_analytics(conn, *, flow_id: str, since: str | None = None, until: str | None = None, include_remote_metric: bool = True) -> dict[str, Any]:
    flow = get_whatsapp_flow(conn, flow_id)
    if not flow:
        raise ValueError("whatsapp_flow_not_found")
    where = "WHERE flow_id = ?"
    params: list[Any] = [flow_id]
    if since:
        where += " AND created_at >= ?"
        params.append(since)
    if until:
        where += " AND created_at <= ?"
        params.append(until)
    analytics = summarize_whatsapp_flow_analytics(conn, flow_id=flow_id, where_clause=where, params=params)
    event_rows = analytics["events"]
    execution_rows = analytics["executions"]
    version_rows = analytics["versions"]
    summary = {
        "flow": serialize_flow(conn, flow, include_versions=True, include_publications=True),
        "events": [{**row} for row in event_rows],
        "executions": [{**row} for row in execution_rows],
        "versions": [{**row} for row in version_rows],
        "remote_endpoint_metric": None,
    }
    if include_remote_metric and flow.get("remote_flow_id") and since and until:
        try:
            client = MetaFlowClient(conn, organization_id=flow["organization_id"], bot_id=flow["bot_id"])
            summary["remote_endpoint_metric"] = client.get_endpoint_metric(flow["remote_flow_id"], since=since, until=until)
        except Exception as exc:
            summary["remote_endpoint_metric"] = {"error": str(exc)}
    return summary
