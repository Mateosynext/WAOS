from __future__ import annotations


def serialize_authenticated_user(user: dict, organizations: list[dict]) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "global_role": user["global_role"],
        "organizations": organizations,
    }
