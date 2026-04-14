from __future__ import annotations

from typing import Any

import httpx

from .db import execute, fetch_all, fetch_one
from .integration_observability import record_integration_event
from .platform import resolve_secret
from .utils import RetryableProviderError, add_minutes, hash_value, new_id, parse_iso, to_json, utcnow_iso

GOOGLE_OAUTH_AUTHORIZE = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_OAUTH_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"


def _fake_providers_enabled() -> bool:
    import os
    return str(os.getenv("WAOS_E2E_FAKE_PROVIDERS", "")).strip().lower() in {"1", "true", "yes", "on"}
DEFAULT_GOOGLE_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/calendar",
]


def _integration_config(integration: dict[str, Any]) -> dict[str, Any]:
    if isinstance(integration.get("config"), dict):
        return integration["config"]
    from .utils import from_json

    return from_json(integration.get("config_json"), {})


def _google_client_secret(conn, integration: dict[str, Any]) -> str | None:
    return resolve_secret(conn, organization_id=integration["organization_id"], bot_id=integration.get("bot_id"), key_name="GOOGLE_CLIENT_SECRET")


def _google_access_token(conn, integration: dict[str, Any]) -> str | None:
    return resolve_secret(conn, organization_id=integration["organization_id"], bot_id=integration.get("bot_id"), key_name="GOOGLE_ACCESS_TOKEN")


def _google_refresh_token(conn, integration: dict[str, Any]) -> str | None:
    return resolve_secret(conn, organization_id=integration["organization_id"], bot_id=integration.get("bot_id"), key_name="GOOGLE_REFRESH_TOKEN")


def _update_integration_config(conn, integration_id: str, config: dict[str, Any], *, health_status: str | None = None, credential_status: str | None = None, last_error: str | None = None) -> dict[str, Any]:
    updates = ["config_json = ?", "updated_at = ?"]
    params: list[Any] = [to_json(config), utcnow_iso()]
    if health_status is not None:
        updates.append("health_status = ?")
        params.append(health_status)
    if credential_status is not None:
        updates.append("credential_status = ?")
        params.append(credential_status)
    if last_error is not None:
        updates.append("last_error = ?")
        params.append(last_error)
    params.append(integration_id)
    execute(conn, f"UPDATE integration_connections SET {', '.join(updates)} WHERE id = ?", params)
    return fetch_one(conn, "SELECT * FROM integration_connections WHERE id = ?", (integration_id,))


def build_google_oauth_url(conn, integration: dict[str, Any]) -> dict[str, Any]:
    config = _integration_config(integration)
    client_id = config.get("client_id") or resolve_secret(conn, organization_id=integration["organization_id"], bot_id=integration.get("bot_id"), key_name="GOOGLE_CLIENT_ID")
    redirect_uri = config.get("redirect_uri")
    if not client_id or not redirect_uri:
        raise ValueError("google_oauth_missing_client_id_or_redirect_uri")
    raw_state = new_id("oauthstate")
    scope = config.get("scopes") or DEFAULT_GOOGLE_SCOPES
    execute(
        conn,
        "INSERT INTO oauth_states (id, organization_id, integration_id, provider, state_token_hash, redirect_uri, scope, code_verifier, expires_at, consumed_at, created_at) VALUES (?, ?, ?, 'google_calendar', ?, ?, ?, NULL, ?, NULL, ?)",
        (new_id("oauth"), integration["organization_id"], integration["id"], hash_value(raw_state), redirect_uri, " ".join(scope), add_minutes(utcnow_iso(), 10), utcnow_iso()),
    )
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "scope": " ".join(scope),
        "state": raw_state,
    }
    from urllib.parse import urlencode

    return {"authorization_url": f"{GOOGLE_OAUTH_AUTHORIZE}?{urlencode(params)}", "state": raw_state, "redirect_uri": redirect_uri, "scopes": scope}


