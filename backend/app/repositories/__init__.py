from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS: dict[str, tuple[str, str]] = {
    "create_audit_log": (".audit", "create_audit_log"),
    "get_org": (".organizations", "get_org"),
    "create_organization": (".organizations", "create_organization"),
    "get_bot": (".bots", "get_bot"),
    "list_bot_versions": (".bots", "list_bot_versions"),
    "create_bot": (".bots", "create_bot"),
    "publish_version": (".bots", "publish_version"),
    "rollback_version": (".bots", "rollback_version"),
    "get_contact": (".contacts", "get_contact"),
    "get_contact_memory": (".contacts", "get_contact_memory"),
    "upsert_contact": (".contacts", "upsert_contact"),
    "upsert_memory": (".contacts", "upsert_memory"),
    "get_conversation": (".conversations", "get_conversation"),
    "upsert_conversation": (".conversations", "upsert_conversation"),
    "create_message": (".conversations", "create_message"),
    "get_whatsapp_number_by_phone_id": (".channels", "get_whatsapp_number_by_phone_id"),
    "get_whatsapp_number_for_bot": (".channels", "get_whatsapp_number_for_bot"),
    "create_or_update_knowledge_items": (".knowledge", "create_or_update_knowledge_items"),
    "ensure_seed_data": (".seed", "ensure_seed_data"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
