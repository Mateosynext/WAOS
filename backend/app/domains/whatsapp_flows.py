from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx

from ..config import settings
from ..db import execute, fetch_all, fetch_one, table_exists
from ..platform import store_secret
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
        number = fetch_one(conn, "SELECT * FROM whatsapp_numbers WHERE bot_id = ?", (bot_id,))
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
        versions = fetch_all(conn, "SELECT * FROM whatsapp_flow_versions WHERE flow_id = ? ORDER BY version_number DESC, created_at DESC", (row["id"],))
        payload["versions"] = [_serialize_flow_version(item) for item in versions]
    if include_publications and table_exists(conn, "whatsapp_flow_publications"):
        publications = fetch_all(conn, "SELECT * FROM whatsapp_flow_publications WHERE flow_id = ? ORDER BY started_at DESC LIMIT 20", (row["id"],))
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
            flow_id,
            organization_id,
            bot_id,
            name,
            flow_type,
            status,
            language,
            to_json(definition),
            to_json(metadata or {}),
            to_json(fallback or DEFAULT_FALLBACK),
            to_json(runtime_config or {}),
            version_id,
            runtime_endpoint,
            now,
            now,
        ),
    )
    version_flow_json = flow_json or _default_flow_json(name, definition["screens"])
    execute(
        conn,
        """
        INSERT INTO whatsapp_flow_versions (
            id, flow_id, organization_id, bot_id, version_number, state, flow_json, metadata_json,
            compatibility_json, rollout_json, remote_asset_status, validation_errors_json,
            cloned_from_version_id, created_at, updated_at, published_at
        ) VALUES (?, ?, ?, ?, 1, 'draft', ?, ?, ?, ?, 'pending', '[]', NULL, ?, ?, NULL)
        """,
        (
            version_id,
            flow_id,
            organization_id,
            bot_id,
            to_json(version_flow_json),
            to_json({"categories": categories, "endpoint_uri": runtime_endpoint}),
            to_json(compatibility or {}),
            to_json({}),
            now,
            now,
        ),
    )
    row = fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,)) or {}
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
    flow = fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,))
    if not flow:
        raise ValueError("whatsapp_flow_not_found")
    current = fetch_one(conn, "SELECT * FROM whatsapp_flow_versions WHERE flow_id = ? ORDER BY version_number DESC LIMIT 1", (flow_id,))
    next_version = int(current.get("version_number") or 0) + 1 if current else 1
    version_id = new_id("flowv")
    now = utcnow_iso()
    base_json = flow_json or _json(current, "flow_json", _json(flow, "definition_json", {}))
    execute(
        conn,
        """
        INSERT INTO whatsapp_flow_versions (
            id, flow_id, organization_id, bot_id, version_number, state, flow_json, metadata_json,
            compatibility_json, rollout_json, remote_asset_status, validation_errors_json,
            cloned_from_version_id, created_at, updated_at, published_at
        ) VALUES (?, ?, ?, ?, ?, 'draft', ?, ?, ?, ?, 'pending', '[]', ?, ?, ?, NULL)
        """,
        (
            version_id,
            flow_id,
            flow["organization_id"],
            flow["bot_id"],
            next_version,
            to_json(base_json),
            to_json(metadata or _json(current, "metadata_json", {})),
            to_json(compatibility or _json(current, "compatibility_json", {})),
            to_json({}),
            cloned_from_version_id,
            now,
            now,
        ),
    )
    execute(conn, "UPDATE whatsapp_flows SET current_version_id = ?, updated_at = ? WHERE id = ?", (version_id, now, flow_id))
    return _serialize_flow_version(fetch_one(conn, "SELECT * FROM whatsapp_flow_versions WHERE id = ?", (version_id,)) or {})


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
    flow = fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,))
    if not flow:
        raise ValueError("whatsapp_flow_not_found")
    row_id = new_id("flowexp")
    now = utcnow_iso()
    execute(
        conn,
        "INSERT INTO whatsapp_flow_experiments (id, flow_id, organization_id, bot_id, version_a_id, version_b_id, rollout_percentage, status, note, metrics_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '{}', ?, ?)",
        (row_id, flow_id, flow["organization_id"], flow["bot_id"], version_a_id, version_b_id, max(1, min(99, rollout_percentage)), status, note, now, now),
    )
    return fetch_one(conn, "SELECT * FROM whatsapp_flow_experiments WHERE id = ?", (row_id,)) or {}


