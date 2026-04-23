from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

import httpx

from ..config import settings
from ..db import table_exists
from ..platform import resolve_secret
from ..repositories import get_whatsapp_number_for_bot
from ..repositories.whatsapp_templates_domain import (
    approve_whatsapp_template,
    complete_template_sync_run,
    create_whatsapp_template_failover,
    create_whatsapp_template_sync_run,
    get_max_template_version_number,
    get_whatsapp_template,
    get_whatsapp_template_by_name,
    get_whatsapp_template_version,
    insert_whatsapp_template,
    insert_whatsapp_template_version,
    list_template_candidate_rows,
    list_template_delivery_projection_rows,
    list_whatsapp_template_sync_runs,
    list_whatsapp_template_versions,
    mark_template_sync_run_lint_failed,
    mark_template_sync_success,
    mark_template_version_sync_error,
    mark_template_version_sync_success,
    update_template_last_sync_status,
    update_whatsapp_template_approval_state,
    update_whatsapp_template_performance,
    update_whatsapp_template_version_approval,
    update_whatsapp_template_version_tracking,
)
from ..utils import from_json, new_id, to_json, utcnow_iso

WHATSAPP_TOKEN_KEYS = [
    "META_ACCESS_TOKEN",
    "WHATSAPP_ACCESS_TOKEN",
    "WHATSAPP_CLOUD_API_ACCESS_TOKEN",
]

ALLOWED_TEMPLATE_CATEGORIES = {"marketing", "utility", "authentication"}
ALLOWED_APPROVAL_STATES = {"draft", "pending", "approved", "rejected", "paused", "disabled"}
ALLOWED_HEADER_TYPES = {"NONE", "TEXT", "IMAGE", "VIDEO", "DOCUMENT"}
LANGUAGE_CODE_RE = re.compile(r"^[a-z]{2}(?:_[A-Z]{2})?$")
PLACEHOLDER_RE = re.compile(r"\{\{\s*(\d+)\s*\}\}")


class MetaTemplateAPIError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


class MetaTemplateClient:
    def __init__(self, conn, *, organization_id: str, bot_id: str) -> None:
        number = get_whatsapp_number_for_bot(conn, bot_id)
        if not number:
            raise ValueError("whatsapp_number_not_configured")
        access_token = resolve_whatsapp_access_token(conn, organization_id=organization_id, bot_id=bot_id)
        if not access_token:
            raise ValueError("missing_whatsapp_access_token")
        self.organization_id = organization_id
        self.bot_id = bot_id
        self.number = number
        self.waba_id = number.get("waba_id")
        self.access_token = access_token
        if not self.waba_id:
            raise ValueError("missing_whatsapp_waba_id")

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = httpx.request(
            method,
            f"{settings.meta_graph_api_base}/{path.lstrip('/')}",
            headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
            json=json_body,
            params=params,
            timeout=20.0,
        )
        try:
            payload = response.json()
        except Exception:
            payload = {"raw_text": response.text}
        if response.status_code >= 400:
            raise MetaTemplateAPIError("meta_template_provider_error", status_code=response.status_code, payload=payload)
        return payload

    def create_template_from_version(self, *, template_name: str, version: dict[str, Any]) -> dict[str, Any]:
        body = {
            "name": template_name,
            "category": _stringify(version.get("category") or "utility").upper(),
            "language": _stringify(version.get("language_code") or "es_MX"),
            "components": _build_meta_components(version),
        }
        return self._request("POST", f"{self.waba_id}/message_templates", json_body=body)

    def get_template_status(self, *, template_name: str | None = None, remote_template_id: str | None = None) -> dict[str, Any]:
        payload = self._request("GET", f"{self.waba_id}/message_templates", params={"limit": 200})
        items = payload.get("data") or []
        if remote_template_id:
            for item in items:
                if _stringify(item.get("id")) == _stringify(remote_template_id):
                    return item
        if template_name:
            normalized = _stringify(template_name).lower()
            for item in items:
                if _stringify(item.get("name")).lower() == normalized:
                    return item
        return {}


def resolve_whatsapp_access_token(conn, *, organization_id: str, bot_id: str | None) -> str | None:
    for key_name in WHATSAPP_TOKEN_KEYS:
        token = resolve_secret(conn, organization_id=organization_id, bot_id=bot_id, key_name=key_name)
        if token:
            return token
    return None


def _stringify(value: Any) -> str:
    return str(value or "").strip()


def _normalize_category(value: Any) -> str:
    category = _stringify(value).lower() or "utility"
    return category if category in ALLOWED_TEMPLATE_CATEGORIES else category


def _normalize_language(value: Any) -> str:
    return _stringify(value) or "es_MX"


def _json(row: dict[str, Any] | None, key: str, default: Any) -> Any:
    return from_json((row or {}).get(key), deepcopy(default))


def _template_placeholders(text: str | None) -> list[int]:
    indexes = sorted({int(match) for match in PLACEHOLDER_RE.findall(_stringify(text))})
    return indexes


def _sample_count(sample_values: Any, component: str) -> int:
    values = (sample_values or {}).get(component) if isinstance(sample_values, dict) else None
    if isinstance(values, list):
        return len(values)
    if isinstance(values, dict):
        return len(values)
    return 0


def _approved_state_from_remote(remote_status: Any, fallback: str = "pending") -> str:
    value = _stringify(remote_status).lower()
    mapping = {
        "approved": "approved",
        "active": "approved",
        "live": "approved",
        "pending": "pending",
        "in_review": "pending",
        "submitted": "pending",
        "rejected": "rejected",
        "paused": "paused",
        "disabled": "disabled",
        "deleted": "disabled",
    }
    return mapping.get(value, fallback if fallback in ALLOWED_APPROVAL_STATES else "pending")


