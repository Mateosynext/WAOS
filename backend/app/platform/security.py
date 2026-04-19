from __future__ import annotations

import hashlib
import hmac
from typing import Any

from ..config import settings
from ..db import execute, fetch_all, fetch_one
from ..contracts import count_row, runtime_callback_row, integration_sync_run_row
from ..verticals import get_vertical_profile
from ..utils import (
    add_minutes,
    current_mfa_code,
    decrypt_secret,
    encrypt_secret,
    from_json,
    generate_recovery_codes,
    generate_totp_secret,
    hash_value,
    new_id,
    next_day_iso,
    parse_iso,
    provisioning_uri,
    qr_svg_data_url,
    random_token,
    to_json,
    utcnow_iso,
    verify_totp,
)

def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:3]}***{value[-3:]}"


def _factor_secret(factor: dict[str, Any] | None) -> str | None:
    if not factor:
        return None
    if factor.get('secret_encrypted'):
        return decrypt_secret(factor['secret_encrypted'], settings.secret_encryption_key)
    secret = factor.get('secret')
    return secret or None


def serialize_mfa_factor(factor: dict[str, Any] | None) -> dict[str, Any] | None:
    if not factor:
        return None
    return {
        'id': factor['id'],
        'factor_type': factor['factor_type'],
        'status': factor['status'],
        'label': factor.get('label') or 'Authenticator app',
        'secret_masked': factor.get('secret_masked') or mask_secret('configured'),
        'enrolled_at': factor.get('enrolled_at'),
        'verified_at': factor.get('verified_at'),
        'last_used_at': factor.get('last_used_at'),
        'revoked_at': factor.get('revoked_at'),
        'recovery_codes_remaining': len([item for item in from_json(factor.get('recovery_codes_json'), []) if not item.get('used_at')]),
    }


def _cleanup_login_attempt(conn, *, scope_key: str) -> None:
    execute(conn, "DELETE FROM auth_login_attempts WHERE scope_key = ?", (scope_key,))


def _revoke_refresh_token_family(conn, *, family_id: str, revoked_at: str, reason: str) -> None:
    execute(conn, "UPDATE auth_refresh_tokens SET status = CASE WHEN status = 'reused' THEN status ELSE 'revoked' END, revoked_at = COALESCE(revoked_at, ?) WHERE family_id = ?", (revoked_at, family_id))
    execute(conn, "UPDATE auth_sessions SET status = CASE WHEN status = 'revoked' THEN status ELSE 'revoked' END, revoked_at = COALESCE(revoked_at, ?), refresh_token_reuse_detected_at = CASE WHEN ? = 'refresh_token_reuse' THEN ? ELSE refresh_token_reuse_detected_at END WHERE refresh_token_family_id = ?", (revoked_at, reason, revoked_at, family_id))


def get_security_policy(conn, *, organization_id: str) -> dict[str, Any]:
    row = fetch_one(conn, "SELECT * FROM organization_security_policies WHERE organization_id = ?", (organization_id,))
    if row:
        return {**row, "ip_allowlist": from_json(row.get("ip_allowlist_json"), []), "allowed_origins": from_json(row.get("allowed_origins_json"), [])}
    return {
        "organization_id": organization_id,
        "require_mfa": 0,
        "require_sso": 0,
        "session_ttl_minutes": settings.refresh_token_ttl_minutes,
        "session_idle_timeout_minutes": settings.session_idle_timeout_minutes,
        "step_up_window_minutes": settings.step_up_window_minutes,
        "max_sessions_per_user": settings.max_sessions_per_user,
        "require_dual_approval_releases": 1,
        "webhook_signature_required": 1,
        "strict_idempotency": 1,
        "ip_allowlist": [],
        "allowed_origins": [],
    }