def _get_active_experiment(conn, *, flow_id: str) -> dict[str, Any] | None:
    if not table_exists(conn, "whatsapp_flow_experiments"):
        return None
    return fetch_one(conn, "SELECT * FROM whatsapp_flow_experiments WHERE flow_id = ? AND status = 'active' ORDER BY updated_at DESC LIMIT 1", (flow_id,))


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
    execute(conn, "UPDATE whatsapp_flow_experiments SET metrics_json = ?, updated_at = ? WHERE id = ?", (to_json(metrics), utcnow_iso(), experiment["id"]))
    return variant, version_id


def _create_publication_run(conn, *, flow: dict[str, Any], version_id: str, action: str, request_payload: dict[str, Any] | None = None) -> str:
    row_id = new_id("flowpub")
    execute(
        conn,
        "INSERT INTO whatsapp_flow_publications (id, flow_id, version_id, organization_id, bot_id, provider, action, status, remote_flow_id, request_json, response_json, validation_errors_json, started_at, finished_at) VALUES (?, ?, ?, ?, ?, 'meta', ?, 'running', ?, ?, '{}', '[]', ?, NULL)",
        (row_id, flow["id"], version_id, flow["organization_id"], flow["bot_id"], action, flow.get("remote_flow_id"), to_json(request_payload or {}), utcnow_iso()),
    )
    return row_id


def _finish_publication_run(conn, *, publication_id: str, status: str, remote_flow_id: str | None = None, response_payload: dict[str, Any] | None = None, validation_errors: list[dict[str, Any]] | None = None) -> None:
    execute(
        conn,
        "UPDATE whatsapp_flow_publications SET status = ?, remote_flow_id = COALESCE(?, remote_flow_id), response_json = ?, validation_errors_json = ?, finished_at = ? WHERE id = ?",
        (status, remote_flow_id, to_json(response_payload or {}), to_json(validation_errors or []), utcnow_iso(), publication_id),
    )


def publish_whatsapp_flow(
    conn,
    *,
    flow_id: str,
    version_id: str | None = None,
    actor_user_id: str | None = None,
    register_encryption_public_key: str | None = None,
) -> dict[str, Any]:
    flow = fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,))
    if not flow:
        raise ValueError("whatsapp_flow_not_found")
    version = fetch_one(conn, "SELECT * FROM whatsapp_flow_versions WHERE id = ? AND flow_id = ?", (version_id or flow.get("current_version_id"), flow_id))
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
            execute(conn, "UPDATE whatsapp_flows SET remote_flow_id = ?, remote_status = 'draft', updated_at = ? WHERE id = ?", (remote_flow_id, utcnow_iso(), flow_id))
        asset_result = client.upload_flow_json(remote_flow_id, flow_json=flow_json)
        validation_errors = asset_result.get("validation_errors") or []
        execute(conn, "UPDATE whatsapp_flow_versions SET remote_asset_status = ?, validation_errors_json = ?, updated_at = ? WHERE id = ?", ("validated" if not validation_errors else "validation_failed", to_json(validation_errors), utcnow_iso(), version["id"]))
        if validation_errors:
            _finish_publication_run(conn, publication_id=publication_id, status="validation_failed", remote_flow_id=remote_flow_id, response_payload=asset_result, validation_errors=validation_errors)
            raise MetaFlowAPIError("meta_flow_validation_failed", payload=asset_result)
        publish_result = client.publish_flow(remote_flow_id)
        remote_details = client.get_flow(remote_flow_id)
        preview = client.get_preview(remote_flow_id)
        now = utcnow_iso()
        execute(
            conn,
            """
            UPDATE whatsapp_flows
            SET status = 'active', remote_flow_id = ?, remote_status = ?, remote_details_json = ?,
                current_version_id = ?, published_version_id = ?, runtime_endpoint = ?, remote_last_synced_at = ?,
                remote_last_published_at = ?, last_sync_error = NULL, updated_at = ?
            WHERE id = ?
            """,
            (
                remote_flow_id,
                remote_details.get("status") or "published",
                to_json({"detail": remote_details, "preview": preview}),
                version["id"],
                version["id"],
                endpoint_uri,
                now,
                now,
                now,
                flow_id,
            ),
        )
        execute(conn, "UPDATE whatsapp_flow_versions SET state = 'published', remote_asset_status = 'published', published_at = ?, updated_at = ? WHERE id = ?", (now, now, version["id"]))
        _finish_publication_run(conn, publication_id=publication_id, status="published", remote_flow_id=remote_flow_id, response_payload={"asset": asset_result, "publish": publish_result, "detail": remote_details, "preview": preview})
    except MetaFlowAPIError as exc:
        _finish_publication_run(conn, publication_id=publication_id, status="failed", remote_flow_id=remote_flow_id, response_payload=exc.payload)
        execute(conn, "UPDATE whatsapp_flows SET last_sync_error = ?, updated_at = ? WHERE id = ?", (to_json({"status_code": exc.status_code, "payload": exc.payload}), utcnow_iso(), flow_id))
        raise
    row = fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,)) or flow
    return serialize_flow(conn, row, include_versions=True, include_publications=True)


