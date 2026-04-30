from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request

parser = argparse.ArgumentParser(description="Payment provider sandbox smoke: preview, execute and idempotent replay for create_payment_link.")
parser.add_argument("--required", action="store_true")
args = parser.parse_args()

required = [
    "WAOS_E2E_BASE_URL",
    "WAOS_E2E_EMAIL",
    "WAOS_E2E_PASSWORD",
    "WAOS_E2E_ORGANIZATION_ID",
    "WAOS_E2E_PAYMENT_BOT_ID",
    "WAOS_E2E_PAYMENT_CONVERSATION_ID",
    "WAOS_E2E_PAYMENT_CONTACT_ID",
    "STRIPE_SECRET_KEY",
]
missing = [name for name in required if not os.getenv(name)]
if missing:
    if args.required:
        raise SystemExit("payment sandbox smoke missing env: " + ",".join(missing))
    print("payment sandbox smoke skipped: " + ",".join(missing))
    raise SystemExit(0)
if not os.getenv("STRIPE_SECRET_KEY", "").startswith("sk_test_"):
    raise SystemExit("STRIPE_SECRET_KEY=sk_test_... is required for provider sandbox smoke")

base = os.environ["WAOS_E2E_BASE_URL"].rstrip("/")
if args.required and not base.startswith("https://"):
    raise SystemExit("WAOS_E2E_BASE_URL must be https:// for required payment sandbox smoke")


def request(path: str, *, method: str = "GET", token: str | None = None, body: dict | None = None, headers: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req_headers = {"Accept": "application/json", "User-Agent": "waos-payment-sandbox-smoke/1.0", **(headers or {})}
    if body is not None:
        req_headers["Content-Type"] = "application/json"
    if token:
        req_headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(base + path, data=data, method=method, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1200]
        raise SystemExit(f"{method} {path} failed with {exc.code}: {detail}") from exc

login = request("/api/v1/auth/login", method="POST", body={"email": os.environ["WAOS_E2E_EMAIL"], "password": os.environ["WAOS_E2E_PASSWORD"]})
token = login.get("access_token")
if not token:
    raise SystemExit("payment sandbox login did not return access_token")

suffix = str(int(time.time()))
client_request_id = f"payment-smoke-{suffix}"
payment_payload = {
    "organization_id": os.environ["WAOS_E2E_ORGANIZATION_ID"],
    "bot_id": os.environ["WAOS_E2E_PAYMENT_BOT_ID"],
    "action": "create_payment_link",
    "client_request_id": client_request_id,
    "payload": {
        "bot_id": os.environ["WAOS_E2E_PAYMENT_BOT_ID"],
        "conversation_id": os.environ["WAOS_E2E_PAYMENT_CONVERSATION_ID"],
        "contact_id": os.environ["WAOS_E2E_PAYMENT_CONTACT_ID"],
        "title": f"WAOS sandbox smoke {suffix}",
        "amount": float(os.getenv("WAOS_E2E_PAYMENT_AMOUNT", "10.00")),
        "currency": os.getenv("WAOS_E2E_PAYMENT_CURRENCY", "MXN"),
        "metadata": {"source": "payment_provider_sandbox_smoke"},
    },
    "metadata": {"correlation_id": client_request_id},
}
preview = request("/api/v1/tool-executions/preview", method="POST", token=token, body=payment_payload)
preview_data = preview.get("data") or preview
execution = preview_data.get("execution") or {}
preview_id = execution.get("id")
confirmation_token = preview_data.get("confirmation_token")
if not preview_id or not confirmation_token:
    raise SystemExit(f"payment sandbox preview missing confirmation: {preview}")
execute_payload = {**payment_payload, "confirm": True, "preview_execution_id": preview_id, "confirmation_token": confirmation_token}
first = request("/api/v1/tool-executions/execute", method="POST", token=token, body=execute_payload, headers={"Idempotency-Key": client_request_id})
second = request("/api/v1/tool-executions/execute", method="POST", token=token, body=execute_payload, headers={"Idempotency-Key": client_request_id})
first_data = first.get("data") or first
second_data = second.get("data") or second
if not (second_data.get("idempotent") or (second_data.get("execution") or {}).get("idempotent_replay_of_run_id")):
    raise SystemExit(f"payment sandbox second execution was not idempotent: {second}")
first_payment = (((first_data.get("result") or {}).get("payment")) or (first_data.get("payment") or {}))
if not (first_payment.get("id") or first_payment.get("external_payment_id") or first_payment.get("payment_link_url")):
    raise SystemExit(f"payment sandbox did not produce a payment artifact: {first}")
print("payment sandbox smoke ok")