def _best_effort_quality_rating(payload: dict[str, Any]) -> str | None:
    for key in ("quality_score", "quality_rating", "quality", "quality_status"):
        value = _stringify(payload.get(key))
        if value:
            return value
    return None


def _build_meta_components(version: dict[str, Any]) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    header_type = _stringify(version.get("header_type") or "NONE").upper() or "NONE"
    if header_type == "TEXT":
        components.append({"type": "HEADER", "format": "TEXT", "text": _stringify(version.get("header_text"))})
    elif header_type in {"IMAGE", "VIDEO", "DOCUMENT"}:
        components.append({"type": "HEADER", "format": header_type, "example": deepcopy((_json(version, "sample_values_json", {}) or {}).get("header") or [])})
    body_text = _stringify(version.get("body_text"))
    components.append({"type": "BODY", "text": body_text, "example": deepcopy((_json(version, "sample_values_json", {}) or {}).get("body") or [])})
    footer_text = _stringify(version.get("footer_text"))
    if footer_text:
        components.append({"type": "FOOTER", "text": footer_text})
    for button in _json(version, "buttons_json", []):
        button_type = _stringify((button or {}).get("type") or "quick_reply").upper()
        label = _stringify((button or {}).get("text") or (button or {}).get("label") or "Acción")
        if button_type in {"URL", "PHONE_NUMBER"}:
            entry = {"type": "BUTTONS", "buttons": [{"type": button_type, "text": label}]}
            if button_type == "URL" and _stringify((button or {}).get("url")):
                entry["buttons"][0]["url"] = _stringify((button or {}).get("url"))
            if button_type == "PHONE_NUMBER" and _stringify((button or {}).get("phone_number")):
                entry["buttons"][0]["phone_number"] = _stringify((button or {}).get("phone_number"))
            components.append(entry)
        else:
            components.append({"type": "BUTTONS", "buttons": [{"type": "QUICK_REPLY", "text": label}]})
    return components


def lint_whatsapp_template_definition(
    *,
    template_name: str,
    language_code: str,
    category: str,
    body_text: str,
    header_type: str = "NONE",
    header_text: str | None = None,
    footer_text: str | None = None,
    buttons: list[dict[str, Any]] | None = None,
    variables: list[dict[str, Any]] | None = None,
    assets: dict[str, Any] | None = None,
    sample_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    normalized_name = _stringify(template_name)
    normalized_language = _normalize_language(language_code)
    normalized_category = _normalize_category(category)
    normalized_header_type = _stringify(header_type or "NONE").upper() or "NONE"
    buttons = deepcopy(buttons or [])
    variables = deepcopy(variables or [])
    assets = deepcopy(assets or {})
    sample_values = deepcopy(sample_values or {})

    if not normalized_name:
        errors.append({"code": "template_name_required", "message": "El nombre del template es obligatorio.", "path": "name"})
    elif not re.fullmatch(r"[a-z0-9_]+", normalized_name):
        errors.append({"code": "template_name_invalid", "message": "Usa solo minúsculas, números y guiones bajos en el nombre del template.", "path": "name"})

    if not LANGUAGE_CODE_RE.fullmatch(normalized_language):
        errors.append({"code": "language_code_invalid", "message": "El idioma debe usar formato tipo es_MX o en.", "path": "language_code"})

    if normalized_category not in ALLOWED_TEMPLATE_CATEGORIES:
        errors.append({"code": "template_category_invalid", "message": "La categoría debe ser marketing, utility o authentication.", "path": "category"})

    if normalized_header_type not in ALLOWED_HEADER_TYPES:
        errors.append({"code": "header_type_invalid", "message": "El header_type no es válido.", "path": "header_type"})

    if not _stringify(body_text):
        errors.append({"code": "body_required", "message": "El body del template es obligatorio.", "path": "body_text"})
    elif len(_stringify(body_text)) > 1024:
        warnings.append({"code": "body_length_high", "message": "El body es largo; valida el límite real antes de publicarlo.", "path": "body_text"})

    if normalized_header_type == "TEXT" and not _stringify(header_text):
        errors.append({"code": "header_text_required", "message": "Los templates con HEADER TEXT necesitan header_text.", "path": "header_text"})
    if normalized_header_type == "NONE" and _stringify(header_text):
        warnings.append({"code": "header_text_unused", "message": "header_text viene informado pero header_type es NONE.", "path": "header_text"})

    body_placeholders = _template_placeholders(body_text)
    header_placeholders = _template_placeholders(header_text)
    expected_body = list(range(1, len(body_placeholders) + 1))
    expected_header = list(range(1, len(header_placeholders) + 1))
    if body_placeholders and body_placeholders != expected_body:
        errors.append({"code": "body_placeholders_non_contiguous", "message": "Las variables del body deben ser contiguas desde {{1}}.", "path": "body_text"})
    if header_placeholders and header_placeholders != expected_header:
        errors.append({"code": "header_placeholders_non_contiguous", "message": "Las variables del header deben ser contiguas desde {{1}}.", "path": "header_text"})

    variable_index_by_component: dict[str, set[int]] = {"body": set(), "header": set()}
    for variable in variables:
        component = _stringify((variable or {}).get("component") or "body").lower() or "body"
        if component not in variable_index_by_component:
            variable_index_by_component[component] = set()
        try:
            variable_index_by_component[component].add(int((variable or {}).get("index")))
        except Exception:
            errors.append({"code": "variable_index_invalid", "message": "Cada variable necesita un index entero.", "path": f"variables.{component}"})

    if body_placeholders and variable_index_by_component.get("body") and set(body_placeholders) != variable_index_by_component.get("body"):
        warnings.append({"code": "body_variable_registry_mismatch", "message": "La definición de variables no coincide exactamente con los placeholders del body.", "path": "variables"})
    if header_placeholders and variable_index_by_component.get("header") and set(header_placeholders) != variable_index_by_component.get("header"):
        warnings.append({"code": "header_variable_registry_mismatch", "message": "La definición de variables no coincide exactamente con los placeholders del header.", "path": "variables"})

    if len(buttons) > 10:
        errors.append({"code": "too_many_buttons", "message": "WhatsApp templates no deben exceder 10 botones.", "path": "buttons"})
    elif len(buttons) > 3:
        warnings.append({"code": "button_count_high", "message": "Valida el mix de quick replies y CTAs antes de publicar.", "path": "buttons"})

    if normalized_header_type in {"IMAGE", "VIDEO", "DOCUMENT"}:
        asset_payload = assets.get(normalized_header_type.lower()) or assets.get("header") or {}
        if not isinstance(asset_payload, dict) or not (_stringify(asset_payload.get("id")) or _stringify(asset_payload.get("link")) or _stringify(asset_payload.get("handle"))):
            errors.append({"code": "header_asset_required", "message": f"El header {normalized_header_type} necesita un asset de ejemplo o referencia.", "path": "assets"})

    body_sample_count = _sample_count(sample_values, "body")
    header_sample_count = _sample_count(sample_values, "header")
    if len(body_placeholders) and body_sample_count < len(body_placeholders):
        errors.append({"code": "body_sample_values_missing", "message": "Faltan sample values para cubrir todas las variables del body.", "path": "sample_values.body"})
    if normalized_header_type == "TEXT" and len(header_placeholders) and header_sample_count < len(header_placeholders):
        errors.append({"code": "header_sample_values_missing", "message": "Faltan sample values para cubrir todas las variables del header.", "path": "sample_values.header"})

    coverage = {
        "required": {
            "body_variable_count": len(body_placeholders),
            "header_variable_count": len(header_placeholders) if normalized_header_type == "TEXT" else 0,
            "header_asset_type": normalized_header_type.lower() if normalized_header_type in {"IMAGE", "VIDEO", "DOCUMENT"} else None,
            "button_count": len(buttons),
        },
        "provided": {
            "declared_body_variables": len(variable_index_by_component.get("body") or []),
            "declared_header_variables": len(variable_index_by_component.get("header") or []),
            "body_sample_values": body_sample_count,
            "header_sample_values": header_sample_count,
            "has_header_asset": bool(assets.get(normalized_header_type.lower()) or assets.get("header")) if normalized_header_type in {"IMAGE", "VIDEO", "DOCUMENT"} else True,
        },
    }

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "coverage": coverage,
        "normalized": {
            "name": normalized_name,
            "language_code": normalized_language,
            "category": normalized_category,
            "header_type": normalized_header_type,
        },
    }