def sync_whatsapp_flow(conn, *, flow_id: str) -> dict[str, Any]:
    flow = fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,))
    if not flow:
        raise ValueError("whatsapp_flow_not_found")
    if not flow.get("remote_flow_id"):
        raise ValueError("whatsapp_flow_not_published")
    client = MetaFlowClient(conn, organization_id=flow["organization_id"], bot_id=flow["bot_id"])
    publication_id = _create_publication_run(conn, flow=flow, version_id=flow.get("published_version_id") or flow.get("current_version_id"), action="sync")
    try:
        remote_details = client.get_flow(flow["remote_flow_id"])
        preview = client.get_preview(flow["remote_flow_id"])
        execute(
            conn,
            "UPDATE whatsapp_flows SET remote_status = ?, remote_details_json = ?, remote_last_synced_at = ?, last_sync_error = NULL, updated_at = ? WHERE id = ?",
            (remote_details.get("status") or flow.get("remote_status") or "unknown", to_json({"detail": remote_details, "preview": preview}), utcnow_iso(), utcnow_iso(), flow_id),
        )
        _finish_publication_run(conn, publication_id=publication_id, status="synced", remote_flow_id=flow["remote_flow_id"], response_payload={"detail": remote_details, "preview": preview})
    except MetaFlowAPIError as exc:
        _finish_publication_run(conn, publication_id=publication_id, status="failed", remote_flow_id=flow["remote_flow_id"], response_payload=exc.payload)
        execute(conn, "UPDATE whatsapp_flows SET last_sync_error = ?, updated_at = ? WHERE id = ?", (to_json({"status_code": exc.status_code, "payload": exc.payload}), utcnow_iso(), flow_id))
        raise
    refreshed = fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,)) or flow
    return serialize_flow(conn, refreshed, include_versions=True, include_publications=True)