def exchange_google_oauth_code(conn, *, state: str, code: str) -> dict[str, Any]:
    oauth_state = fetch_one(conn, "SELECT * FROM oauth_states WHERE state_token_hash = ?", (hash_value(state),))
    if not oauth_state or oauth_state.get("consumed_at"):
        raise ValueError("oauth_state_invalid")
    expires = parse_iso(oauth_state.get("expires_at"))
    if not expires or expires <= parse_iso(utcnow_iso()):
        raise ValueError("oauth_state_expired")
    integration = fetch_one(conn, "SELECT * FROM integration_connections WHERE id = ?", (oauth_state["integration_id"],))
    if not integration:
        raise ValueError("integration_not_found")
    config = _integration_config(integration)
    client_id = config.get("client_id") or resolve_secret(conn, organization_id=integration["organization_id"], bot_id=integration.get("bot_id"), key_name="GOOGLE_CLIENT_ID")
    client_secret = _google_client_secret(conn, integration)
    redirect_uri = oauth_state.get("redirect_uri") or config.get("redirect_uri")
    response = httpx.post(
        GOOGLE_OAUTH_TOKEN,
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=20.0,
    )
    data = response.json()
    if response.status_code >= 400:
        raise RetryableProviderError("google_oauth_exchange_failed", retryable=False, status_code=response.status_code, details=data)
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    expires_in = int(data.get("expires_in") or 3600)
    if access_token:
        from .platform import store_secret

        store_secret(conn, organization_id=integration["organization_id"], bot_id=integration.get("bot_id"), scope="bot" if integration.get("bot_id") else "tenant", key_name="GOOGLE_ACCESS_TOKEN", secret_value=access_token)
    if refresh_token:
        from .platform import store_secret

        store_secret(conn, organization_id=integration["organization_id"], bot_id=integration.get("bot_id"), scope="bot" if integration.get("bot_id") else "tenant", key_name="GOOGLE_REFRESH_TOKEN", secret_value=refresh_token)
    config["token_expires_at"] = add_minutes(utcnow_iso(), max(1, expires_in // 60))
    config["oauth_connected_at"] = utcnow_iso()
    execute(conn, "UPDATE oauth_states SET consumed_at = ? WHERE id = ?", (utcnow_iso(), oauth_state["id"]))
    updated = _update_integration_config(conn, integration["id"], config, health_status="healthy", credential_status="connected", last_error=None)
    if int((updated or {}).get("auto_sync_enabled") or 0) == 1:
        execute(conn, "UPDATE integration_connections SET next_sync_at = ?, updated_at = ? WHERE id = ?", (utcnow_iso(), utcnow_iso(), integration["id"]))
        updated = fetch_one(conn, "SELECT * FROM integration_connections WHERE id = ?", (integration["id"],))
    try:
        listing = list_google_calendars(conn, updated)
        if listing and not config.get("calendar_id"):
            config["calendar_id"] = listing[0].get("id")
            updated = _update_integration_config(conn, integration["id"], config, health_status="healthy", credential_status="connected", last_error=None)
    except Exception:
        pass
    return {"integration": updated, "config": config, "token_response": {"expires_in": expires_in, "scope": data.get("scope")}}


def _refresh_google_access_token(conn, integration: dict[str, Any]) -> str:
    config = _integration_config(integration)
    client_id = config.get("client_id") or resolve_secret(conn, organization_id=integration["organization_id"], bot_id=integration.get("bot_id"), key_name="GOOGLE_CLIENT_ID")
    client_secret = _google_client_secret(conn, integration)
    refresh_token = _google_refresh_token(conn, integration)
    if not client_id or not client_secret or not refresh_token:
        raise RetryableProviderError("missing_google_refresh_credentials", retryable=False)
    response = httpx.post(
        GOOGLE_OAUTH_TOKEN,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=20.0,
    )
    data = response.json()
    if response.status_code >= 400:
        raise RetryableProviderError("google_refresh_failed", retryable=False, status_code=response.status_code, details=data)
    access_token = data.get("access_token")
    expires_in = int(data.get("expires_in") or 3600)
    from .platform import store_secret

    store_secret(conn, organization_id=integration["organization_id"], bot_id=integration.get("bot_id"), scope="bot" if integration.get("bot_id") else "tenant", key_name="GOOGLE_ACCESS_TOKEN", secret_value=access_token)
    config["token_expires_at"] = add_minutes(utcnow_iso(), max(1, expires_in // 60))
    _update_integration_config(conn, integration["id"], config, health_status="healthy", credential_status="connected", last_error=None)
    return access_token


def get_google_access_token(conn, integration: dict[str, Any]) -> str:
    config = _integration_config(integration)
    token = _google_access_token(conn, integration)
    expires_at = parse_iso(config.get("token_expires_at"))
    now = parse_iso(utcnow_iso())
    if token and expires_at and now and expires_at > now:
        return token
    if token and not expires_at:
        return token
    return _refresh_google_access_token(conn, integration)


def _google_headers(conn, integration: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {get_google_access_token(conn, integration)}", "Accept": "application/json"}


def _record_google_event(conn, integration: dict[str, Any], *, event_type: str, status: str, summary: str, request_payload: dict[str, Any] | None = None, response_payload: dict[str, Any] | None = None, error_payload: dict[str, Any] | None = None, provider_status_code: int | None = None, external_reference: str | None = None) -> None:
    record_integration_event(
        conn,
        organization_id=integration["organization_id"],
        integration_id=integration.get("id"),
        bot_id=integration.get("bot_id"),
        provider="google_calendar",
        event_type=event_type,
        status=status,
        summary=summary,
        severity="error" if status in {"failed", "degraded"} else "info",
        request_payload=request_payload,
        response_payload=response_payload,
        error_payload=error_payload,
        provider_status_code=provider_status_code,
        external_reference=external_reference,
    )


def _google_request(conn, integration: dict[str, Any], method: str, path: str, *, event_type: str, request_payload: dict[str, Any] | None = None, allow_retry_on_401: bool = True, **kwargs: Any) -> dict[str, Any]:
    headers = {**_google_headers(conn, integration), **kwargs.pop("headers", {})}
    response = httpx.request(method, f"{GOOGLE_CALENDAR_API}{path}", headers=headers, timeout=20.0, **kwargs)
    try:
        data = response.json()
    except Exception:
        data = {"raw": response.text}
    if response.status_code == 401 and allow_retry_on_401:
        _refresh_google_access_token(conn, integration)
        return _google_request(conn, integration, method, path, event_type=event_type, request_payload=request_payload, allow_retry_on_401=False, **kwargs)
    if response.status_code >= 400:
        _record_google_event(conn, integration, event_type=event_type, status="failed", summary=f"google calendar {event_type} failed", request_payload=request_payload, response_payload=data, error_payload=data, provider_status_code=response.status_code)
        execute(conn, "UPDATE integration_connections SET health_status = 'degraded', last_error = ?, last_provider_event_at = ?, last_provider_status_code = ?, updated_at = ? WHERE id = ?", (str(data), utcnow_iso(), response.status_code, utcnow_iso(), integration["id"]))
        raise RetryableProviderError(f"google_{event_type.replace('.', '_')}_failed", retryable=response.status_code >= 500 or response.status_code in {401, 429}, status_code=response.status_code, details=data)
    execute(conn, "UPDATE integration_connections SET health_status = 'healthy', credential_status = 'connected', last_error = NULL, last_provider_event_at = ?, last_provider_status_code = ?, updated_at = ? WHERE id = ?", (utcnow_iso(), response.status_code, utcnow_iso(), integration["id"]))
    _record_google_event(conn, integration, event_type=event_type, status="ok", summary=f"google calendar {event_type} ok", request_payload=request_payload, response_payload=data, provider_status_code=response.status_code)
    return data


def list_google_calendars(conn, integration: dict[str, Any]) -> list[dict[str, Any]]:
    if _fake_providers_enabled():
        return [{"id": "primary", "summary": "WAOS Demo Calendar", "timeZone": (_integration_config(integration).get("timezone") or "America/Mexico_City")}]
    data = _google_request(conn, integration, "GET", "/users/me/calendarList", event_type="calendar.list")
    return data.get("items") or []


def test_google_calendar_connection(conn, integration: dict[str, Any]) -> dict[str, Any]:
    calendars = list_google_calendars(conn, integration)
    config = _integration_config(integration)
    calendar_id = config.get("calendar_id") or (calendars[0].get("id") if calendars else "primary")
    if _fake_providers_enabled():
        return {"calendar": {"id": calendar_id, "summary": "WAOS Demo Calendar", "timeZone": config.get("timezone") or "America/Mexico_City"}, "calendar_count": len(calendars), "fake": True}
    data = _google_request(conn, integration, "GET", f"/calendars/{_calendar_path(calendar_id)}", event_type="calendar.test", request_payload={"calendar_id": calendar_id})
    return {"calendar": {"id": data.get("id"), "summary": data.get("summary"), "timeZone": data.get("timeZone")}, "calendar_count": len(calendars)}


def _calendar_path(calendar_id: str) -> str:
    from urllib.parse import quote

    return quote(calendar_id, safe="")



def get_google_calendar_availability(conn, integration: dict[str, Any], *, time_min: str, time_max: str) -> dict[str, Any]:
    config = _integration_config(integration)
    calendar_id = config.get("calendar_id") or "primary"
    if _fake_providers_enabled():
        return {"calendar_id": calendar_id, "busy": [], "time_min": time_min, "time_max": time_max, "fake": True}
    data = _google_request(conn, integration, "POST", "/freeBusy", event_type="calendar.freebusy", request_payload={"timeMin": time_min, "timeMax": time_max, "calendar_id": calendar_id}, headers={"Content-Type": "application/json"}, json={"timeMin": time_min, "timeMax": time_max, "items": [{"id": calendar_id}]})
    busy = ((data.get("calendars") or {}).get(calendar_id) or {}).get("busy") or []
    return {"calendar_id": calendar_id, "busy": busy, "time_min": time_min, "time_max": time_max}

def sync_google_calendar(conn, integration: dict[str, Any]) -> dict[str, Any]:
    config = _integration_config(integration)
    calendar_id = config.get("calendar_id") or "primary"
    if _fake_providers_enabled():
        rows = fetch_all(
            conn,
            "SELECT * FROM appointments WHERE organization_id = ? AND COALESCE(bot_id,'') = COALESCE(?, '') AND status IN ('scheduled','confirmed') ORDER BY scheduled_for ASC LIMIT 100",
            (integration["organization_id"], integration.get("bot_id")),
        )
        pushed = 0
        now = utcnow_iso()
        for appointment in rows:
            execute(conn, "UPDATE appointments SET external_id = COALESCE(external_id, ?), provider = 'google_calendar', provider_payload_json = ?, integration_id = ?, synced_at = ?, updated_at = ? WHERE id = ?", (f"gcal_fake_{appointment["id"]}", to_json({"id": f"gcal_fake_{appointment["id"]}", "status": "confirmed"}), integration["id"], now, now, appointment["id"]))
            pushed += 1
        return {"provider": "google_calendar", "calendar_id": calendar_id, "pushed": pushed, "pulled": 0, "conflicts": 0, "errors": [], "fake": True}
    pushed = 0
    pulled = 0
    conflicts = 0
    errors: list[dict[str, Any]] = []
    bot_id = integration.get("bot_id")

    local_rows = fetch_all(
        conn,
        "SELECT * FROM appointments WHERE organization_id = ? AND COALESCE(bot_id,'') = COALESCE(?, '') AND status IN ('scheduled','confirmed') ORDER BY scheduled_for ASC LIMIT 100",
        (integration["organization_id"], bot_id),
    )
    for appointment in local_rows:
        event_payload = {
            "summary": appointment.get("notes") or f"Cita WAOS {appointment['id']}",
            "description": appointment.get("notes") or "Creado desde WAOS",
            "start": {"dateTime": appointment["scheduled_for"]},
            "end": {"dateTime": add_minutes(appointment["scheduled_for"], int(appointment.get("duration_minutes") or 30))},
        }
        try:
            if appointment.get("external_id"):
                data = _google_request(conn, integration, "PATCH", f"/calendars/{_calendar_path(calendar_id)}/events/{appointment['external_id']}", event_type="calendar.push", request_payload={"appointment_id": appointment["id"], "calendar_id": calendar_id}, headers={"Content-Type": "application/json"}, json=event_payload)
            else:
                event_payload["extendedProperties"] = {"private": {"waos_appointment_id": appointment["id"], "waos_org_id": integration["organization_id"]}}
                data = _google_request(conn, integration, "POST", f"/calendars/{_calendar_path(calendar_id)}/events", event_type="calendar.push", request_payload={"appointment_id": appointment["id"], "calendar_id": calendar_id}, headers={"Content-Type": "application/json"}, json=event_payload)
            execute(
                conn,
                "UPDATE appointments SET external_id = ?, provider = 'google_calendar', provider_payload_json = ?, integration_id = ?, synced_at = ?, updated_at = ? WHERE id = ?",
                (data.get("id"), to_json(data), integration["id"], utcnow_iso(), utcnow_iso(), appointment["id"]),
            )
            pushed += 1
        except Exception as exc:
            errors.append({"appointment_id": appointment["id"], "error": str(exc)})

    pull_params: dict[str, Any] = {"singleEvents": True, "showDeleted": True, "maxResults": 100}
    sync_token = config.get("sync_token")
    if sync_token:
        pull_params["syncToken"] = sync_token
    else:
        pull_params.update({"timeMin": utcnow_iso(), "orderBy": "startTime"})
    try:
        data = _google_request(conn, integration, "GET", f"/calendars/{_calendar_path(calendar_id)}/events", event_type="calendar.pull", request_payload={"calendar_id": calendar_id, "sync_token": sync_token or None}, params=pull_params)
    except RetryableProviderError as exc:
        data = exc.details or {}
        if exc.status_code != 410:
            raise
    if isinstance(data, dict) and data.get("error", {}).get("code") == 410:
        config.pop("sync_token", None)
        _update_integration_config(conn, integration["id"], config, health_status="degraded", credential_status="connected", last_error="google_sync_token_expired")
        data = _google_request(conn, integration, "GET", f"/calendars/{_calendar_path(calendar_id)}/events", event_type="calendar.pull.reset", request_payload={"calendar_id": calendar_id}, params={"singleEvents": True, "showDeleted": True, "timeMin": utcnow_iso(), "maxResults": 100, "orderBy": "startTime"})
    for item in data.get("items") or []:
        start = (item.get("start") or {}).get("dateTime") or (item.get("start") or {}).get("date")
        if item.get('status') == 'cancelled':
            existing_cancelled = fetch_one(conn, "SELECT * FROM appointments WHERE organization_id = ? AND external_id = ?", (integration["organization_id"], item.get("id")))
            if existing_cancelled:
                execute(conn, "UPDATE appointments SET status = 'cancelled', provider_payload_json = ?, synced_at = ?, updated_at = ? WHERE id = ?", (to_json(item), utcnow_iso(), utcnow_iso(), existing_cancelled['id']))
                pulled += 1
            continue
        if not start:
            continue
        private_props = ((item.get("extendedProperties") or {}).get("private") or {})
        existing = None
        if private_props.get("waos_appointment_id"):
            existing = fetch_one(conn, "SELECT * FROM appointments WHERE organization_id = ? AND id = ?", (integration["organization_id"], private_props.get("waos_appointment_id")))
        if not existing:
            existing = fetch_one(conn, "SELECT * FROM appointments WHERE organization_id = ? AND external_id = ?", (integration["organization_id"], item.get("id")))
        if existing:
            local_updated = parse_iso(existing.get("updated_at"))
            provider_updated = parse_iso(item.get("updated"))
            if local_updated and provider_updated and local_updated > provider_updated and existing.get("synced_at"):
                conflicts += 1
                continue
            execute(
                conn,
                "UPDATE appointments SET scheduled_for = ?, status = ?, notes = ?, duration_minutes = ?, timezone = ?, provider = 'google_calendar', provider_payload_json = ?, integration_id = ?, synced_at = ?, updated_at = ? WHERE id = ?",
                (
                    start,
                    item.get("status") or existing.get("status") or "scheduled",
                    item.get("summary") or existing.get("notes"),
                    existing.get("duration_minutes") or 30,
                    (item.get("start") or {}).get("timeZone") or existing.get("timezone") or config.get("timezone") or "UTC",
                    to_json(item),
                    integration["id"],
                    utcnow_iso(),
                    utcnow_iso(),
                    existing["id"],
                ),
            )
        else:
            execute(
                conn,
                "INSERT INTO appointments (id, organization_id, bot_id, conversation_id, contact_id, scheduled_for, status, duration_minutes, timezone, notes, created_at, updated_at, external_id, provider, provider_payload_json, integration_id, synced_at) VALUES (?, ?, ?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, 'google_calendar', ?, ?, ?)",
                (
                    new_id("appt"),
                    integration["organization_id"],
                    bot_id,
                    start,
                    item.get("status") or "scheduled",
                    30,
                    (item.get("start") or {}).get("timeZone") or config.get("timezone") or "UTC",
                    item.get("summary") or "Evento importado",
                    utcnow_iso(),
                    utcnow_iso(),
                    item.get("id"),
                    to_json(item),
                    integration["id"],
                    utcnow_iso(),
                ),
            )
        pulled += 1
    config["last_real_sync_at"] = utcnow_iso()
    if data.get('nextSyncToken'):
        config['sync_token'] = data.get('nextSyncToken')
    _update_integration_config(conn, integration["id"], config, health_status="healthy", credential_status="connected", last_error=None)
    execute(conn, "UPDATE integration_connections SET last_sync_at = ?, last_provider_event_at = ?, updated_at = ? WHERE id = ?", (utcnow_iso(), utcnow_iso(), utcnow_iso(), integration["id"]))
    _record_google_event(conn, integration, event_type="calendar.sync", status="ok" if not errors else "warning", summary="google calendar sync finished", response_payload={"calendar_id": calendar_id, "objects_pushed": pushed, "objects_pulled": pulled, "conflicts": conflicts, "errors": errors[:20], "sync_token_present": bool(config.get("sync_token"))})
    return {"provider": "google_calendar", "calendar_id": calendar_id, "objects_pushed": pushed, "objects_pulled": pulled, "conflicts": conflicts, "errors": errors[:20], "sync_state": "healthy" if not errors else "warning", "sync_token_present": bool(config.get("sync_token")), "last_real_sync_at": config.get("last_real_sync_at")}
