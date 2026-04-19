from __future__ import annotations

from ..utils import from_json

def serialize_authenticated_user(user: dict, organizations: list[dict]) -> dict:
    enriched_orgs = []
    for item in organizations:
        row = dict(item)
        settings = from_json(row.get("settings_json"), {})
        if isinstance(settings, dict):
            row["settings_json"] = settings
            row.setdefault("subvertical", settings.get("subvertical") or settings.get("active_subvertical"))
        enriched_orgs.append(row)
    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "global_role": user["global_role"],
        "organizations": enriched_orgs,
    }
