from __future__ import annotations

from typing import Any

from .db import execute, fetch_one
from .platform import store_secret
from .utils import add_minutes, hash_value, new_id, parse_iso, random_token, to_json, utcnow_iso


def start_meta_embedded_signup(conn, integration: dict[str, Any]) -> dict[str, Any]:
    from .utils import from_json

    config = from_json(integration.get("config_json"), {}) if not isinstance(integration.get("config"), dict) else integration["config"]
    redirect_uri = config.get("redirect_uri")
    app_id = config.get("app_id")
    config_id = config.get("config_id") or config.get("setup_config_id")
    if not redirect_uri or not app_id or not config_id:
        raise ValueError("meta_embedded_signup_missing_config")
    raw_state = new_id("meta_state")
    execute(
        conn,
        "INSERT INTO oauth_states (id, organization_id, integration_id, provider, state_token_hash, redirect_uri, scope, code_verifier, expires_at, consumed_at, created_at) VALUES (?, ?, ?, 'meta_embedded_signup', ?, ?, ?, ?, ?, NULL, ?)",
        (
            new_id("oauth"),
            integration["organization_id"],
            integration["id"],
            hash_value(raw_state),
            redirect_uri,
            "whatsapp_business_management whatsapp_business_messaging",
            integration["id"],
            add_minutes(utcnow_iso(), 20),
            utcnow_iso(),
        ),
    )
    return {
        "provider": "meta_embedded_signup",
        "integration_id": integration["id"],
        "app_id": app_id,
        "config_id": config_id,
        "redirect_uri": redirect_uri,
        "state": raw_state,
        "sessionInfoVersion": int(config.get("sessionInfoVersion") or 3),
        "setup": config.get("setup") or {},
    }


def complete_meta_embedded_signup(
    conn,
    *,
    integration: dict[str, Any],
    state: str,
    bot_id: str | None,
    phone_number_id: str,
    phone_number: str | None = None,
    waba_id: str | None = None,
    access_token: str | None = None,
    app_secret: str | None = None,
    webhook_verify_token: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    oauth_state = fetch_one(conn, "SELECT * FROM oauth_states WHERE state_token_hash = ? AND provider = 'meta_embedded_signup'", (hash_value(state),))
    if not oauth_state or oauth_state.get("consumed_at") or oauth_state.get("integration_id") != integration["id"]:
        raise ValueError("oauth_state_invalid")
    expires = parse_iso(oauth_state.get("expires_at"))
    if not expires or expires <= parse_iso(utcnow_iso()):
        raise ValueError("oauth_state_expired")
    if access_token:
        store_secret(conn, organization_id=integration["organization_id"], bot_id=bot_id, scope="bot" if bot_id else "tenant", key_name="META_ACCESS_TOKEN", secret_value=access_token)
    if app_secret:
        store_secret(conn, organization_id=integration["organization_id"], bot_id=None, scope="tenant", key_name="META_APP_SECRET", secret_value=app_secret)
    verify_token = webhook_verify_token or random_token("waverify")
    row = fetch_one(conn, "SELECT * FROM whatsapp_numbers WHERE bot_id = ?", (bot_id,)) if bot_id else None
    now = utcnow_iso()
    masked = (access_token[:4] + "***" + access_token[-3:]) if access_token else (row.get("access_token_masked") if row else "")
    metadata = payload or {}
    if row:
        execute(
            conn,
            "UPDATE whatsapp_numbers SET phone_number = ?, phone_number_id = ?, waba_id = ?, connection_status = 'connected', webhook_verify_token = ?, access_token_masked = ?, metadata_json = ?, updated_at = ? WHERE id = ?",
            (phone_number or row.get("phone_number"), phone_number_id, waba_id or row.get("waba_id"), verify_token, masked, to_json(metadata), now, row["id"]),
        )
    elif bot_id:
        execute(
            conn,
            "INSERT INTO whatsapp_numbers (id, organization_id, bot_id, provider, phone_number, phone_number_id, waba_id, connection_status, webhook_verify_token, access_token_masked, metadata_json, created_at, updated_at) VALUES (?, ?, ?, 'meta_cloud_api', ?, ?, ?, 'connected', ?, ?, ?, ?, ?)",
            (new_id("wan"), integration["organization_id"], bot_id, phone_number or "", phone_number_id, waba_id or "", verify_token, masked or "", to_json(metadata), now, now),
        )
    config = payload or {}
    config["embedded_signup_completed_at"] = now
    execute(conn, "UPDATE integration_connections SET status = 'active', health_status = 'healthy', credential_status = ?, config_json = ?, updated_at = ? WHERE id = ?", ("connected" if access_token else "configured", to_json(config), now, integration["id"]))
    execute(conn, "UPDATE oauth_states SET consumed_at = ? WHERE id = ?", (now, oauth_state["id"]))
    return {
        "integration": fetch_one(conn, "SELECT * FROM integration_connections WHERE id = ?", (integration["id"],)),
        "whatsapp_number": fetch_one(conn, "SELECT * FROM whatsapp_numbers WHERE bot_id = ?", (bot_id,)) if bot_id else None,
        "webhook_verify_token": verify_token,
    }