def validate_template_runtime_payload(version: dict[str, Any], template_payload: dict[str, Any]) -> dict[str, Any]:
    components = template_payload.get("components") or []
    body_params = 0
    header_params = 0
    has_header_asset = False

    for component in components:
        component_type = _stringify((component or {}).get("type")).lower()
        parameters = (component or {}).get("parameters") or []
        if component_type == "body":
            body_params = len(parameters)
        elif component_type == "header":
            header_type = _stringify(version.get("header_type") or "NONE").upper() or "NONE"
            if header_type == "TEXT":
                header_params = len(parameters)
            elif header_type in {"IMAGE", "VIDEO", "DOCUMENT"}:
                for parameter in parameters:
                    param_type = _stringify((parameter or {}).get("type")).lower()
                    if param_type == header_type.lower() and isinstance(parameter.get(header_type.lower()), dict):
                        media = parameter.get(header_type.lower()) or {}
                        if _stringify(media.get("id")) or _stringify(media.get("link")) or _stringify(media.get("handle")):
                            has_header_asset = True
                    if param_type == "document" and header_type == "DOCUMENT":
                        media = parameter.get("document") or {}
                        if _stringify(media.get("id")) or _stringify(media.get("link")) or _stringify(media.get("handle")):
                            has_header_asset = True

    coverage = _json(version, "coverage_json", {})
    required = coverage.get("required") if isinstance(coverage, dict) else {}
    required_body = int((required or {}).get("body_variable_count") or 0)
    required_header = int((required or {}).get("header_variable_count") or 0)
    required_asset = _stringify((required or {}).get("header_asset_type"))

    errors: list[dict[str, Any]] = []
    if body_params < required_body:
        errors.append({"code": "runtime_body_variables_missing", "message": "El payload no cubre todas las variables del body.", "path": "template.components.body"})
    if required_header and header_params < required_header:
        errors.append({"code": "runtime_header_variables_missing", "message": "El payload no cubre todas las variables del header.", "path": "template.components.header"})
    if required_asset and not has_header_asset:
        errors.append({"code": "runtime_header_asset_missing", "message": "El payload no incluye el asset requerido para el header.", "path": "template.components.header"})

    return {
        "ok": not errors,
        "errors": errors,
        "coverage": {
            "required_body_params": required_body,
            "required_header_params": required_header,
            "required_header_asset": required_asset or None,
            "provided_body_params": body_params,
            "provided_header_params": header_params,
            "provided_header_asset": has_header_asset,
        },
    }


def _serialize_template_version(row: dict[str, Any]) -> dict[str, Any]:
    if not row:
        return {}
    return {
        **row,
        "buttons": _json(row, "buttons_json", []),
        "variables": _json(row, "variables_json", []),
        "assets": _json(row, "assets_json", {}),
        "sample_values": _json(row, "sample_values_json", {}),
        "lint_report": _json(row, "lint_report_json", {}),
        "coverage": _json(row, "coverage_json", {}),
        "metadata": _json(row, "metadata_json", {}),
    }


