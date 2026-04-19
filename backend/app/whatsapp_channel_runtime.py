from __future__ import annotations

from copy import deepcopy
from typing import Any

from .db import execute, fetch_one, table_exists
from .platform import create_runtime_callback
from .utils import RetryableProviderError, from_json, hash_value, new_id, to_json, utcnow_iso
from .whatsapp_governance import update_whatsapp_number_health
from .world_class_ext import register_channel_event
from .whatsapp_delivery_truth import record_whatsapp_delivery_status, seed_whatsapp_delivery_projection


SUPPORTED_INBOUND_TYPES = {
    "text",
    "audio",
    "image",
    "document",
    "video",
    "interactive",
    "location",
    "contacts",
}

FIRST_CLASS_OUTBOUND_TYPES = {
    "text",
    "audio",
    "image",
    "document",
    "video",
    "template",
    "interactive_button",
    "interactive_list",
    "flow_entrypoint",
    "product",
    "catalog",
    "mark_as_read",
}

OUTBOUND_ALIASES = {
    "button": "interactive_button",
    "buttons": "interactive_button",
    "interactive_buttons": "interactive_button",
    "list": "interactive_list",
    "interactive_menu": "interactive_list",
    "flow": "flow_entrypoint",
    "catalog_list": "catalog",
    "product_list": "catalog",
    "read": "mark_as_read",
    "mark_read": "mark_as_read",
}


def _stringify(value: Any) -> str:
    return str(value or "").strip()


