from __future__ import annotations

from typing import Any

import httpx

from .db import fetch_all, fetch_one
from .repositories.integrations_runtime import (
    create_appointment_from_provider as repo_create_appointment_from_provider,
    create_oauth_state as repo_create_oauth_state,
    find_appointment_by_external_id as repo_find_appointment_by_external_id,
    find_appointment_by_id as repo_find_appointment_by_id,
    get_integration_by_id as repo_get_integration_by_id,
    get_oauth_state_by_hash as repo_get_oauth_state_by_hash,
    list_syncable_appointments as repo_list_syncable_appointments,
    mark_appointment_cancelled_from_provider as repo_mark_appointment_cancelled_from_provider,
    mark_appointment_provider_sync as repo_mark_appointment_provider_sync,
    mark_fake_google_calendar_sync as repo_mark_fake_google_calendar_sync,
    mark_integration_health as repo_mark_integration_health,
    mark_integration_sync_completed as repo_mark_integration_sync_completed,
    mark_oauth_state_consumed as repo_mark_oauth_state_consumed,
    schedule_integration_sync_now as repo_schedule_integration_sync_now,
    update_appointment_from_provider as repo_update_appointment_from_provider,
    update_integration_config as repo_update_integration_config,
)
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
    return repo_update_integration_config(conn, integration_id, config, health_status=health_status, credential_status=credential_status, last_error=last_error)