def rollback_whatsapp_flow(conn, *, flow_id: str, target_version_id: str, register_encryption_public_key: str | None = None) -> dict[str, Any]:
    flow = fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,))
    if not flow:
        raise ValueError("whatsapp_flow_not_found")
    target = fetch_one(conn, "SELECT * FROM whatsapp_flow_versions WHERE id = ? AND flow_id = ?", (target_version_id, flow_id))
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
    execute(conn, "UPDATE whatsapp_flow_versions SET state = 'rollback_candidate', updated_at = ? WHERE id = ?", (utcnow_iso(), cloned["id"]))
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
    execute(
        conn,
        "INSERT INTO whatsapp_flow_events (id, flow_id, version_id, execution_id, organization_id, bot_id, event_type, screen_id, step_index, variant, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (row_id, flow["id"], version_id, execution_id, flow["organization_id"], flow["bot_id"], event_type, screen_id, step_index, variant, to_json(payload or {}), utcnow_iso()),
    )
    return fetch_one(conn, "SELECT * FROM whatsapp_flow_events WHERE id = ?", (row_id,)) or {}


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
    flow = fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,))
    if not flow:
        raise ValueError("whatsapp_flow_not_found")
    assigned_variant, experiment_version_id = _assign_experiment_variant(conn, flow=flow, conversation_id=conversation_id, contact_id=contact_id, flow_token=flow_token)
    selected_version_id = version_id or experiment_version_id or flow.get("published_version_id") or flow.get("current_version_id")
    version = fetch_one(conn, "SELECT * FROM whatsapp_flow_versions WHERE id = ? AND flow_id = ?", (selected_version_id, flow_id))
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
    execute(
        conn,
        """
        INSERT INTO whatsapp_flow_executions (
            id, flow_id, version_id, organization_id, bot_id, conversation_id, contact_id, flow_token,
            assigned_variant, status, current_screen_id, fallback_reason, fallback_mode, context_json,
            result_json, channel_message_id, started_at, completed_at, last_event_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '{}', NULL, ?, NULL, ?)
        """,
        (
            execution_id,
            flow_id,
            version["id"],
            flow["organization_id"],
            flow["bot_id"],
            conversation_id,
            contact_id,
            flow_token or new_id("flowtok"),
            assigned_variant,
            status,
            current_screen_id,
            fallback_reason,
            fallback.get("mode"),
            to_json({"source": source, "client_capabilities": capabilities}),
            now,
            now,
        ),
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
    flow = fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,))
    if not flow:
        raise ValueError("whatsapp_flow_not_found")
    execution = fetch_one(conn, "SELECT * FROM whatsapp_flow_executions WHERE id = ? AND flow_id = ?", (execution_id, flow_id)) if execution_id else None
    if not execution:
        raise ValueError("whatsapp_flow_execution_not_found")
    version = fetch_one(conn, "SELECT * FROM whatsapp_flow_versions WHERE id = ?", (execution["version_id"],))
    if not version:
        raise ValueError("whatsapp_flow_version_not_found")
    flow_json = _json(version, "flow_json", {})
    screens = flow_json.get("screens") or []
    screen_lookup = {item.get("id"): item for item in screens}
    current_id = screen_id or execution.get("current_screen_id") or (screens[0].get("id") if screens else None)
    current_screen = screen_lookup.get(current_id) if current_id else None
    if execution.get("status") == "fallback":
        return {"execution_id": execution["id"], "status": "fallback", "fallback": _json(flow, "fallback_json", DEFAULT_FALLBACK)}
    step_index = len(fetch_all(conn, "SELECT id FROM whatsapp_flow_events WHERE execution_id = ?", (execution["id"],))) + 1
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
    execute(
        conn,
        "UPDATE whatsapp_flow_executions SET current_screen_id = ?, status = ?, result_json = ?, completed_at = ?, last_event_at = ? WHERE id = ?",
        (
            None if completed else next_screen_id,
            "completed" if completed else "running",
            to_json({"last_action": action, "submitted_data": submitted_data or {}, "client_capabilities": client_capabilities or {}}),
            now if completed else None,
            now,
            execution["id"],
        ),
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
    flow = fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,))
    if not flow:
        raise ValueError("whatsapp_flow_not_found")
    execution = fetch_one(conn, "SELECT * FROM whatsapp_flow_executions WHERE id = ?", (execution_id,)) if execution_id else None
    row = _record_flow_event(conn, flow=flow, version_id=execution.get("version_id") if execution else flow.get("published_version_id"), execution_id=execution_id, event_type=event_type, screen_id=screen_id, step_index=step_index, variant=execution.get("assigned_variant") if execution else None, payload=payload)
    if execution:
        execute(conn, "UPDATE whatsapp_flow_executions SET last_event_at = ? WHERE id = ?", (utcnow_iso(), execution_id))
    return {**row, "payload": _json(row, "payload_json", {})}


def whatsapp_flow_analytics(conn, *, flow_id: str, since: str | None = None, until: str | None = None, include_remote_metric: bool = True) -> dict[str, Any]:
    flow = fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,))
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
    event_rows = fetch_all(conn, f"SELECT event_type, screen_id, variant, COUNT(*) AS total FROM whatsapp_flow_events {where} GROUP BY event_type, screen_id, variant ORDER BY total DESC", params)
    execution_rows = fetch_all(conn, f"SELECT status, assigned_variant, fallback_reason, COUNT(*) AS total FROM whatsapp_flow_executions WHERE flow_id = ? GROUP BY status, assigned_variant, fallback_reason ORDER BY total DESC", (flow_id,))
    version_rows = fetch_all(conn, "SELECT version_id, event_type, COUNT(*) AS total FROM whatsapp_flow_events WHERE flow_id = ? GROUP BY version_id, event_type ORDER BY total DESC", (flow_id,))
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