def _clean_dict(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def _message_dump(message: Any) -> dict[str, Any]:
    if hasattr(message, "model_dump"):
        return message.model_dump(by_alias=True, exclude_none=True)
    return dict(message or {})


def _contact_name(shared_contact: dict[str, Any]) -> str:
    name = shared_contact.get("name") or {}
    return (
        _stringify(name.get("formatted_name"))
        or " ".join(part for part in [_stringify(name.get("first_name")), _stringify(name.get("last_name"))] if part).strip()
        or "Contacto"
    )


def _normalize_message_type(raw_message_type: Any) -> str:
    message_type = _stringify(raw_message_type).lower()
    return OUTBOUND_ALIASES.get(message_type, message_type)


def _ensure_string(value: Any, *, error_code: str) -> str:
    result = _stringify(value)
    if not result:
        raise ValueError(error_code)
    return result


def _ensure_dict(value: Any, *, error_code: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(error_code)
    return deepcopy(value)


def _ensure_list(value: Any, *, error_code: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(error_code)
    return deepcopy(value)


def _append_unique_event(collection: list[dict[str, Any]], payload: dict[str, Any]) -> bool:
    signature = hash_value(to_json(payload))
    for item in collection:
        if hash_value(to_json(item)) == signature:
            return False
    collection.append(payload)
    return True


def _build_event_receipt_key(event: dict[str, Any]) -> str:
    event_class = _stringify(event.get("event_class") or "event").lower() or "event"
    number_id = _stringify(((event.get("metadata") or {}).get("phone_number_id"))) or "unknown_number"
    if event_class == "message":
        message_id = _stringify(event.get("message_id"))
        if message_id:
            return f"wa:{number_id}:message:{message_id}"
        return f"wa:{number_id}:message:{hash_value(to_json(event))[:24]}"
    if event_class == "status":
        message_id = _stringify(event.get("message_id")) or "unknown"
        status = _stringify(event.get("status") or "sent")
        timestamp = _stringify(event.get("timestamp")) or hash_value(to_json(event.get("errors") or []))[:12]
        return f"wa:{number_id}:status:{message_id}:{status}:{timestamp}"
    error = event.get("error") or {}
    fingerprint = hash_value(
        "|".join(
            [
                _stringify(event.get("entry_id")),
                _stringify(event.get("field")),
                _stringify(error.get("code")),
                _stringify(error.get("title")),
                _stringify(error.get("message")),
                to_json(error.get("error_data") or {}),
            ]
        )
    )
    return f"wa:{number_id}:provider_error:{fingerprint[:32]}"


def _event_for_storage(event: dict[str, Any]) -> dict[str, Any]:
    payload = deepcopy(event)
    message = payload.get("message")
    if hasattr(message, "model_dump"):
        payload["message"] = message.model_dump(by_alias=True, exclude_none=True)
    return payload


def register_whatsapp_event_receipt(
    conn,
    *,
    organization_id: str,
    event: dict[str, Any],
) -> bool:
    if not table_exists(conn, "webhook_event_receipts"):
        return True
    event_key = _build_event_receipt_key(event)
    existing = fetch_one(conn, "SELECT * FROM webhook_event_receipts WHERE channel = 'whatsapp' AND external_event_id = ?", (event_key,))
    if existing:
        return False
    stored_event = _event_for_storage(event)
    execute(
        conn,
        """
        INSERT INTO webhook_event_receipts
        (id, channel, organization_id, external_event_id, status, payload_hash, created_at)
        VALUES (?, 'whatsapp', ?, ?, ?, ?, ?)
        """,
        (
            new_id("wreceipt"),
            organization_id,
            event_key,
            _stringify(event.get("event_class") or "event"),
            hash_value(to_json(stored_event)),
            utcnow_iso(),
        ),
    )
    return True


def summarize_whatsapp_inbound_message(message: Any) -> dict[str, Any]:
    payload = _message_dump(message)
    message_type = _stringify(payload.get("type") or "text").lower() or "text"
    normalized_type = message_type if message_type in SUPPORTED_INBOUND_TYPES else "unsupported"
    metadata = {"whatsapp": payload, "message_type": message_type}
    body = ""
    kind = normalized_type if normalized_type != "unsupported" else message_type

    if message_type == "text":
        body = _stringify(((payload.get("text") or {}).get("body")))
    elif message_type == "audio":
        audio = payload.get("audio") or {}
        transcript = _stringify(audio.get("transcript") or ((payload.get("text") or {}).get("body")))
        body = transcript or "Nota de voz recibida por WhatsApp."
        metadata["is_voice_note"] = bool(audio.get("voice"))
    elif message_type == "image":
        image = payload.get("image") or {}
        caption = _stringify(image.get("caption"))
        body = caption or "Imagen recibida por WhatsApp."
    elif message_type == "document":
        document = payload.get("document") or {}
        filename = _stringify(document.get("filename"))
        caption = _stringify(document.get("caption"))
        body = caption or (f"Documento recibido: {filename}." if filename else "Documento recibido por WhatsApp.")
    elif message_type == "video":
        video = payload.get("video") or {}
        caption = _stringify(video.get("caption"))
        body = caption or "Video recibido por WhatsApp."
    elif message_type == "location":
        location = payload.get("location") or {}
        latitude = location.get("latitude")
        longitude = location.get("longitude")
        label_bits = [item for item in [_stringify(location.get("name")), _stringify(location.get("address"))] if item]
        prefix = f"Ubicación compartida: {' - '.join(label_bits)}." if label_bits else "Ubicación compartida por WhatsApp."
        coords = f" Coordenadas: {latitude}, {longitude}." if latitude is not None and longitude is not None else ""
        body = f"{prefix}{coords}".strip()
    elif message_type == "contacts":
        contacts = payload.get("contacts") or []
        names = [_contact_name(item) for item in contacts]
        body = "Contacto compartido: " + ", ".join(names) if names else "Contacto compartido por WhatsApp."
    elif message_type == "interactive":
        interactive = payload.get("interactive") or {}
        interactive_type = _stringify(interactive.get("type") or "interactive_reply").lower()
        kind = interactive_type or "interactive"
        button_reply = interactive.get("button_reply") or {}
        list_reply = interactive.get("list_reply") or {}
        nfm_reply = interactive.get("nfm_reply") or {}
        metadata["interactive_type"] = interactive_type
        if interactive_type == "button_reply":
            title = _stringify(button_reply.get("title"))
            button_id = _stringify(button_reply.get("id"))
            body = title or button_id or "Respuesta interactiva recibida."
        elif interactive_type == "list_reply":
            title = _stringify(list_reply.get("title"))
            description = _stringify(list_reply.get("description"))
            list_id = _stringify(list_reply.get("id"))
            body = " - ".join(item for item in [title or list_id, description] if item) or "Respuesta de lista recibida."
        elif interactive_type == "nfm_reply":
            name = _stringify(nfm_reply.get("name"))
            response_json = _stringify(nfm_reply.get("response_json"))
            body = name or response_json or _stringify(nfm_reply.get("body")) or "Respuesta de flow recibida."
        else:
            body = "Respuesta interactiva recibida por WhatsApp."
    else:
        body = f"Evento de WhatsApp recibido ({message_type})."

    return {
        "kind": kind,
        "body": body,
        "message_type": message_type,
        "supported": message_type in SUPPORTED_INBOUND_TYPES,
        "metadata": metadata,
    }


def flatten_whatsapp_webhook_events(payload: Any) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for entry in getattr(payload, "entry", []) or []:
        entry_id = getattr(entry, "id", None)
        for change in getattr(entry, "changes", []) or []:
            value = getattr(change, "value", None)
            if value is None:
                continue
            metadata = value.metadata.model_dump(by_alias=True, exclude_none=True) if getattr(value, "metadata", None) else {}
            contacts = {item.wa_id: item for item in (value.contacts or []) if getattr(item, "wa_id", None)}
            for message in value.messages or []:
                normalized = summarize_whatsapp_inbound_message(message)
                normalized_metadata = normalized.pop("metadata", {}) if isinstance(normalized, dict) else {}
                wa_id = getattr(message, "from_", None)
                contact = contacts.get(wa_id)
                profile_name = None
                if contact and getattr(contact, "profile", None):
                    profile_name = contact.profile.name
                events.append(
                    {
                        "event_class": "message",
                        "entry_id": entry_id,
                        "field": getattr(change, "field", None),
                        "metadata": {**metadata, **(normalized_metadata if isinstance(normalized_metadata, dict) else {})},
                        "profile_name": profile_name,
                        "phone": wa_id,
                        "message_id": getattr(message, "id", None),
                        "message": message,
                        **normalized,
                    }
                )
            for status in value.statuses or []:
                events.append(
                    {
                        "event_class": "status",
                        "entry_id": entry_id,
                        "field": getattr(change, "field", None),
                        "metadata": metadata,
                        "message_id": getattr(status, "id", None),
                        "status": _stringify(getattr(status, "status", None)).lower() or "sent",
                        "recipient_id": getattr(status, "recipient_id", None),
                        "timestamp": getattr(status, "timestamp", None),
                        "conversation": status.conversation.model_dump(by_alias=True, exclude_none=True) if getattr(status, "conversation", None) else {},
                        "pricing": status.pricing.model_dump(by_alias=True, exclude_none=True) if getattr(status, "pricing", None) else {},
                        "errors": [dict(item) for item in (getattr(status, "errors", None) or [])],
                    }
                )
            for error in value.errors or []:
                events.append(
                    {
                        "event_class": "provider_error",
                        "entry_id": entry_id,
                        "field": getattr(change, "field", None),
                        "metadata": metadata,
                        "error": error.model_dump(by_alias=True, exclude_none=True),
                    }
                )
    return events


def _normalize_media_payload(message_type: str, payload: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    media = deepcopy(payload.get("media") or payload.get(message_type) or {})
    if not isinstance(media, dict):
        raise ValueError(f"whatsapp_{message_type}_payload_invalid")
    if not media.get("id") and not media.get("link"):
        raise ValueError(f"whatsapp_{message_type}_id_or_link_required")
    caption = _stringify(media.get("caption"))
    filename = _stringify(media.get("filename"))
    labels = {
        "audio": "Audio enviado por WhatsApp.",
        "image": "Imagen enviada por WhatsApp.",
        "document": f"Documento enviado: {filename}." if filename else "Documento enviado por WhatsApp.",
        "video": "Video enviado por WhatsApp.",
    }
    return media, caption or labels[message_type], message_type


def _normalize_template_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    template = _ensure_dict(payload.get("template") or {}, error_code="whatsapp_template_payload_invalid")
    template["name"] = _ensure_string(template.get("name"), error_code="whatsapp_template_name_required")
    language = template.get("language") or {}
    if not isinstance(language, dict) or not _stringify(language.get("code")):
        template["language"] = {"code": _stringify(payload.get("language_code") or "es") or "es"}
    components = template.get("components")
    if components is not None and not isinstance(components, list):
        raise ValueError("whatsapp_template_components_invalid")
    return template, _stringify(payload.get("summary")) or f"Template enviado: {template.get('name')}.", "template"


def _normalize_buttons_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    interactive = _ensure_dict(payload.get("interactive") or {}, error_code="whatsapp_interactive_payload_invalid")
    buttons = _ensure_list(interactive.get("buttons") or [], error_code="whatsapp_interactive_buttons_required")
    normalized_buttons: list[dict[str, Any]] = []
    for index, button in enumerate(buttons, start=1):
        item = _ensure_dict(button, error_code="whatsapp_interactive_button_invalid")
        button_id = _ensure_string(item.get("id"), error_code=f"whatsapp_interactive_button_id_required:{index}")
        title = _ensure_string(item.get("title"), error_code=f"whatsapp_interactive_button_title_required:{index}")
        normalized_buttons.append({"type": "reply", "reply": {"id": button_id, "title": title}})
    if len(normalized_buttons) > 3:
        raise ValueError("whatsapp_interactive_buttons_limit_exceeded")
    interactive["buttons"] = normalized_buttons
    summary = _stringify((interactive.get("body") or {}).get("text")) or _stringify(payload.get("summary")) or "Botones interactivos enviados por WhatsApp."
    return interactive, summary, "interactive"


def _normalize_list_sections(raw_sections: list[Any]) -> list[dict[str, Any]]:
    normalized_sections: list[dict[str, Any]] = []
    for index, section in enumerate(raw_sections, start=1):
        item = _ensure_dict(section, error_code=f"whatsapp_interactive_section_invalid:{index}")
        title = _ensure_string(item.get("title"), error_code=f"whatsapp_interactive_section_title_required:{index}")
        rows = _ensure_list(item.get("rows") or item.get("product_items") or [], error_code=f"whatsapp_interactive_section_rows_required:{index}")
        normalized_rows: list[dict[str, Any]] = []
        normalized_product_items: list[dict[str, Any]] = []
        for row_index, row in enumerate(rows, start=1):
            row_item = _ensure_dict(row, error_code=f"whatsapp_interactive_row_invalid:{index}:{row_index}")
            if row_item.get("product_retailer_id"):
                normalized_product_items.append({"product_retailer_id": _ensure_string(row_item.get("product_retailer_id"), error_code=f"whatsapp_catalog_product_required:{index}:{row_index}")})
                continue
            normalized_rows.append(
                {
                    "id": _ensure_string(row_item.get("id"), error_code=f"whatsapp_interactive_row_id_required:{index}:{row_index}"),
                    "title": _ensure_string(row_item.get("title"), error_code=f"whatsapp_interactive_row_title_required:{index}:{row_index}"),
                    "description": _stringify(row_item.get("description")) or None,
                }
            )
        normalized_sections.append(
            _clean_dict(
                {
                    "title": title,
                    "rows": normalized_rows or None,
                    "product_items": normalized_product_items or None,
                }
            )
        )
    return normalized_sections


def _normalize_interactive_list_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    interactive = _ensure_dict(payload.get("interactive") or {}, error_code="whatsapp_interactive_payload_invalid")
    interactive["button"] = _ensure_string(interactive.get("button"), error_code="whatsapp_interactive_list_button_required")
    interactive["sections"] = _normalize_list_sections(_ensure_list(interactive.get("sections") or [], error_code="whatsapp_interactive_list_sections_required"))
    summary = _stringify((interactive.get("body") or {}).get("text")) or _stringify(payload.get("summary")) or "Lista interactiva enviada por WhatsApp."
    return interactive, summary, "interactive"


def _normalize_flow_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    flow = _ensure_dict(payload.get("flow") or payload.get("interactive") or {}, error_code="whatsapp_flow_payload_invalid")
    flow["flow_id"] = _ensure_string(flow.get("flow_id"), error_code="whatsapp_flow_id_required")
    if flow.get("flow_action_payload") is not None and not isinstance(flow.get("flow_action_payload"), dict):
        raise ValueError("whatsapp_flow_action_payload_invalid")
    summary = _stringify((flow.get("body") or {}).get("text")) or _stringify(payload.get("summary")) or "Flow de WhatsApp enviado."
    return flow, summary, "interactive"


def _normalize_product_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    product = _ensure_dict(payload.get("product") or {}, error_code="whatsapp_product_payload_invalid")
    product["catalog_id"] = _ensure_string(product.get("catalog_id"), error_code="whatsapp_product_catalog_required")
    product["product_retailer_id"] = _ensure_string(product.get("product_retailer_id"), error_code="whatsapp_product_retailer_required")
    summary = _stringify(payload.get("summary")) or _stringify((product.get("body") or {}).get("text")) or "Producto enviado por WhatsApp."
    return product, summary, "product"


def _normalize_catalog_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    catalog = _ensure_dict(payload.get("catalog") or payload.get("interactive") or {}, error_code="whatsapp_catalog_payload_invalid")
    catalog["catalog_id"] = _ensure_string(catalog.get("catalog_id"), error_code="whatsapp_catalog_id_required")
    catalog["sections"] = _normalize_list_sections(_ensure_list(catalog.get("sections") or [], error_code="whatsapp_catalog_sections_required"))
    summary = _stringify((catalog.get("body") or {}).get("text")) or _stringify(payload.get("summary")) or "Catálogo enviado por WhatsApp."
    return catalog, summary, "catalog"


def normalize_whatsapp_outbound_request(*, body: str | None = None, whatsapp_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = deepcopy(whatsapp_payload or {})
    fallback_body = _stringify(body)
    provider_payload = payload.get("provider_payload")
    if provider_payload:
        message_type = _normalize_message_type(provider_payload.get("type") or ("mark_as_read" if provider_payload.get("status") == "read" else "text"))
        payload.setdefault("message_type", message_type)
    else:
        message_type = _normalize_message_type(payload.get("message_type") or payload.get("type") or ("text" if fallback_body else ""))
        payload["message_type"] = message_type

    if not message_type:
        raise ValueError("whatsapp_message_type_required")

    kind = message_type
    summary = fallback_body

    if message_type == "text":
        text_body = _ensure_string(payload.get("body") or fallback_body, error_code="whatsapp_text_body_required")
        payload["body"] = text_body
        summary = text_body
        kind = "text"
    elif message_type in {"audio", "image", "document", "video"}:
        media, summary, kind = _normalize_media_payload(message_type, payload)
        payload["media"] = media
    elif message_type == "template":
        template, summary, kind = _normalize_template_payload(payload)
        payload["template"] = template
    elif message_type == "interactive_button":
        interactive, summary, kind = _normalize_buttons_payload(payload)
        payload["interactive"] = interactive
    elif message_type == "interactive_list":
        interactive, summary, kind = _normalize_interactive_list_payload(payload)
        payload["interactive"] = interactive
    elif message_type == "flow_entrypoint":
        flow, summary, kind = _normalize_flow_payload(payload)
        payload["flow"] = flow
    elif message_type == "product":
        product, summary, kind = _normalize_product_payload(payload)
        payload["product"] = product
    elif message_type == "catalog":
        catalog, summary, kind = _normalize_catalog_payload(payload)
        payload["catalog"] = catalog
    elif message_type == "mark_as_read":
        read_target = _ensure_string(payload.get("message_id") or payload.get("read_target") or payload.get("target_message_id"), error_code="whatsapp_mark_as_read_message_id_required")
        payload["read_target"] = read_target
        summary = _stringify(payload.get("summary")) or f"Mensaje marcado como leído: {read_target}."
        kind = "status"
    else:
        raise ValueError(f"unsupported_whatsapp_message_type:{message_type}")

    return {"message_type": message_type, "kind": kind, "summary": summary, "payload": payload}


def build_whatsapp_outbound_payload(payload: dict[str, Any], *, message: dict[str, Any] | None = None) -> dict[str, Any]:
    provider_payload = deepcopy(payload.get("provider_payload") or {})
    if provider_payload:
        return provider_payload

    normalized = normalize_whatsapp_outbound_request(body=payload.get("body") or (message or {}).get("body"), whatsapp_payload=payload)
    message_type = normalized["message_type"]
    normalized_payload = normalized["payload"]

    if message_type == "text":
        return {"type": "text", "text": {"body": normalized_payload.get("body")}}
    if message_type in {"audio", "image", "document", "video"}:
        media = deepcopy(normalized_payload.get("media") or {})
        return _clean_dict({"type": message_type, message_type: media})
    if message_type == "template":
        return {"type": "template", "template": deepcopy(normalized_payload.get("template") or {})}
    if message_type == "interactive_button":
        interactive = deepcopy(normalized_payload.get("interactive") or {})
        action = {"buttons": deepcopy(interactive.get("buttons") or [])}
        return {
            "type": "interactive",
            "interactive": _clean_dict(
                {
                    "type": "button",
                    "header": deepcopy(interactive.get("header")),
                    "body": deepcopy(interactive.get("body")),
                    "footer": deepcopy(interactive.get("footer")),
                    "action": action,
                }
            ),
        }
    if message_type == "interactive_list":
        interactive = deepcopy(normalized_payload.get("interactive") or {})
        action = _clean_dict({"button": interactive.get("button"), "sections": deepcopy(interactive.get("sections") or [])})
        return {
            "type": "interactive",
            "interactive": _clean_dict(
                {
                    "type": "list",
                    "header": deepcopy(interactive.get("header")),
                    "body": deepcopy(interactive.get("body")),
                    "footer": deepcopy(interactive.get("footer")),
                    "action": action,
                }
            ),
        }
    if message_type == "flow_entrypoint":
        flow = deepcopy(normalized_payload.get("flow") or {})
        parameters = _clean_dict(
            {
                "flow_message_version": flow.get("flow_message_version") or "3",
                "flow_token": flow.get("flow_token"),
                "flow_id": flow.get("flow_id"),
                "flow_cta": flow.get("flow_cta") or "Abrir",
                "flow_action": flow.get("flow_action") or "navigate",
                "flow_action_payload": deepcopy(flow.get("flow_action_payload")),
                "mode": flow.get("mode"),
            }
        )
        return {
            "type": "interactive",
            "interactive": _clean_dict(
                {
                    "type": "flow",
                    "header": deepcopy(flow.get("header")),
                    "body": deepcopy(flow.get("body")),
                    "footer": deepcopy(flow.get("footer")),
                    "action": {"name": "flow", "parameters": parameters},
                }
            ),
        }
    if message_type == "product":
        product = deepcopy(normalized_payload.get("product") or {})
        return {
            "type": "interactive",
            "interactive": {
                "type": "product",
                "body": deepcopy(product.get("body")) or {"text": _stringify(product.get("body_text")) or "Te comparto este producto."},
                "footer": deepcopy(product.get("footer")),
                "action": {
                    "catalog_id": product.get("catalog_id"),
                    "product_retailer_id": product.get("product_retailer_id"),
                },
            },
        }
    if message_type == "catalog":
        catalog = deepcopy(normalized_payload.get("catalog") or {})
        return {
            "type": "interactive",
            "interactive": _clean_dict(
                {
                    "type": "product_list",
                    "header": deepcopy(catalog.get("header")),
                    "body": deepcopy(catalog.get("body")),
                    "footer": deepcopy(catalog.get("footer")),
                    "action": {
                        "catalog_id": catalog.get("catalog_id"),
                        "sections": deepcopy(catalog.get("sections") or []),
                    },
                }
            ),
        }
    if message_type == "mark_as_read":
        return {"status": "read", "message_id": normalized_payload.get("read_target")}
    raise RetryableProviderError(f"unsupported_whatsapp_message_type:{message_type}", retryable=False)


def apply_whatsapp_status_event(
    conn,
    *,
    organization_id: str,
    bot_id: str | None,
    conversation_id: str | None,
    event: dict[str, Any],
    correlation_id: str | None = None,
) -> dict[str, Any]:
    provider_message_id = _stringify(event.get("message_id"))
    provider_status = _stringify(event.get("status") or "sent").lower() or "sent"
    mapped_status = provider_status if provider_status in {"sent", "delivered", "read", "failed"} else "sent"
    callback_payload = {
        "provider_message_id": provider_message_id,
        "status": provider_status,
        "conversation": event.get("conversation") or {},
        "pricing": event.get("pricing") or {},
        "errors": event.get("errors") or [],
        "correlation_id": correlation_id,
    }

    outbox = fetch_one(conn, "SELECT * FROM outbox_messages WHERE provider_message_id = ? ORDER BY created_at DESC LIMIT 1", (provider_message_id,)) if provider_message_id else None
    message = fetch_one(conn, "SELECT * FROM messages WHERE external_id = ? ORDER BY created_at DESC LIMIT 1", (provider_message_id,)) if provider_message_id else None

    if outbox:
        response_payload = from_json(outbox.get("provider_response_json"), {})
        status_events = response_payload.setdefault("status_events", [])
        _append_unique_event(status_events, callback_payload)
        execute(
            conn,
            "UPDATE outbox_messages SET status = ?, provider_response_json = ?, provider_status_code = COALESCE(provider_status_code, ?) WHERE id = ?",
            (mapped_status, to_json(response_payload), 200 if mapped_status != "failed" else 500, outbox["id"]),
        )
        outbox = fetch_one(conn, "SELECT * FROM outbox_messages WHERE id = ?", (outbox["id"],)) or outbox
    if message:
        metadata = from_json(message.get("metadata_json"), {})
        whatsapp_metadata = metadata.setdefault("whatsapp", {})
        status_events = whatsapp_metadata.setdefault("status_events", [])
        _append_unique_event(status_events, callback_payload)
        execute(conn, "UPDATE messages SET status = ?, metadata_json = ? WHERE id = ?", (mapped_status, to_json(metadata), message["id"]))
        message = fetch_one(conn, "SELECT * FROM messages WHERE id = ?", (message["id"],)) or message

    if outbox:
        seed_whatsapp_delivery_projection(conn, outbox=outbox, message=message)
    truth_projection = record_whatsapp_delivery_status(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        event=event,
        outbox=outbox,
        message=message,
        source="webhook",
    )
    delivery_attempt_id = _stringify((from_json((outbox or {}).get("payload_json"), {}).get("delivery_attempt_id")))
    if delivery_attempt_id:
        from backend.worker import _update_delivery_attempt  # local import to avoid circular import at module load

        _update_delivery_attempt(
            conn,
            delivery_attempt_id,
            status=("delivered" if mapped_status in {"delivered", "read"} else mapped_status),
            provider="whatsapp",
            metadata_patch={
                "delivery_truth_status": mapped_status,
                "provider_message_id": provider_message_id,
                "errors": event.get("errors") or [],
            },
            delivered=mapped_status in {"delivered", "read"},
        )

    register_channel_event(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        conversation_id=conversation_id or (message or {}).get("conversation_id") or (outbox or {}).get("conversation_id"),
        contact_id=(message or {}).get("contact_id"),
        channel="whatsapp",
        direction="outbound",
        event_type=f"whatsapp_status_{provider_status}",
        body=(message or {}).get("body"),
        external_thread_id=((event.get("conversation") or {}).get("id") or provider_message_id),
        external_user_id=event.get("recipient_id"),
        identities=[{"type": "phone", "value": event.get("recipient_id"), "confidence": 1.0}] if event.get("recipient_id") else None,
        metadata=callback_payload,
    )
    create_runtime_callback(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        execution_run_id=(outbox or {}).get("execution_run_id"),
        callback_type=f"whatsapp.status.{provider_status}",
        target="provider://whatsapp",
        status="failed" if mapped_status == "failed" else "delivered",
        payload=callback_payload,
        response={"outbox_id": (outbox or {}).get("id"), "message_id": (message or {}).get("id")},
        last_error=((event.get("errors") or [{}])[0].get("message") if event.get("errors") else None),
    )
    if mapped_status == "failed" and bot_id:
        failed_error = {"error": (event.get("errors") or [{}])[0]} if event.get("errors") else {"error": {"message": "delivery_failed"}}
        update_whatsapp_number_health(conn, organization_id=organization_id, bot_id=bot_id, status_code=500, payload=failed_error, success=False, event_type="status_failed")
    elif mapped_status in {"sent", "delivered", "read"} and bot_id:
        update_whatsapp_number_health(conn, organization_id=organization_id, bot_id=bot_id, payload={"status": mapped_status}, success=True, event_type=f"status_{mapped_status}")
    return {
        "provider_message_id": provider_message_id,
        "status": mapped_status,
        "outbox_id": (outbox or {}).get("id"),
        "message_id": (message or {}).get("id"),
        "delivery_truth_status": (truth_projection or {}).get("current_status") or mapped_status,
        "accepted_at": (truth_projection or {}).get("accepted_at"),
        "delivered_at": (truth_projection or {}).get("delivered_at"),
        "read_at": (truth_projection or {}).get("read_at"),
        "failed_at": (truth_projection or {}).get("failed_at"),
    }


def apply_whatsapp_provider_error(
    conn,
    *,
    organization_id: str,
    bot_id: str | None,
    event: dict[str, Any],
    correlation_id: str | None = None,
) -> dict[str, Any]:
    error = deepcopy(event.get("error") or {})
    payload = {**error, "correlation_id": correlation_id, "occurred_at": utcnow_iso()}
    register_channel_event(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        channel="whatsapp",
        direction="system",
        event_type="whatsapp_provider_error",
        body=_stringify(error.get("message") or error.get("title") or "Error del provider de WhatsApp."),
        metadata=payload,
    )
    create_runtime_callback(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        execution_run_id=None,
        callback_type="whatsapp.provider_error",
        target="provider://whatsapp",
        status="failed",
        payload=payload,
        response=error,
        last_error=_stringify(error.get("message") or error.get("title") or "whatsapp_provider_error"),
    )
    if bot_id:
        update_whatsapp_number_health(conn, organization_id=organization_id, bot_id=bot_id, status_code=500, payload={"error": error}, success=False, event_type="webhook_provider_error")
    return payload