def _serialize_sync_run(row: dict[str, Any]) -> dict[str, Any]:
    if not row:
        return {}
    return {
        **row,
        "request": _json(row, "request_json", {}),
        "response": _json(row, "response_json", {}),
        "validation_errors": _json(row, "validation_errors_json", []),
    }


def _analytics_summary_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    accepted = len(rows)
    delivered = 0
    read = 0
    failed = 0
    versions: dict[str, dict[str, Any]] = {}
    languages: dict[str, int] = {}
    categories: dict[str, int] = {}

    for row in rows:
        status = _stringify(row.get("current_status")).lower() or "accepted"
        if status in {"delivered", "read"}:
            delivered += 1
        if status == "read":
            read += 1
        if status == "failed":
            failed += 1
        metadata = _json(row, "metadata_json", {})
        governance = metadata.get("governance") if isinstance(metadata, dict) else {}
        version_id = _stringify((governance or {}).get("selected_template_version_id")) or "unknown"
        bucket = versions.setdefault(version_id, {"version_id": version_id, "accepted": 0, "delivered": 0, "read": 0, "failed": 0})
        bucket["accepted"] += 1
        if status in {"delivered", "read"}:
            bucket["delivered"] += 1
        if status == "read":
            bucket["read"] += 1
        if status == "failed":
            bucket["failed"] += 1
        language = _stringify((governance or {}).get("selected_template_language")) or "unknown"
        category = _stringify((governance or {}).get("message_category")) or "unknown"
        languages[language] = languages.get(language, 0) + 1
        categories[category] = categories.get(category, 0) + 1

    delivery_rate = round((delivered / accepted) * 100, 2) if accepted else 0.0
    read_rate = round((read / accepted) * 100, 2) if accepted else 0.0
    fail_rate = round((failed / accepted) * 100, 2) if accepted else 0.0
    performance_score = round(max(0.0, delivery_rate - fail_rate * 1.5 + read_rate * 0.2), 2) if accepted else 0.0

    return {
        "accepted_count": accepted,
        "delivered_count": delivered,
        "read_count": read,
        "failed_count": failed,
        "delivery_rate": delivery_rate,
        "read_rate": read_rate,
        "fail_rate": fail_rate,
        "performance_score": performance_score,
        "by_version": sorted(versions.values(), key=lambda item: (-item["accepted"], item["version_id"])),
        "by_language": [{"language": key, "accepted_count": value} for key, value in sorted(languages.items(), key=lambda item: (-item[1], item[0]))],
        "by_category": [{"category": key, "accepted_count": value} for key, value in sorted(categories.items(), key=lambda item: (-item[1], item[0]))],
    }


def whatsapp_template_analytics(conn, *, template_id: str, since: str | None = None, until: str | None = None) -> dict[str, Any]:
    template = get_whatsapp_template(conn, template_id)
    if not template:
        raise ValueError("whatsapp_template_not_found")
    if not table_exists(conn, "whatsapp_delivery_projection"):
        return {"template": serialize_template(conn, template, include_analytics=False), "window": {"since": since, "until": until}, "summary": _analytics_summary_from_rows([]), "deliveries": []}
    rows = list_template_delivery_projection_rows(conn, organization_id=template["organization_id"], template_name=template["name"], since=since, until=until, limit=500)
    summary = _analytics_summary_from_rows(rows)
    update_whatsapp_template_performance(conn, template_id=template_id, performance_score=summary.get("performance_score") or 0, updated_at=utcnow_iso())
    template = get_whatsapp_template(conn, template_id) or template
    return {
        "template": serialize_template(conn, template, include_analytics=False),
        "window": {"since": since, "until": until},
        "summary": summary,
        "deliveries": [
            {
                "provider_message_id": row.get("provider_message_id"),
                "current_status": row.get("current_status"),
                "accepted_at": row.get("accepted_at"),
                "delivered_at": row.get("delivered_at"),
                "read_at": row.get("read_at"),
                "failed_at": row.get("failed_at"),
                "template_name": row.get("template_name"),
                "metadata": _json(row, "metadata_json", {}),
            }
            for row in rows[:50]
        ],
    }


def serialize_template(conn, row: dict[str, Any], *, include_versions: bool = False, include_sync_runs: bool = False, include_analytics: bool = True) -> dict[str, Any]:
    payload = {
        **row,
        "metadata": _json(row, "metadata_json", {}),
    }
    if include_versions and table_exists(conn, "whatsapp_template_versions"):
        versions = list_whatsapp_template_versions(conn, row["id"])
        payload["versions"] = [_serialize_template_version(item) for item in versions]
    if include_sync_runs and table_exists(conn, "whatsapp_template_sync_runs"):
        runs = list_whatsapp_template_sync_runs(conn, row["id"], limit=20)
        payload["sync_runs"] = [_serialize_sync_run(item) for item in runs]
    if include_analytics:
        payload["performance"] = whatsapp_template_analytics(conn, template_id=row["id"], since=None, until=None).get("summary") if table_exists(conn, "whatsapp_delivery_projection") else _analytics_summary_from_rows([])
    return payload