def build_google_oauth_url(conn, integration: dict[str, Any]) -> dict[str, Any]:
    config = _integration_config(integration)
    client_id = config.get("client_id") or resolve_secret(conn, organization_id=integration["organization_id"], bot_id=integration.get("bot_id"), key_name="GOOGLE_CLIENT_ID")
    redirect_uri = config.get("redirect_uri")
    if not client_id or not redirect_uri:
        raise ValueError("google_oauth_missing_client_id_or_redirect_uri")
    raw_state = new_id("oauthstate")
    scope = config.get("scopes") or DEFAULT_GOOGLE_SCOPES
    repo_create_oauth_state(
        conn,
        organization_id=integration["organization_id"],
        integration_id=integration["id"],
        provider="google_calendar",
        state_token_hash=hash_value(raw_state),
        redirect_uri=redirect_uri,
        scope=scope,
        expires_at=add_minutes(utcnow_iso(), 10),
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
    oauth_state = repo_get_oauth_state_by_hash(conn, hash_value(state))
    if not oauth_state or oauth_state.get("consumed_at"):
        raise ValueError("oauth_state_invalid")
    expires = parse_iso(oauth_state.get("expires_at"))
    if not expires or expires <= parse_iso(utcnow_iso()):
        raise ValueError("oauth_state_expired")
    integration = repo_get_integration_by_id(conn, oauth_state["integration_id"])
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
    repo_mark_oauth_state_consumed(conn, oauth_state["id"], consumed_at=utcnow_iso())
    updated = _update_integration_config(conn, integration["id"], config, health_status="healthy", credential_status="connected", last_error=None)
    if int((updated or {}).get("auto_sync_enabled") or 0) == 1:
        updated = repo_schedule_integration_sync_now(conn, integration["id"], timestamp=utcnow_iso())
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
        repo_mark_integration_health(
            conn,
            integration["id"],
            health_status="degraded",
            last_error=str(data),
            last_provider_event_at=utcnow_iso(),
            last_provider_status_code=response.status_code,
        )
        raise RetryableProviderError(f"google_{event_type.replace('.', '_')}_failed", retryable=response.status_code >= 500 or response.status_code in {401, 429}, status_code=response.status_code, details=data)
    repo_mark_integration_health(
        conn,
        integration["id"],
        health_status="healthy",
        credential_status="connected",
        last_provider_event_at=utcnow_iso(),
        last_provider_status_code=response.status_code,
    )
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
        rows = repo_list_syncable_appointments(conn, organization_id=integration["organization_id"], bot_id=integration.get("bot_id"))
        pushed = 0
        now = utcnow_iso()
        for appointment in rows:
            repo_mark_fake_google_calendar_sync(conn, appointment_id=appointment["id"], integration_id=integration["id"], synced_at=now)
            pushed += 1
        return {"provider": "google_calendar", "calendar_id": calendar_id, "pushed": pushed, "pulled": 0, "conflicts": 0, "errors": [], "fake": True}
    pushed = 0
    pulled = 0
    conflicts = 0
    errors: list[dict[str, Any]] = []
    bot_id = integration.get("bot_id")

    local_rows = repo_list_syncable_appointments(conn, organization_id=integration["organization_id"], bot_id=bot_id)
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
            repo_mark_appointment_provider_sync(
                conn,
                appointment_id=appointment["id"],
                external_id=data.get("id"),
                provider_payload=data,
                integration_id=integration["id"],
                synced_at=utcnow_iso(),
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
            existing_cancelled = repo_find_appointment_by_external_id(conn, organization_id=integration["organization_id"], external_id=item.get("id"))
            if existing_cancelled:
                repo_mark_appointment_cancelled_from_provider(conn, appointment_id=existing_cancelled['id'], provider_payload=item, synced_at=utcnow_iso())
                pulled += 1
            continue
        if not start:
            continue
        private_props = ((item.get("extendedProperties") or {}).get("private") or {})
        existing = None
        if private_props.get("waos_appointment_id"):
            existing = repo_find_appointment_by_id(conn, organization_id=integration["organization_id"], appointment_id=private_props.get("waos_appointment_id"))
        if not existing:
            existing = repo_find_appointment_by_external_id(conn, organization_id=integration["organization_id"], external_id=item.get("id"))
        if existing:
            local_updated = parse_iso(existing.get("updated_at"))
            provider_updated = parse_iso(item.get("updated"))
            if local_updated and provider_updated and local_updated > provider_updated and existing.get("synced_at"):
                conflicts += 1
                continue
            repo_update_appointment_from_provider(
                conn,
                appointment_id=existing["id"],
                scheduled_for=start,
                status=item.get("status") or existing.get("status") or "scheduled",
                notes=item.get("summary") or existing.get("notes"),
                duration_minutes=existing.get("duration_minutes") or 30,
                timezone=(item.get("start") or {}).get("timeZone") or existing.get("timezone") or config.get("timezone") or "UTC",
                provider_payload=item,
                integration_id=integration["id"],
                synced_at=utcnow_iso(),
            )
        else:
            repo_create_appointment_from_provider(
                conn,
                organization_id=integration["organization_id"],
                bot_id=bot_id,
                scheduled_for=start,
                status=item.get("status") or "scheduled",
                duration_minutes=30,
                timezone=(item.get("start") or {}).get("timeZone") or config.get("timezone") or "UTC",
                notes=item.get("summary") or "Evento importado",
                external_id=item.get("id"),
                provider_payload=item,
                integration_id=integration["id"],
                synced_at=utcnow_iso(),
            )
        pulled += 1
    config["last_real_sync_at"] = utcnow_iso()
    if data.get('nextSyncToken'):
        config['sync_token'] = data.get('nextSyncToken')
    _update_integration_config(conn, integration["id"], config, health_status="healthy", credential_status="connected", last_error=None)
    repo_mark_integration_sync_completed(conn, integration["id"], timestamp=utcnow_iso())
    _record_google_event(conn, integration, event_type="calendar.sync", status="ok" if not errors else "warning", summary="google calendar sync finished", response_payload={"calendar_id": calendar_id, "objects_pushed": pushed, "objects_pulled": pulled, "conflicts": conflicts, "errors": errors[:20], "sync_token_present": bool(config.get("sync_token"))})
    return {"provider": "google_calendar", "calendar_id": calendar_id, "objects_pushed": pushed, "objects_pulled": pulled, "conflicts": conflicts, "errors": errors[:20], "sync_state": "healthy" if not errors else "warning", "sync_token_present": bool(config.get("sync_token")), "last_real_sync_at": config.get("last_real_sync_at")}
