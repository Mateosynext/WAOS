from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

from .db import execute, fetch_one
from .platform import create_auth_session, resolve_secret
from .utils import RetryableProviderError, add_minutes, hash_password, hash_value, new_id, parse_iso, random_token, to_json, utcnow_iso


OIDC_WELL_KNOWN = "/.well-known/openid-configuration"
DEFAULT_OIDC_SCOPES = ["openid", "profile", "email"]


def _metadata(provider: dict[str, Any]) -> dict[str, Any]:
    from .utils import from_json

    if isinstance(provider.get("metadata"), dict):
        return provider["metadata"]
    return from_json(provider.get("metadata_json"), {})


def _scopes(provider: dict[str, Any]) -> list[str]:
    from .utils import from_json

    scopes = provider.get("scopes") if isinstance(provider.get("scopes"), list) else from_json(provider.get("scopes_json"), [])
    return scopes or DEFAULT_OIDC_SCOPES


def _discover(provider: dict[str, Any]) -> dict[str, Any]:
    metadata = _metadata(provider)
    issuer = (provider.get("issuer") or metadata.get("issuer") or "").rstrip("/")
    if not issuer:
        raise ValueError("sso_missing_issuer")
    discovered = metadata.get("oidc_discovery")
    if discovered:
        return discovered
    response = httpx.get(f"{issuer}{OIDC_WELL_KNOWN}", timeout=20.0)
    data = response.json()
    if response.status_code >= 400:
        raise RetryableProviderError("oidc_discovery_failed", retryable=response.status_code >= 500 or response.status_code == 429, status_code=response.status_code, details=data)
    metadata["oidc_discovery"] = data
    execute(
        provider["conn"],
        "UPDATE sso_providers SET metadata_json = ?, updated_at = ? WHERE id = ?",
        (to_json(metadata), utcnow_iso(), provider["id"]),
    )
    return data


def _client_secret(conn, provider: dict[str, Any]) -> str | None:
    metadata = _metadata(provider)
    key_name = metadata.get("client_secret_key_name") or f"SSO_CLIENT_SECRET_{provider['id']}"
    return resolve_secret(conn, organization_id=provider["organization_id"], key_name=key_name, actor_type="runtime")


def build_sso_authorization_url(conn, provider: dict[str, Any]) -> dict[str, Any]:
    provider = {**provider, "conn": conn}
    metadata = _metadata(provider)
    discovery = _discover(provider)
    client_id = provider.get("client_id") or metadata.get("client_id")
    redirect_uri = metadata.get("redirect_uri")
    if not client_id or not redirect_uri:
        raise ValueError("sso_missing_client_id_or_redirect_uri")
    raw_state = new_id("sso_state")
    execute(
        conn,
        "INSERT INTO oauth_states (id, organization_id, integration_id, provider, state_token_hash, redirect_uri, scope, code_verifier, expires_at, consumed_at, created_at) VALUES (?, ?, NULL, 'sso', ?, ?, ?, ?, ?, NULL, ?)",
        (
            new_id("oauth"),
            provider["organization_id"],
            hash_value(raw_state),
            redirect_uri,
            " ".join(_scopes(provider)),
            provider["id"],
            add_minutes(utcnow_iso(), 10),
            utcnow_iso(),
        ),
    )
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(_scopes(provider)),
        "state": raw_state,
    }
    if metadata.get("domain_hint"):
        params["domain_hint"] = metadata["domain_hint"]
    if metadata.get("prompt"):
        params["prompt"] = metadata["prompt"]
    return {
        "authorization_url": f"{discovery['authorization_endpoint']}?{urlencode(params)}",
        "state": raw_state,
        "provider_id": provider["id"],
        "redirect_uri": redirect_uri,
        "scopes": _scopes(provider),
    }


def _token_payload(conn, provider: dict[str, Any], code: str, redirect_uri: str) -> dict[str, Any]:
    metadata = _metadata(provider)
    discovery = _discover({**provider, "conn": conn})
    client_secret = _client_secret(conn, provider)
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": provider.get("client_id") or metadata.get("client_id"),
        "redirect_uri": redirect_uri,
    }
    if client_secret:
        payload["client_secret"] = client_secret
    response = httpx.post(discovery["token_endpoint"], data=payload, timeout=20.0)
    data = response.json()
    if response.status_code >= 400:
        raise RetryableProviderError("oidc_token_exchange_failed", retryable=response.status_code >= 500 or response.status_code == 429, status_code=response.status_code, details=data)
    return data


def _userinfo_from_tokens(conn, provider: dict[str, Any], token_response: dict[str, Any]) -> dict[str, Any]:
    metadata = _metadata(provider)
    discovery = _discover({**provider, "conn": conn})
    id_token = token_response.get("id_token")
    client_id = provider.get("client_id") or metadata.get("client_id")
    claims: dict[str, Any] = {}
    if id_token:
        jwks_uri = discovery.get("jwks_uri")
        if not jwks_uri:
            raise ValueError("oidc_missing_jwks_uri")
        signing_key = jwt.PyJWKClient(jwks_uri).get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            key=signing_key.key,
            algorithms=["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
            audience=client_id,
            issuer=provider.get("issuer") or metadata.get("issuer") or discovery.get("issuer"),
            options={"verify_at_hash": False},
        )
    if not claims.get("email") and discovery.get("userinfo_endpoint") and token_response.get("access_token"):
        response = httpx.get(
            discovery["userinfo_endpoint"],
            headers={"Authorization": f"Bearer {token_response['access_token']}"},
            timeout=20.0,
        )
        data = response.json()
        if response.status_code >= 400:
            raise RetryableProviderError("oidc_userinfo_failed", retryable=response.status_code >= 500 or response.status_code == 429, status_code=response.status_code, details=data)
        claims = {**data, **claims}
    if not claims.get("sub"):
        raise ValueError("oidc_missing_subject")
    return claims