def create_whatsapp_template(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    name: str,
    category: str,
    default_language: str = "es_MX",
    body_text: str,
    header_type: str = "NONE",
    header_text: str | None = None,
    footer_text: str | None = None,
    buttons: list[dict[str, Any]] | None = None,
    variables: list[dict[str, Any]] | None = None,
    assets: dict[str, Any] | None = None,
    sample_values: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    approval_status: str = "draft",
    fallback_template_id: str | None = None,
) -> dict[str, Any]:
    template_id = new_id("watpl")
    now = utcnow_iso()
    insert_whatsapp_template(
        conn,
        template_id=template_id,
        organization_id=organization_id,
        bot_id=bot_id,
        name=_stringify(name),
        category=_normalize_category(category),
        default_language=_normalize_language(default_language),
        fallback_template_id=fallback_template_id,
        metadata_json=to_json(metadata or {}),
        created_at=now,
        updated_at=now,
    )
    version = create_whatsapp_template_version(
        conn,
        template_id=template_id,
        language_code=default_language,
        category=category,
        body_text=body_text,
        header_type=header_type,
        header_text=header_text,
        footer_text=footer_text,
        buttons=buttons,
        variables=variables,
        assets=assets,
        sample_values=sample_values,
        metadata=metadata,
        approval_status=approval_status,
        fallback_template_id=fallback_template_id,
    )
    if approval_status == "approved":
        approve_whatsapp_template(conn, template_id=template_id, version_id=version["id"], updated_at=utcnow_iso())
    row = get_whatsapp_template(conn, template_id) or {}
    return serialize_template(conn, row, include_versions=True, include_sync_runs=True)


def create_whatsapp_template_version(
    conn,
    *,
    template_id: str,
    language_code: str,
    category: str,
    body_text: str,
    header_type: str = "NONE",
    header_text: str | None = None,
    footer_text: str | None = None,
    buttons: list[dict[str, Any]] | None = None,
    variables: list[dict[str, Any]] | None = None,
    assets: dict[str, Any] | None = None,
    sample_values: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    approval_status: str = "draft",
    fallback_template_id: str | None = None,
) -> dict[str, Any]:
    template = get_whatsapp_template(conn, template_id)
    if not template:
        raise ValueError("whatsapp_template_not_found")
    current = get_max_template_version_number(conn, template_id) if table_exists(conn, "whatsapp_template_versions") else None
    version_number = int((current or {}).get("value") or 0) + 1
    lint = lint_whatsapp_template_definition(
        template_name=template.get("name"),
        language_code=language_code,
        category=category,
        body_text=body_text,
        header_type=header_type,
        header_text=header_text,
        buttons=buttons,
        variables=variables,
        assets=assets,
        sample_values=sample_values,
    )
    state = "linted" if lint.get("ok") else "needs_changes"
    normalized = lint.get("normalized") or {}
    version_id = new_id("watplv")
    now = utcnow_iso()
    insert_whatsapp_template_version(
        conn,
        version_id=version_id,
        template_id=template_id,
        organization_id=template["organization_id"],
        bot_id=template["bot_id"],
        version_number=version_number,
        state=state,
        language_code=normalized.get("language_code") or _normalize_language(language_code),
        category=normalized.get("category") or _normalize_category(category),
        body_text=_stringify(body_text),
        header_type=normalized.get("header_type") or _stringify(header_type or "NONE").upper(),
        header_text=_stringify(header_text),
        footer_text=_stringify(footer_text),
        buttons_json=to_json(buttons or []),
        variables_json=to_json(variables or []),
        assets_json=to_json(assets or {}),
        sample_values_json=to_json(sample_values or {}),
        lint_report_json=to_json(lint),
        coverage_json=to_json(lint.get("coverage") or {}),
        approval_status=approval_status if approval_status in ALLOWED_APPROVAL_STATES else "draft",
        fallback_template_id=fallback_template_id,
        metadata_json=to_json(metadata or {}),
        created_at=now,
        updated_at=now,
    )
    template_status = "ready" if lint.get("ok") else "needs_changes"
    approved_version_id = template.get("approved_version_id")
    if approval_status == "approved":
        approved_version_id = version_id
        template_status = "approved"
    update_whatsapp_template_version_tracking(
        conn,
        template_id=template_id,
        latest_version_id=version_id,
        approved_version_id=approved_version_id,
        status=template_status,
        fallback_template_id=fallback_template_id,
        updated_at=now,
    )
    row = get_whatsapp_template_version(conn, version_id) or {}
    return _serialize_template_version(row)


def update_whatsapp_template_approval(
    conn,
    *,
    template_id: str,
    version_id: str | None = None,
    approval_status: str,
    rejection_reason: str | None = None,
    remote_status: str | None = None,
    remote_quality_rating: str | None = None,
) -> dict[str, Any]:
    template = get_whatsapp_template(conn, template_id)
    if not template:
        raise ValueError("whatsapp_template_not_found")
    if not version_id:
        version_id = template.get("latest_version_id")
    version = get_whatsapp_template_version(conn, version_id, template_id)
    if not version:
        raise ValueError("whatsapp_template_version_not_found")
    approval_status = approval_status if approval_status in ALLOWED_APPROVAL_STATES else _approved_state_from_remote(approval_status)
    now = utcnow_iso()
    update_whatsapp_template_version_approval(
        conn,
        version_id=version_id,
        approval_status=approval_status,
        rejection_reason=rejection_reason,
        remote_status=remote_status,
        remote_quality_rating=remote_quality_rating,
        updated_at=now,
        publish_now=approval_status == "approved",
    )
    approved_version_id = version_id if approval_status == "approved" else (template.get("approved_version_id") if template.get("approved_version_id") != version_id else None)
    update_whatsapp_template_approval_state(
        conn,
        template_id=template_id,
        approved_version_id=approved_version_id,
        status=approval_status,
        last_sync_status=remote_status,
        updated_at=now,
    )
    return serialize_template(conn, get_whatsapp_template(conn, template_id) or template, include_versions=True, include_sync_runs=True)


def _create_sync_run(conn, *, template: dict[str, Any], version: dict[str, Any], action: str, request_payload: dict[str, Any]) -> dict[str, Any]:
    row_id = new_id("watplsync")
    now = utcnow_iso()
    return create_whatsapp_template_sync_run(
        conn,
        row_id=row_id,
        template_id=template["id"],
        version_id=version["id"],
        organization_id=template["organization_id"],
        bot_id=template["bot_id"],
        action=action,
        request_json=to_json(request_payload),
        started_at=now,
    )


