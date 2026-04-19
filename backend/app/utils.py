from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import json
from decimal import Decimal
import os
import secrets
import struct
import urllib.parse
import uuid
from io import BytesIO
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

try:
    import qrcode
    import qrcode.image.svg
except Exception:  # pragma: no cover
    qrcode = None


_PASSWORD_HASHER = PasswordHasher(
    time_cost=int(os.getenv("ARGON2_TIME_COST", "3")),
    memory_cost=int(os.getenv("ARGON2_MEMORY_COST", "65536")),
    parallelism=int(os.getenv("ARGON2_PARALLELISM", "4")),
)


class SecretDecryptionError(Exception):
    pass


class RetryableProviderError(Exception):
    def __init__(self, message: str, *, retryable: bool, status_code: int | None = None, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code
        self.details = details or {}


def utcnow() -> dt.datetime:
    fixed_now = os.getenv("WAOS_FIXED_NOW")
    if fixed_now:
        value = fixed_now.replace("Z", "+00:00")
        parsed = dt.datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    return dt.datetime.now(dt.timezone.utc)


def utcnow_iso() -> str:
    return utcnow().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    value = value.replace("Z", "+00:00")
    return dt.datetime.fromisoformat(value)


def add_minutes(value: str | None, minutes: int) -> str:
    base = parse_iso(value) or utcnow()
    return (base + dt.timedelta(minutes=minutes)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def add_seconds(value: str | None, seconds: int) -> str:
    base = parse_iso(value) or utcnow()
    return (base + dt.timedelta(seconds=seconds)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def next_day_iso(day: str) -> str:
    base = dt.datetime.fromisoformat(f"{day}T00:00:00+00:00")
    return (base + dt.timedelta(days=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def slugify(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or secrets.token_hex(4)


def _legacy_hash_password(password: str) -> str:
    salt = "waos-legacy-salt"
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    return _PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    if password_hash.startswith("$argon2"):
        try:
            return bool(_PASSWORD_HASHER.verify(password_hash, password))
        except VerifyMismatchError:
            return False
        except Exception:
            return False
    return hmac.compare_digest(_legacy_hash_password(password), password_hash)


def password_needs_rehash(password_hash: str) -> bool:
    if not password_hash or not password_hash.startswith("$argon2"):
        return True
    try:
            return _PASSWORD_HASHER.check_needs_rehash(password_hash)
    except Exception:
        return True


def _legacy_sign_payload(payload: dict[str, Any], secret: str) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")
    signature = hmac.new(secret.encode("utf-8"), encoded.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def _legacy_verify_signed_payload(token: str, secret: str) -> dict[str, Any] | None:
    try:
        encoded, signature = token.split(".", 1)
        expected = hmac.new(secret.encode("utf-8"), encoded.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        padded = encoded + "=" * ((4 - len(encoded) % 4) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("utf-8"))
        payload = json.loads(raw.decode("utf-8"))
        exp = payload.get("exp")
        if exp and utcnow().timestamp() > exp:
            return None
        return payload
    except Exception:
        return None


def sign_payload(payload: dict[str, Any], secret: str) -> str:
    claims = dict(payload)
    now = int(utcnow().timestamp())
    claims.setdefault("iat", now)
    claims.setdefault("nbf", now)
    claims.setdefault("jti", new_id("jwt"))
    return jwt.encode(claims, secret, algorithm="HS256")


def verify_signed_payload(token: str, secret: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], options={"require": ["exp", "iat"]})
        return dict(payload)
    except Exception:
        return _legacy_verify_signed_payload(token, secret)


def _json_default(value: Any):
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=_json_default)


def from_json(value: str | None, default: Any) -> Any:
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except Exception:
        return default



def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def random_token(prefix: str = "tok") -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def generate_totp_secret(length: int = 32) -> str:
    raw = secrets.token_bytes(length)
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def _totp_key(secret: str) -> bytes:
    padded = secret.upper() + "=" * ((8 - len(secret) % 8) % 8)
    return base64.b32decode(padded.encode("ascii"))


def current_mfa_code(secret: str, timestamp: int | None = None, step_seconds: int = 30, digits: int = 6) -> str:
    ts = int(timestamp or utcnow().timestamp())
    counter = ts // step_seconds
    key = _totp_key(secret)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    truncated = struct.unpack(">I", digest[offset: offset + 4])[0] & 0x7FFFFFFF
    code_int = truncated % (10 ** digits)
    return str(code_int).zfill(digits)


def verify_totp(secret: str, code: str, *, window: int = 1, timestamp: int | None = None, step_seconds: int = 30, digits: int = 6) -> bool:
    now = int(timestamp or utcnow().timestamp())
    for drift in range(-window, window + 1):
        expected = current_mfa_code(secret, timestamp=now + drift * step_seconds, step_seconds=step_seconds, digits=digits)
        if hmac.compare_digest(expected, code):
            return True
    return False


def provisioning_uri(secret: str, *, account_name: str, issuer: str = "WAOS") -> str:
    label = urllib.parse.quote(f"{issuer}:{account_name}")
    params = urllib.parse.urlencode({"secret": secret, "issuer": issuer, "algorithm": "SHA1", "digits": 6, "period": 30})
    return f"otpauth://totp/{label}?{params}"


def qr_svg_data_url(content: str) -> str | None:
    if not qrcode:
        return None
    image = qrcode.make(content, image_factory=qrcode.image.svg.SvgImage)
    buffer = BytesIO()
    image.save(buffer)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def generate_recovery_codes(count: int = 8) -> list[str]:
    return [f"{secrets.token_hex(3)}-{secrets.token_hex(3)}" for _ in range(count)]


def _derive_master_key(master_key: str) -> bytes:
    return hashlib.sha256(master_key.encode("utf-8")).digest()


def _fernet(master_key: str) -> Fernet:
    if not master_key:
        raise ValueError("missing_master_key")
    return Fernet(base64.urlsafe_b64encode(_derive_master_key(master_key)))


def _encrypt_secret_v1(secret_value: str, master_key: str) -> str:
    plaintext = secret_value.encode("utf-8")
    nonce = secrets.token_bytes(16)
    key = _derive_master_key(master_key)
    keystream = b""
    counter = 0
    while len(keystream) < len(plaintext):
        counter_bytes = struct.pack(">I", counter)
        keystream += hmac.new(key, nonce + counter_bytes, hashlib.sha256).digest()
        counter += 1
    ciphertext = bytes(a ^ b for a, b in zip(plaintext, keystream[: len(plaintext)]))
    mac = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    envelope = {
        "v": 1,
        "n": base64.b64encode(nonce).decode("ascii"),
        "c": base64.b64encode(ciphertext).decode("ascii"),
        "m": base64.b64encode(mac).decode("ascii"),
    }
    return base64.urlsafe_b64encode(json.dumps(envelope, separators=(",", ":")).encode("utf-8")).decode("ascii")


def encrypt_secret(secret_value: str, master_key: str) -> str:
    if not master_key:
        raise ValueError("missing_master_key")
    token = _fernet(master_key).encrypt(secret_value.encode("utf-8"))
    return token.decode("ascii")


def _decrypt_secret_v1(encrypted_value: str, master_key: str) -> str:
    envelope_raw = base64.urlsafe_b64decode(encrypted_value.encode("ascii"))
    envelope = json.loads(envelope_raw.decode("utf-8"))
    nonce = base64.b64decode(envelope["n"])
    ciphertext = base64.b64decode(envelope["c"])
    mac = base64.b64decode(envelope["m"])
    key = _derive_master_key(master_key)
    expected_mac = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected_mac):
        raise SecretDecryptionError("integrity_check_failed")
    keystream = b""
    counter = 0
    while len(keystream) < len(ciphertext):
        counter_bytes = struct.pack(">I", counter)
        keystream += hmac.new(key, nonce + counter_bytes, hashlib.sha256).digest()
        counter += 1
    plaintext = bytes(a ^ b for a, b in zip(ciphertext, keystream[: len(ciphertext)]))
    return plaintext.decode("utf-8")


def decrypt_secret(encrypted_value: str, master_key: str) -> str:
    if not encrypted_value:
        raise SecretDecryptionError("empty_secret")
    try:
        return _fernet(master_key).decrypt(encrypted_value.encode("ascii")).decode("utf-8")
    except InvalidToken:
        try:
            return _decrypt_secret_v1(encrypted_value, master_key)
        except SecretDecryptionError:
            raise
        except Exception as exc:  # pragma: no cover
            raise SecretDecryptionError(str(exc)) from exc
    except SecretDecryptionError:
        raise
    except Exception as exc:  # pragma: no cover
        raise SecretDecryptionError(str(exc)) from exc


def verify_hub_signature(raw_body: bytes, signature_header: str | None, app_secret: str) -> bool:
    if not signature_header or not app_secret:
        return False
    incoming = signature_header.removeprefix("sha256=")
    expected = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(incoming, expected)
