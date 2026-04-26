from __future__ import annotations

import json

from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from backend.app.errors import AppError, app_error_from_validation, error_body, error_response
from backend.app.http_runtime import extract_org_id
from backend.app.main import app
from backend.app.platform.security import create_auth_session, refresh_auth_session
from backend.app.request_context import extract_bot_id
from backend.app.security import create_access_token, get_current_user
from backend.app.db import get_connection, init_db, fetch_one, execute
from starlette.requests import Request


client = TestClient(app)


def test_extract_scope_accepts_frontend_header_aliases() -> None:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/conversations",
        "headers": [(b"x-waos-org-id", b"org_alias"), (b"x-waos-bot-id", b"bot_alias")],
        "query_string": b"",
        "path_params": {},
    }
    request = Request(scope)
    assert extract_org_id(request) == "org_alias"
    assert extract_bot_id(request) == "bot_alias"



def test_conflicting_scope_values_return_consistent_400() -> None:
    response = client.get("/health", headers={"x-waos-org-id": "org_a", "x-organization-id": "org_b"})
    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "scope_conflict"
    assert response.headers.get("x-request-id")



def test_validation_errors_use_envelope_contract() -> None:
    response = client.post("/api/v1/auth/login", json={"email": "bad", "password": "short"})
    assert response.status_code == 422
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "validation_error"
    assert payload.get("request_id")



def test_validation_error_details_with_value_error_ctx_are_json_serializable() -> None:
    exc = RequestValidationError([
        {
            "type": "value_error",
            "loc": ("body",),
            "msg": "Value error, godmode requires AI_ENABLE_GODMODE=true",
            "input": {"intensity": "godmode"},
            "ctx": {"error": ValueError("godmode requires AI_ENABLE_GODMODE=true")},
        }
    ])
    payload = error_body(app_error_from_validation(exc))
    json.dumps(payload)
    assert payload["error"]["details"]["errors"][0]["ctx"]["error"] == "godmode requires AI_ENABLE_GODMODE=true"


def test_error_response_sanitizes_nested_non_json_objects() -> None:
    class Weird:
        def __str__(self) -> str:
            return "weird-object"

    response = error_response(AppError("bad", details={"error": RuntimeError("boom"), "nested": [{"value": Weird()}]}))
    assert response.status_code == 400
    payload = json.loads(response.body.decode("utf-8"))
    assert payload["error"]["details"]["error"] == "boom"
    assert payload["error"]["details"]["nested"][0]["value"] == "weird-object"


def test_session_idle_timeout_is_persisted_on_refresh_cycle() -> None:
    init_db()
    with get_connection() as conn:
        user = fetch_one(conn, "SELECT * FROM users ORDER BY created_at ASC LIMIT 1")
        if not user:
            execute(conn, "INSERT INTO users (id, email, full_name, global_role, password_hash, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)", ("usr_test_idle", "idle@example.com", "Idle User", "org_admin", "$2b$12$abcdefghijklmnopqrstuv12345678901234567890123456789012"))
            user = fetch_one(conn, "SELECT * FROM users WHERE id = ?", ("usr_test_idle",))
        session = create_auth_session(conn, user=user, ttl_minutes=120, idle_timeout_minutes=17)
        assert int(session["idle_timeout_minutes"]) == 17
        refreshed = refresh_auth_session(conn, refresh_token=session["refresh_token"], ttl_minutes=180)
        assert refreshed is not None
        assert int(refreshed["idle_timeout_minutes"]) == 17