def sync_whatsapp_template(conn, *, template_id: str, version_id: str | None = None, action: str = "publish") -> dict[str, Any]:
    template = get_whatsapp_template(conn, template_id)
    if not template:
        raise ValueError("whatsapp_template_not_found")
    version = get_whatsapp_template_version(conn, version_id or template.get("latest_version_id"), template_id)
    if not version:
        raise ValueError("whatsapp_template_version_not_found")
    lint_report = _json(version, "lint_report_json", {})
    sync_run = _create_sync_run(conn, template=template, version=version, action=action, request_payload={"template_id": template_id, "version_id": version["id"], "action": action})
    now = utcnow_iso()
    if not lint_report.get("ok"):
        mark_template_sync_run_lint_failed(conn, sync_run_id=sync_run["id"], validation_errors_json=to_json(lint_report.get("errors") or []), response_json=to_json({"reason": "lint_failed"}), finished_at=now)
        update_template_last_sync_status(conn, template_id=template_id, last_sync_status="lint_failed", updated_at=now)
        return serialize_template(conn, get_whatsapp_template(conn, template_id) or template, include_versions=True, include_sync_runs=True)

    client = MetaTemplateClient(conn, organization_id=template["organization_id"], bot_id=template["bot_id"])
    try:
        response = client.create_template_from_version(template_name=template["name"], version=version)
        remote_status = _stringify(response.get("status") or response.get("event") or "pending")
        approval_status = _approved_state_from_remote(remote_status, fallback="pending")
        remote_template_id = _stringify(response.get("id") or response.get("template_id") or template.get("remote_template_id")) or None
        mark_template_version_sync_success(
            conn,
            version_id=version["id"],
            approval_status=approval_status,
            remote_template_id=remote_template_id,
            remote_status=remote_status,
            remote_quality_rating=_best_effort_quality_rating(response),
            synced_at=now,
        )
        approved_version_id = version["id"] if approval_status == "approved" else template.get("approved_version_id")
        mark_template_sync_success(
            conn,
            template_id=template_id,
            remote_template_id=remote_template_id,
            last_sync_status=remote_status or approval_status,
            approved_version_id=approved_version_id,
            status=approval_status,
            updated_at=now,
        )
        complete_template_sync_run(conn, sync_run_id=sync_run["id"], status="approved" if approval_status == "approved" else "synced", response_json=to_json(response), finished_at=now)
    except MetaTemplateAPIError as exc:
        response = exc.payload or {}
        remote_status = _stringify((response.get("error") or {}).get("error_subcode") or (response.get("error") or {}).get("code") or "provider_error")
        approval_status = _approved_state_from_remote(_stringify((response.get("error") or {}).get("error_user_title")) or remote_status, fallback="rejected")
        mark_template_version_sync_error(conn, version_id=version["id"], approval_status=approval_status, remote_status=remote_status, rejection_reason=_stringify((response.get("error") or {}).get("message") or str(exc)), updated_at=now)
        update_whatsapp_template_approval_state(conn, template_id=template_id, approved_version_id=template.get("approved_version_id"), status=approval_status, last_sync_status=remote_status, updated_at=now)
        fail_template_sync_run(conn, sync_run_id=sync_run["id"], response_json=to_json(response), validation_errors_json=to_json([{"code": remote_status or 'provider_error', "message": _stringify((response.get('error') or {}).get('message') or str(exc))}]), finished_at=now)
    return serialize_template(conn, get_whatsapp_template(conn, template_id) or template, include_versions=True, include_sync_runs=True)


def sync_whatsapp_template_status(conn, *, template_id: str, version_id: str | None = None) -> dict[str, Any]:
    template = get_whatsapp_template(conn, template_id)
    if not template:
        raise ValueError("whatsapp_template_not_found")
    version = get_whatsapp_template_version(conn, version_id or template.get("latest_version_id"), template_id)
    if not version:
        raise ValueError("whatsapp_template_version_not_found")
    client = MetaTemplateClient(conn, organization_id=template["organization_id"], bot_id=template["bot_id"])
    response = client.get_template_status(template_name=template.get("name"), remote_template_id=version.get("remote_template_id") or template.get("remote_template_id"))
    remote_status = _stringify(response.get("status") or response.get("event") or version.get("remote_status") or "pending")
    approval_status = _approved_state_from_remote(remote_status, fallback=version.get("approval_status") or "pending")
    return update_whatsapp_template_approval(
        conn,
        template_id=template_id,
        version_id=version["id"],
        approval_status=approval_status,
        rejection_reason=_stringify(response.get("rejected_reason") or response.get("rejection_reason") or version.get("rejection_reason")) or None,
        remote_status=remote_status,
        remote_quality_rating=_best_effort_quality_rating(response),
    )


def _fetch_template_candidates(conn, *, organization_id: str, bot_id: str, language_code: str, category: str, exclude_template_names: set[str] | None = None) -> list[dict[str, Any]]:
    exclude_template_names = exclude_template_names or set()
    rows = list_template_candidate_rows(conn, organization_id=organization_id, bot_id=bot_id)
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if _stringify(row.get("name")) in exclude_template_names:
            continue
        row_language = _normalize_language(row.get("language_code"))
        row_category = _normalize_category(row.get("version_category") or row.get("category"))
        approval_status = _stringify(row.get("approval_status") or row.get("status")).lower() or "draft"
        if approval_status != "approved":
            continue
        if language_code and row_language != language_code:
            continue
        if category and row_category != category:
            continue
        filtered.append(row)
    return filtered


def _validate_candidate_payload(candidate: dict[str, Any], template_payload: dict[str, Any]) -> dict[str, Any]:
    version = {
        "header_type": candidate.get("header_type"),
        "coverage_json": candidate.get("coverage_json"),
    }
    return validate_template_runtime_payload(version, template_payload)