def _find_or_provision_user(conn, provider: dict[str, Any], claims: dict[str, Any]) -> dict[str, Any]:
    metadata = _metadata(provider)
    email = (claims.get("email") or "").lower().strip()
    subject = claims.get("sub")
    if not email and not subject:
        raise ValueError("oidc_missing_identity")
    identity = fetch_one(conn, "SELECT * FROM sso_identities WHERE provider_id = ? AND external_subject = ?", (provider["id"], subject)) if subject else None
    user = fetch_one(conn, "SELECT * FROM users WHERE id = ?", (identity["user_id"],)) if identity else None
    if not user and email:
        user = fetch_one(conn, "SELECT * FROM users WHERE email = ?", (email,))
    if not user:
        allowed_domains = metadata.get("allowed_domains") or ([] if not metadata.get("domain_hint") else [metadata.get("domain_hint")])
        domain = email.split("@", 1)[1] if "@" in email else ""
        if allowed_domains and domain not in allowed_domains:
            raise ValueError("sso_email_domain_not_allowed")
        if metadata.get("allow_jit_provisioning", True) is not True:
            raise ValueError("sso_jit_disabled")
        user_id = new_id("usr")
        execute(
            conn,
            "INSERT INTO users (id, email, password_hash, full_name, global_role, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
            (
                user_id,
                email or f"{subject}@sso.invalid",
                hash_password(random_token("pwd")),
                claims.get("name") or claims.get("preferred_username") or email or subject,
                metadata.get("jit_global_role") or "client",
                utcnow_iso(),
                utcnow_iso(),
            ),
        )
        user = fetch_one(conn, "SELECT * FROM users WHERE id = ?", (user_id,))
    membership = fetch_one(conn, "SELECT * FROM organization_members WHERE user_id = ? AND organization_id = ?", (user["id"], provider["organization_id"]))
    if not membership:
        execute(
            conn,
            "INSERT INTO organization_members (id, organization_id, user_id, role, is_active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
            (new_id("omem"), provider["organization_id"], user["id"], metadata.get("default_role") or "client", utcnow_iso()),
        )
    if subject:
        existing = fetch_one(conn, "SELECT * FROM sso_identities WHERE provider_id = ? AND external_subject = ?", (provider["id"], subject))
        if existing:
            execute(conn, "UPDATE sso_identities SET user_id = ?, email = ?, metadata_json = ?, last_login_at = ? WHERE id = ?", (user["id"], email, to_json(claims), utcnow_iso(), existing["id"]))
        else:
            execute(
                conn,
                "INSERT INTO sso_identities (id, organization_id, provider_id, user_id, external_subject, email, metadata_json, last_login_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (new_id("ssoid"), provider["organization_id"], provider["id"], user["id"], subject, email, to_json(claims), utcnow_iso(), utcnow_iso()),
            )
    return fetch_one(conn, "SELECT * FROM users WHERE id = ?", (user["id"],))


def exchange_sso_code(conn, *, state: str, code: str, ip_address: str | None = None, user_agent: str | None = None) -> dict[str, Any]:
    oauth_state = fetch_one(conn, "SELECT * FROM oauth_states WHERE state_token_hash = ?", (hash_value(state),))
    if not oauth_state or oauth_state.get("consumed_at") or oauth_state.get("provider") != "sso":
        raise ValueError("oauth_state_invalid")
    expires = parse_iso(oauth_state.get("expires_at"))
    if not expires or expires <= parse_iso(utcnow_iso()):
        raise ValueError("oauth_state_expired")
    provider = fetch_one(conn, "SELECT * FROM sso_providers WHERE id = ?", (oauth_state.get("code_verifier"),))
    if not provider or provider.get("status") != "active":
        raise ValueError("sso_provider_unavailable")
    token_response = _token_payload(conn, provider, code, oauth_state.get("redirect_uri") or _metadata(provider).get("redirect_uri") or "")
    claims = _userinfo_from_tokens(conn, provider, token_response)
    user = _find_or_provision_user(conn, provider, claims)
    execute(conn, "UPDATE oauth_states SET consumed_at = ? WHERE id = ?", (utcnow_iso(), oauth_state["id"]))
    session = create_auth_session(conn, user=user, ttl_minutes=int((_metadata(provider).get("session_ttl_minutes") or 720)), ip_address=ip_address, user_agent=user_agent)
    from .security import create_access_token

    access = create_access_token(user, session_id=session["id"], ttl_minutes=min(int((_metadata(provider).get("session_ttl_minutes") or 720)), 60 * 12))
    execute(conn, "UPDATE sso_providers SET last_test_at = ?, updated_at = ? WHERE id = ?", (utcnow_iso(), utcnow_iso(), provider["id"]))
    return {
        "provider": provider,
        "user": user,
        "claims": {k: claims.get(k) for k in ["sub", "email", "name", "preferred_username"] if claims.get(k) is not None},
        "access_token": access,
        "refresh_token": session["refresh_token"],
        "token_type": "bearer",
        "session": {"id": session["id"], "expires_at": session["expires_at"], "status": session["status"]},
    }


def test_sso_provider_connection(conn, provider: dict[str, Any]) -> dict[str, Any]:
    discovery = _discover({**provider, "conn": conn})
    result = {
        "issuer": discovery.get("issuer"),
        "authorization_endpoint": discovery.get("authorization_endpoint"),
        "token_endpoint": discovery.get("token_endpoint"),
        "jwks_uri": discovery.get("jwks_uri"),
        "userinfo_endpoint": discovery.get("userinfo_endpoint"),
        "scopes_supported": discovery.get("scopes_supported") or [],
    }
    return result