def upsert_rate_limit_policy(
    conn,
    *,
    organization_id: str,
    bot_id: str | None,
    scope: str,
    window_seconds: int,
    max_requests: int,
    is_active: bool,
) -> dict[str, Any]:
    existing = fetch_one(
        conn,
        "SELECT * FROM rate_limit_policies WHERE organization_id = ? AND COALESCE(bot_id,'') = COALESCE(?, '') AND scope = ?",
        (organization_id, bot_id, scope),
    )
    now = utcnow_iso()
    if existing:
        execute(
            conn,
            """
            UPDATE rate_limit_policies
            SET window_seconds = ?, max_requests = ?, is_active = ?, updated_at = ?
            WHERE id = ?
            """,
            (window_seconds, max_requests, int(is_active), now, existing["id"]),
        )
        return fetch_one(conn, "SELECT * FROM rate_limit_policies WHERE id = ?", (existing["id"],))
    policy_id = new_id("rlp")
    execute(
        conn,
        """
        INSERT INTO rate_limit_policies
        (id, organization_id, bot_id, scope, window_seconds, max_requests, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (policy_id, organization_id, bot_id, scope, window_seconds, max_requests, int(is_active), now, now),
    )
    return fetch_one(conn, "SELECT * FROM rate_limit_policies WHERE id = ?", (policy_id,))


def list_rate_limit_policies(conn, *, organization_id: str, bot_id: str | None = None) -> list[dict[str, Any]]:
    if bot_id:
        return fetch_all(conn, "SELECT * FROM rate_limit_policies WHERE organization_id = ? AND (bot_id = ? OR bot_id IS NULL) ORDER BY updated_at DESC", (organization_id, bot_id))
    return fetch_all(conn, "SELECT * FROM rate_limit_policies WHERE organization_id = ? ORDER BY updated_at DESC", (organization_id,))


def check_rate_limit(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    phone: str | None,
) -> dict[str, Any]:
    policies = fetch_all(
        conn,
        "SELECT * FROM rate_limit_policies WHERE organization_id = ? AND is_active = 1 AND (bot_id = ? OR bot_id IS NULL) ORDER BY CASE WHEN bot_id IS NULL THEN 1 ELSE 0 END, updated_at DESC",
        (organization_id, bot_id),
    )
    if not policies:
        return {"allowed": True, "checks": []}
    checks: list[dict[str, Any]] = []
    now = parse_iso(utcnow_iso())
    for policy in policies:
        scope_key = bot_id if policy["scope"] == "bot" else (phone or "unknown")
        window_start = (now - __import__('datetime').timedelta(seconds=int(policy["window_seconds"]))).replace(microsecond=0).isoformat().replace('+00:00','Z')
        execute(conn, "DELETE FROM request_counters WHERE last_seen_at < ?", (window_start,))
        current = fetch_one(
            conn,
            "SELECT SUM(request_count) AS total FROM request_counters WHERE organization_id = ? AND COALESCE(bot_id,'') = COALESCE(?, '') AND scope = ? AND scope_key = ? AND window_started_at >= ?",
            (organization_id, policy.get("bot_id"), policy["scope"], scope_key, window_start),
        )
        current_count = int((current or {}).get("total") or 0)
        allowed = current_count < int(policy["max_requests"])
        checks.append({
            "policy_id": policy["id"],
            "scope": policy["scope"],
            "scope_key": scope_key,
            "current": current_count,
            "max_requests": int(policy["max_requests"]),
            "window_seconds": int(policy["window_seconds"]),
            "allowed": allowed,
        })
        if not allowed:
            return {"allowed": False, "checks": checks}
        counter_id = new_id("ctr")
        execute(
            conn,
            """
            INSERT INTO request_counters
            (id, organization_id, bot_id, scope, scope_key, window_started_at, request_count, last_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (counter_id, organization_id, policy.get("bot_id"), policy["scope"], scope_key, utcnow_iso(), utcnow_iso()),
        )
    return {"allowed": True, "checks": checks}


def check_login_rate_limit(conn, *, scope_key: str) -> dict[str, Any]:
    row = fetch_one(conn, "SELECT * FROM auth_login_attempts WHERE scope_key = ?", (scope_key,))
    now = parse_iso(utcnow_iso())
    if not row:
        return {"allowed": True, "remaining": settings.login_rate_limit_max_attempts}
    blocked_until = parse_iso(row.get("blocked_until"))
    if blocked_until and now and blocked_until > now:
        remaining_seconds = max(0, int((blocked_until - now).total_seconds()))
        return {"allowed": False, "blocked_until": row.get("blocked_until"), "retry_after_seconds": remaining_seconds}
    first_attempt = parse_iso(row.get("first_attempt_at"))
    if not first_attempt or not now:
        return {"allowed": True, "remaining": settings.login_rate_limit_max_attempts}
    if (now - first_attempt).total_seconds() > settings.login_rate_limit_window_seconds:
        _cleanup_login_attempt(conn, scope_key=scope_key)
        return {"allowed": True, "remaining": settings.login_rate_limit_max_attempts}
    attempts = int(row.get("attempt_count") or 0)
    return {"allowed": attempts < settings.login_rate_limit_max_attempts, "remaining": max(0, settings.login_rate_limit_max_attempts - attempts), "blocked_until": row.get("blocked_until")}


def record_login_attempt(conn, *, scope_key: str, success: bool, ip_address: str | None = None, user_agent: str | None = None) -> dict[str, Any]:
    if success:
        _cleanup_login_attempt(conn, scope_key=scope_key)
        return {"allowed": True, "remaining": settings.login_rate_limit_max_attempts}
    row = fetch_one(conn, "SELECT * FROM auth_login_attempts WHERE scope_key = ?", (scope_key,))
    now = utcnow_iso()
    now_dt = parse_iso(now)
    if row:
        first_attempt = parse_iso(row.get("first_attempt_at"))
        expired_window = bool(first_attempt and now_dt and (now_dt - first_attempt).total_seconds() > settings.login_rate_limit_window_seconds)
        attempt_count = 1 if expired_window else int(row.get("attempt_count") or 0) + 1
        first_attempt_at = now if expired_window else (row.get("first_attempt_at") or now)
        blocked_until = add_minutes(now, 15) if attempt_count >= settings.login_rate_limit_max_attempts else None
        execute(
            conn,
            """
            UPDATE auth_login_attempts
            SET attempt_count = ?, first_attempt_at = ?, last_attempt_at = ?, blocked_until = ?, last_ip_address = ?, last_user_agent = ?
            WHERE scope_key = ?
            """,
            (attempt_count, first_attempt_at, now, blocked_until, ip_address, user_agent, scope_key),
        )
        return {"allowed": blocked_until is None, "remaining": max(0, settings.login_rate_limit_max_attempts - attempt_count), "blocked_until": blocked_until}
    execute(
        conn,
        """
        INSERT INTO auth_login_attempts
        (id, scope_key, attempt_count, first_attempt_at, last_attempt_at, blocked_until, last_ip_address, last_user_agent)
        VALUES (?, ?, 1, ?, ?, NULL, ?, ?)
        """,
        (new_id("lgna"), scope_key, now, now, ip_address, user_agent),
    )
    return {"allowed": True, "remaining": max(0, settings.login_rate_limit_max_attempts - 1)}


def list_auth_sessions(conn, *, user_id: str) -> list[dict[str, Any]]:
    rows = fetch_all(conn, "SELECT * FROM auth_sessions WHERE user_id = ? ORDER BY last_seen_at DESC, issued_at DESC", (user_id,))
    payload: list[dict[str, Any]] = []
    for row in rows:
        payload.append({
            **row,
            "is_active": row.get("status") == "active",
        })
    return payload


def revoke_other_auth_sessions(conn, *, user_id: str, current_session_id: str | None = None) -> int:
    rows = fetch_all(conn, "SELECT id, refresh_token_family_id FROM auth_sessions WHERE user_id = ? AND status = 'active' ORDER BY last_seen_at DESC, issued_at DESC", (user_id,))
    revoked = 0
    now = utcnow_iso()
    for row in rows:
        if current_session_id and row.get("id") == current_session_id:
            continue
        family_id = row.get("refresh_token_family_id")
        if family_id:
            _revoke_refresh_token_family(conn, family_id=family_id, revoked_at=now, reason="user_session_revoke")
        else:
            execute(conn, "UPDATE auth_sessions SET status = 'revoked', revoked_at = ?, last_seen_at = ? WHERE id = ?", (now, now, row["id"]))
        revoked += 1
    return revoked


def create_auth_session(conn, *, user: dict, ttl_minutes: int = 720, idle_timeout_minutes: int | None = None, max_sessions: int | None = None, ip_address: str | None = None, user_agent: str | None = None) -> dict[str, Any]:
    session_id = new_id("sess")
    family_id = new_id("sessfam")
    refresh_token = random_token("refresh")
    refresh_hash = hash_value(refresh_token)
    now = utcnow_iso()
    expires_at = add_minutes(now, ttl_minutes)
    max_idle_at = add_minutes(now, idle_timeout_minutes or settings.session_idle_timeout_minutes)
    execute(
        conn,
        """
        INSERT INTO auth_sessions
        (id, user_id, refresh_token_hash, refresh_token_family_id, status, issued_at, expires_at, max_idle_at, idle_timeout_minutes, last_authenticated_at, refresh_token_last_rotated_at, refresh_token_reuse_detected_at, revoked_at, last_seen_at, ip_address, user_agent)
        VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?)
        """,
        (session_id, user["id"], refresh_hash, family_id, now, expires_at, max_idle_at, idle_timeout_minutes or settings.session_idle_timeout_minutes, now, now, now, ip_address, user_agent),
    )
    execute(
        conn,
        """
        INSERT INTO auth_refresh_tokens
        (id, session_id, family_id, token_hash, previous_token_hash, status, issued_at, used_at, rotated_at, revoked_at, reuse_detected_at, replaced_by_token_hash)
        VALUES (?, ?, ?, ?, NULL, 'active', ?, NULL, NULL, NULL, NULL, NULL)
        """,
        (new_id("reftok"), session_id, family_id, refresh_hash, now),
    )
    session_limit = max_sessions or settings.max_sessions_per_user
    active_sessions = fetch_all(conn, "SELECT id, refresh_token_family_id FROM auth_sessions WHERE user_id = ? AND status = 'active' ORDER BY last_seen_at DESC, issued_at DESC", (user["id"],))
    for stale in active_sessions[session_limit:]:
        family_id = stale.get("refresh_token_family_id")
        if family_id:
            _revoke_refresh_token_family(conn, family_id=family_id, revoked_at=now, reason="session_limit")
        else:
            execute(conn, "UPDATE auth_sessions SET status = 'revoked', revoked_at = ?, last_seen_at = ? WHERE id = ?", (now, now, stale["id"]))
    row = fetch_one(conn, "SELECT * FROM auth_sessions WHERE id = ?", (session_id,))
    return {**row, "refresh_token": refresh_token}


def refresh_auth_session(conn, *, refresh_token: str, ttl_minutes: int = 720, idle_timeout_minutes: int | None = None) -> dict[str, Any] | None:
    token_hash = hash_value(refresh_token)
    token_row = fetch_one(conn, "SELECT * FROM auth_refresh_tokens WHERE token_hash = ?", (token_hash,))
    if not token_row:
        return None
    session = fetch_one(conn, "SELECT * FROM auth_sessions WHERE id = ?", (token_row["session_id"],))
    if not session:
        return None
    now = utcnow_iso()
    now_dt = parse_iso(now)
    if token_row.get("status") != "active":
        family_id = token_row.get("family_id") or session.get("refresh_token_family_id")
        if family_id:
            execute(conn, "UPDATE auth_refresh_tokens SET status = 'reused', reuse_detected_at = ? WHERE token_hash = ?", (now, token_hash))
            _revoke_refresh_token_family(conn, family_id=family_id, revoked_at=now, reason="refresh_token_reuse")
        return {**session, "reuse_detected": True}
    expires = parse_iso(session.get("expires_at"))
    idle_expires = parse_iso(session.get("max_idle_at"))
    if session.get("status") != "active" or not expires or (now_dt and expires <= now_dt) or (idle_expires and now_dt and idle_expires <= now_dt):
        execute(conn, "UPDATE auth_sessions SET status = 'expired', revoked_at = ?, last_seen_at = ? WHERE id = ?", (now, now, session["id"]))
        execute(conn, "UPDATE auth_refresh_tokens SET status = 'revoked', revoked_at = ? WHERE session_id = ? AND status = 'active'", (now, session["id"]))
        return None
    new_refresh = random_token("refresh")
    new_hash = hash_value(new_refresh)
    execute(
        conn,
        "UPDATE auth_refresh_tokens SET status = 'rotated', used_at = ?, rotated_at = ?, replaced_by_token_hash = ? WHERE id = ?",
        (now, now, new_hash, token_row["id"]),
    )
    execute(
        conn,
        """
        INSERT INTO auth_refresh_tokens
        (id, session_id, family_id, token_hash, previous_token_hash, status, issued_at, used_at, rotated_at, revoked_at, reuse_detected_at, replaced_by_token_hash)
        VALUES (?, ?, ?, ?, ?, 'active', ?, NULL, NULL, NULL, NULL, NULL)
        """,
        (new_id("reftok"), session["id"], token_row["family_id"], new_hash, token_hash, now),
    )
    session_idle_timeout = int(idle_timeout_minutes or session.get("idle_timeout_minutes") or settings.session_idle_timeout_minutes)
    execute(
        conn,
        "UPDATE auth_sessions SET refresh_token_hash = ?, expires_at = ?, max_idle_at = ?, idle_timeout_minutes = ?, last_seen_at = ?, refresh_token_last_rotated_at = ? WHERE id = ?",
        (new_hash, add_minutes(now, ttl_minutes), add_minutes(now, session_idle_timeout), session_idle_timeout, now, now, session["id"]),
    )
    updated = fetch_one(conn, "SELECT * FROM auth_sessions WHERE id = ?", (session["id"],))
    return {**updated, "refresh_token": new_refresh, "reuse_detected": False}


def revoke_auth_session(conn, *, refresh_token: str | None = None, session_id: str | None = None) -> dict[str, Any] | None:
    if refresh_token:
        token_row = fetch_one(conn, "SELECT * FROM auth_refresh_tokens WHERE token_hash = ?", (hash_value(refresh_token),))
        row = fetch_one(conn, "SELECT * FROM auth_sessions WHERE id = ?", (token_row["session_id"],)) if token_row else None
    elif session_id:
        row = fetch_one(conn, "SELECT * FROM auth_sessions WHERE id = ?", (session_id,))
    else:
        row = None
    if not row:
        return None
    now = utcnow_iso()
    family_id = row.get("refresh_token_family_id")
    if family_id:
        _revoke_refresh_token_family(conn, family_id=family_id, revoked_at=now, reason="session_revoke")
    else:
        execute(conn, "UPDATE auth_sessions SET status = 'revoked', revoked_at = ?, last_seen_at = ? WHERE id = ?", (now, now, row["id"]))
    return fetch_one(conn, "SELECT * FROM auth_sessions WHERE id = ?", (row["id"],))


def enroll_mfa_factor(conn, *, user_id: str) -> dict[str, Any]:
    existing = fetch_one(conn, "SELECT * FROM mfa_factors WHERE user_id = ?", (user_id,))
    secret = generate_totp_secret()
    now = utcnow_iso()
    recovery_codes = generate_recovery_codes()
    recovery_payload = [{"hash": hash_value(code), "used_at": None} for code in recovery_codes]
    secret_encrypted = encrypt_secret(secret, settings.secret_encryption_key)
    secret_masked = mask_secret(secret)
    if existing:
        execute(conn, "UPDATE mfa_factors SET secret = ?, secret_encrypted = ?, secret_masked = ?, recovery_codes_json = ?, status = 'pending', enrolled_at = ?, verified_at = NULL, revoked_at = NULL WHERE id = ?", (secret_masked, secret_encrypted, secret_masked, to_json(recovery_payload), now, existing["id"]))
        row = fetch_one(conn, "SELECT * FROM mfa_factors WHERE id = ?", (existing["id"],))
    else:
        factor_id = new_id("mfa")
        execute(conn, "INSERT INTO mfa_factors (id, user_id, factor_type, secret, secret_encrypted, secret_masked, recovery_codes_json, status, enrolled_at, verified_at, last_used_at, revoked_at, label) VALUES (?, ?, 'totp', ?, ?, ?, ?, 'pending', ?, NULL, NULL, NULL, 'Authenticator app')", (factor_id, user_id, secret_masked, secret_encrypted, secret_masked, to_json(recovery_payload), now))
        row = fetch_one(conn, "SELECT * FROM mfa_factors WHERE id = ?", (factor_id,))
    uri = provisioning_uri(secret, account_name=user_id, issuer='WAOS')
    return {**serialize_mfa_factor(row), "provisioning_uri": uri, "qr_svg_data_url": qr_svg_data_url(uri), "recovery_codes": recovery_codes}


def activate_mfa_factor(conn, *, user_id: str, code: str) -> dict[str, Any] | None:
    factor = fetch_one(conn, "SELECT * FROM mfa_factors WHERE user_id = ?", (user_id,))
    secret = _factor_secret(factor)
    if not factor or not secret:
        return None
    if not verify_totp(secret, code):
        return None
    now = utcnow_iso()
    execute(conn, "UPDATE mfa_factors SET status = 'active', verified_at = ?, last_used_at = ?, revoked_at = NULL WHERE id = ?", (now, now, factor["id"]))
    return serialize_mfa_factor(fetch_one(conn, "SELECT * FROM mfa_factors WHERE id = ?", (factor["id"],)))


def create_mfa_challenge(conn, *, user_id: str) -> dict[str, Any] | None:
    factor = fetch_one(conn, "SELECT * FROM mfa_factors WHERE user_id = ? AND status = 'active' AND revoked_at IS NULL", (user_id,))
    if not factor:
        return None
    challenge_id = new_id("mfachal")
    now = utcnow_iso()
    expires_at = add_minutes(now, 5)
    execute(conn, "INSERT INTO mfa_challenges (id, user_id, factor_id, status, expires_at, verified_at, created_at) VALUES (?, ?, ?, 'pending', ?, NULL, ?)", (challenge_id, user_id, factor["id"], expires_at, now))
    return {"id": challenge_id, "expires_at": expires_at, "factor_id": factor["id"]}


def verify_mfa_challenge(conn, *, user_id: str, challenge_id: str, code: str) -> bool:
    challenge = fetch_one(conn, "SELECT * FROM mfa_challenges WHERE id = ? AND user_id = ?", (challenge_id, user_id))
    factor = fetch_one(conn, "SELECT * FROM mfa_factors WHERE user_id = ? AND status = 'active' AND revoked_at IS NULL", (user_id,))
    secret = _factor_secret(factor)
    if not challenge or not factor or not secret or challenge["status"] != 'pending':
        return False
    expires = parse_iso(challenge.get("expires_at"))
    now = parse_iso(utcnow_iso())
    if not expires or (now and expires <= now):
        execute(conn, "UPDATE mfa_challenges SET status = 'expired' WHERE id = ?", (challenge_id,))
        return False
    verified = verify_totp(secret, code)
    if not verified:
        recovery_codes = from_json(factor.get('recovery_codes_json'), [])
        for item in recovery_codes:
            if item.get('used_at'):
                continue
            if hmac.compare_digest(item.get('hash', ''), hash_value(code)):
                item['used_at'] = utcnow_iso()
                execute(conn, "UPDATE mfa_factors SET recovery_codes_json = ? WHERE id = ?", (to_json(recovery_codes), factor['id']))
                verified = True
                break
    if not verified:
        return False
    ts = utcnow_iso()
    execute(conn, "UPDATE mfa_challenges SET status = 'verified', verified_at = ? WHERE id = ?", (ts, challenge_id))
    execute(conn, "UPDATE mfa_factors SET last_used_at = ? WHERE id = ?", (ts, factor["id"]))
    return True


def upsert_security_policy(conn, *, organization_id: str, updated_by: str, require_mfa: bool, require_sso: bool, session_ttl_minutes: int, session_idle_timeout_minutes: int, step_up_window_minutes: int, max_sessions_per_user: int, require_dual_approval_releases: bool, webhook_signature_required: bool, strict_idempotency: bool, ip_allowlist: list[str], allowed_origins: list[str]) -> dict[str, Any]:
    existing = fetch_one(conn, "SELECT * FROM organization_security_policies WHERE organization_id = ?", (organization_id,))
    now = utcnow_iso()
    payload = (
        int(require_mfa),
        int(require_sso),
        session_ttl_minutes,
        session_idle_timeout_minutes,
        step_up_window_minutes,
        max_sessions_per_user,
        int(require_dual_approval_releases),
        int(webhook_signature_required),
        int(strict_idempotency),
        to_json(ip_allowlist),
        to_json(allowed_origins),
        updated_by,
        now,
    )
    if existing:
        execute(conn, "UPDATE organization_security_policies SET require_mfa = ?, require_sso = ?, session_ttl_minutes = ?, session_idle_timeout_minutes = ?, step_up_window_minutes = ?, max_sessions_per_user = ?, require_dual_approval_releases = ?, webhook_signature_required = ?, strict_idempotency = ?, ip_allowlist_json = ?, allowed_origins_json = ?, updated_by = ?, updated_at = ? WHERE organization_id = ?", payload + (organization_id,))
        row = fetch_one(conn, "SELECT * FROM organization_security_policies WHERE organization_id = ?", (organization_id,))
    else:
        policy_id = new_id("secpol")
        execute(conn, "INSERT INTO organization_security_policies (id, organization_id, require_mfa, require_sso, session_ttl_minutes, session_idle_timeout_minutes, step_up_window_minutes, max_sessions_per_user, require_dual_approval_releases, webhook_signature_required, strict_idempotency, ip_allowlist_json, allowed_origins_json, updated_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (policy_id, organization_id) + payload + (now,))
        row = fetch_one(conn, "SELECT * FROM organization_security_policies WHERE organization_id = ?", (organization_id,))
    return {**row, "ip_allowlist": from_json(row.get("ip_allowlist_json"), []), "allowed_origins": from_json(row.get("allowed_origins_json"), [])}


def upsert_sso_provider(conn, *, organization_id: str, provider: str, issuer: str, client_id: str, status: str, scopes: list[str], metadata: dict[str, Any]) -> dict[str, Any]:
    existing = fetch_one(conn, "SELECT * FROM sso_providers WHERE organization_id = ? AND provider = ?", (organization_id, provider))
    now = utcnow_iso()
    if existing:
        execute(conn, "UPDATE sso_providers SET issuer = ?, client_id = ?, status = ?, scopes_json = ?, metadata_json = ?, updated_at = ? WHERE id = ?", (issuer, client_id, status, to_json(scopes), to_json(metadata), now, existing["id"]))
        row = fetch_one(conn, "SELECT * FROM sso_providers WHERE id = ?", (existing["id"],))
    else:
        provider_id = new_id("sso")
        execute(conn, "INSERT INTO sso_providers (id, organization_id, provider, issuer, client_id, status, scopes_json, metadata_json, last_test_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)", (provider_id, organization_id, provider, issuer, client_id, status, to_json(scopes), to_json(metadata), now, now))
        row = fetch_one(conn, "SELECT * FROM sso_providers WHERE id = ?", (provider_id,))
    return {**row, "scopes": from_json(row.get("scopes_json"), []), "metadata": from_json(row.get("metadata_json"), {})}


def list_sso_providers(conn, *, organization_id: str) -> list[dict[str, Any]]:
    rows = fetch_all(conn, "SELECT * FROM sso_providers WHERE organization_id = ? ORDER BY updated_at DESC", (organization_id,))
    return [{**row, "scopes": from_json(row.get("scopes_json"), []), "metadata": from_json(row.get("metadata_json"), {})} for row in rows]