def resolve_whatsapp_template_for_payload(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    payload: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    allow_alternative: bool = True,
    fallback_only: bool = False,
) -> dict[str, Any]:
    if not table_exists(conn, "whatsapp_templates") or not table_exists(conn, "whatsapp_template_versions"):
        return {"ok": True, "status": "registry_unavailable", "payload": deepcopy(payload)}

    metadata = metadata or {}
    working_payload = deepcopy(payload)
    template_payload = deepcopy(working_payload.get("template") or {})
    if not isinstance(template_payload, dict):
        return {"ok": False, "status": "invalid_template_payload", "errors": [{"code": "template_payload_invalid", "message": "El payload.template debe ser un objeto."}], "payload": deepcopy(payload)}

    requested_name = _stringify(template_payload.get("name"))
    language_code = _normalize_language(((template_payload.get("language") or {}).get("code")) or metadata.get("default_template_language") or "es_MX")
    category = _normalize_category(template_payload.get("category") or payload.get("message_category") or metadata.get("default_template_category") or "utility")
    template_payload.setdefault("language", {"code": language_code})
    template_payload["category"] = category
    working_payload["template"] = template_payload

    if not requested_name and fallback_only:
        fallback_candidate = payload.get("template_fallback") or payload.get("template_candidate") or {}
        requested_name = _stringify((fallback_candidate or {}).get("name"))
        if requested_name:
            working_payload["template"] = deepcopy(fallback_candidate)
            working_payload["template"].setdefault("language", {"code": language_code})
            working_payload["template"]["category"] = _normalize_category((working_payload["template"] or {}).get("category") or category)
            template_payload = working_payload["template"]
            category = _normalize_category(template_payload.get("category") or category)
            language_code = _normalize_language(((template_payload.get("language") or {}).get("code")) or language_code)

    current_version = None
    current_template = None
    if requested_name:
        current_template = get_whatsapp_template_by_name(conn, organization_id=organization_id, bot_id=bot_id, name=requested_name)
        if current_template:
            version_id = current_template.get("approved_version_id") or current_template.get("latest_version_id")
            if version_id:
                current_version = get_whatsapp_template_version(conn, version_id)

    def _candidate_from_template_row(row: dict[str, Any]) -> dict[str, Any] | None:
        version_id = row.get("approved_version_id") or row.get("latest_version_id")
        if not version_id:
            return None
        version = get_whatsapp_template_version(conn, version_id)
        if not version:
            return None
        return {"template": row, "version": version}

    exact_candidate = _candidate_from_template_row(current_template) if current_template and not fallback_only else None
    exact_valid = None
    if exact_candidate:
        exact_approval = _stringify((exact_candidate["version"] or {}).get("approval_status")).lower() or "draft"
        if exact_approval == "approved":
            exact_valid = validate_template_runtime_payload(exact_candidate["version"], template_payload)
            if exact_valid.get("ok"):
                return {
                    "ok": True,
                    "status": "approved",
                    "decision": "selected_exact",
                    "selected_template": current_template.get("name"),
                    "selected_template_id": current_template.get("id"),
                    "selected_template_version_id": exact_candidate["version"].get("id"),
                    "selected_template_language": exact_candidate["version"].get("language_code"),
                    "message_category": exact_candidate["version"].get("category") or category,
                    "approval_status": exact_approval,
                    "coverage": exact_valid.get("coverage"),
                    "payload": working_payload,
                    "used_fallback": False,
                }
    elif requested_name and fallback_only and not current_template:
        return {
            "ok": True,
            "status": "unmanaged_fallback_passthrough",
            "decision": "passthrough_unmanaged_fallback",
            "selected_template": requested_name,
            "selected_template_id": None,
            "selected_template_version_id": None,
            "selected_template_language": language_code,
            "message_category": category,
            "approval_status": "unmanaged",
            "coverage": None,
            "payload": working_payload,
            "used_fallback": True,
            "managed": False,
        }
    elif requested_name and not fallback_only:
        return {
            "ok": True,
            "status": "unmanaged_passthrough",
            "decision": "passthrough_unmanaged",
            "selected_template": requested_name,
            "selected_template_id": None,
            "selected_template_version_id": None,
            "selected_template_language": language_code,
            "message_category": category,
            "approval_status": "unmanaged",
            "coverage": None,
            "payload": working_payload,
            "used_fallback": False,
            "managed": False,
        }

    fallback_template_names: list[str] = []
    explicit_fallback = payload.get("template_fallback") or payload.get("template_candidate") or {}
    explicit_fallback_name = _stringify((explicit_fallback or {}).get("name"))
    if explicit_fallback_name:
        fallback_template_names.append(explicit_fallback_name)
    if current_template and _stringify(current_template.get("fallback_template_id")):
        linked = get_whatsapp_template(conn, current_template.get("fallback_template_id"))
        if linked and _stringify(linked.get("name")):
            fallback_template_names.append(_stringify(linked.get("name")))
    if current_version and _stringify(current_version.get("fallback_template_id")):
        linked = get_whatsapp_template(conn, current_version.get("fallback_template_id"))
        if linked and _stringify(linked.get("name")):
            fallback_template_names.append(_stringify(linked.get("name")))

    exclude_names = {requested_name} if requested_name else set()
    candidates = _fetch_template_candidates(conn, organization_id=organization_id, bot_id=bot_id, language_code=language_code, category=category, exclude_template_names=exclude_names)
    prioritized: list[dict[str, Any]] = []
    for fallback_name in fallback_template_names:
        for row in candidates:
            if _stringify(row.get("name")) == fallback_name and row not in prioritized:
                prioritized.append(row)
    for row in candidates:
        if row not in prioritized:
            prioritized.append(row)

    if allow_alternative:
        for candidate in prioritized:
            validation = _validate_candidate_payload(candidate, template_payload)
            if not validation.get("ok"):
                continue
            candidate_name = _stringify(candidate.get("name"))
            chosen_payload = deepcopy(working_payload)
            chosen_payload.setdefault("template", {})
            chosen_payload["template"]["name"] = candidate_name
            chosen_payload["template"]["language"] = {"code": _normalize_language(candidate.get("language_code") or language_code)}
            chosen_payload["template"]["category"] = _normalize_category(candidate.get("version_category") or candidate.get("category") or category)
            return {
                "ok": True,
                "status": "fallback_selected" if candidate_name != requested_name else "approved",
                "decision": "selected_fallback" if candidate_name != requested_name else "selected_exact",
                "selected_template": candidate_name,
                "selected_template_id": candidate.get("id"),
                "selected_template_version_id": candidate.get("version_id"),
                "selected_template_language": _normalize_language(candidate.get("language_code") or language_code),
                "message_category": _normalize_category(candidate.get("version_category") or candidate.get("category") or category),
                "approval_status": "approved",
                "coverage": validation.get("coverage"),
                "payload": chosen_payload,
                "used_fallback": candidate_name != requested_name,
                "fallback_reason": "requested_template_unavailable_or_invalid",
            }

    errors: list[dict[str, Any]] = []
    if exact_candidate and exact_valid and not exact_valid.get("ok"):
        errors.extend(exact_valid.get("errors") or [])
    if exact_candidate and _stringify((exact_candidate["version"] or {}).get("approval_status")).lower() != "approved":
        errors.append({"code": "template_not_approved", "message": "El template solicitado no está aprobado.", "path": "template.name"})
    if not exact_candidate:
        errors.append({"code": "template_not_registered", "message": "El template no existe en el registry local.", "path": "template.name"})
    return {
        "ok": False,
        "status": "rejected",
        "decision": "deny",
        "payload": working_payload,
        "errors": errors,
        "selected_template": requested_name or None,
        "selected_template_id": current_template.get("id") if current_template else None,
        "selected_template_version_id": current_version.get("id") if current_version else None,
        "selected_template_language": language_code,
        "message_category": category,
        "used_fallback": False,
    }


def register_whatsapp_template_failover(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    outbox_id: str | None,
    current_template_name: str | None,
    current_version_id: str | None,
    fallback_template_name: str,
    fallback_version_id: str,
    reason_code: str,
    payload_snapshot: dict[str, Any],
    source: str = "runtime",
) -> dict[str, Any]:
    if not table_exists(conn, "whatsapp_template_failovers"):
        return {}
    row_id = new_id("watplfo")
    fallback_template = get_whatsapp_template_by_name(conn, organization_id=organization_id, bot_id=bot_id, name=fallback_template_name)
    current_template = get_whatsapp_template_by_name(conn, organization_id=organization_id, bot_id=bot_id, name=current_template_name) if current_template_name else None
    return create_whatsapp_template_failover(
        conn,
        row_id=row_id,
        organization_id=organization_id,
        bot_id=bot_id,
        outbox_id=outbox_id,
        current_template_id=(current_template or {}).get("id"),
        current_version_id=current_version_id,
        fallback_template_id=(fallback_template or {}).get("id"),
        fallback_version_id=fallback_version_id,
        reason_code=reason_code,
        source=source,
        payload_json=to_json(payload_snapshot),
        created_at=utcnow_iso(),
    )


def recover_template_failure(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    outbox_id: str | None,
    payload: dict[str, Any],
    governance: dict[str, Any] | None,
    error_details: dict[str, Any] | None,
) -> dict[str, Any] | None:
    governance = governance or {}
    current_template = _stringify(((payload.get("template") or {}).get("name")))
    current_template_row = get_whatsapp_template_by_name(conn, organization_id=organization_id, bot_id=bot_id, name=current_template) if current_template else None
    explicit_fallback = deepcopy(payload.get("template_fallback") or payload.get("template_candidate") or {})
    if not explicit_fallback and current_template_row and _stringify(current_template_row.get("fallback_template_id")):
        linked = get_whatsapp_template(conn, current_template_row.get("fallback_template_id"))
        if linked:
            explicit_fallback = {
                "name": linked.get("name"),
                "language": {"code": ((payload.get("template") or {}).get("language") or {}).get("code") or governance.get("selected_template_language") or linked.get("default_language")},
                "category": linked.get("category"),
                "components": deepcopy(((payload.get("template") or {}).get("components") or [])),
            }
    trial_payload = {**deepcopy(payload), "template_fallback": explicit_fallback}
    resolved = resolve_whatsapp_template_for_payload(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        payload=trial_payload,
        metadata={"default_template_language": governance.get("selected_template_language")},
        allow_alternative=True,
        fallback_only=bool(explicit_fallback),
    )
    selected_template = _stringify(resolved.get("selected_template"))
    if not resolved.get("ok") or not selected_template or selected_template == current_template:
        return None
    failover = register_whatsapp_template_failover(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        outbox_id=outbox_id,
        current_template_name=current_template or None,
        current_version_id=governance.get("selected_template_version_id"),
        fallback_template_name=selected_template,
        fallback_version_id=resolved.get("selected_template_version_id"),
        reason_code=_stringify((error_details or {}).get("error_class") or "template_failover"),
        payload_snapshot=resolved.get("payload") or payload,
        source="provider_error",
    )
    return {
        "payload": resolved.get("payload"),
        "selected_template": selected_template,
        "selected_template_version_id": resolved.get("selected_template_version_id"),
        "coverage": resolved.get("coverage"),
        "failover": failover,
        "reason_code": _stringify((error_details or {}).get("error_class") or "template_failover"),
    }
