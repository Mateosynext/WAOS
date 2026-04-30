from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request

parser = argparse.ArgumentParser(description="Critical production E2E smoke: login, /me, bot creation workflow and read-back.")
parser.add_argument("--required", action="store_true")
args = parser.parse_args()

required = [
    "WAOS_E2E_BASE_URL",
    "WAOS_E2E_EMAIL",
    "WAOS_E2E_PASSWORD",
    "WAOS_E2E_ORGANIZATION_ID",
    "WAOS_E2E_WHATSAPP_SANDBOX_PHONE",
]
missing = [name for name in required if not os.getenv(name)]
if missing:
    if args.required:
        raise SystemExit("critical E2E missing env: " + ",".join(missing))
    print("critical E2E skipped: " + ",".join(missing))
    raise SystemExit(0)

base = os.environ["WAOS_E2E_BASE_URL"].rstrip("/")
if args.required and not base.startswith("https://"):
    raise SystemExit("WAOS_E2E_BASE_URL must be https:// for required critical E2E")


def request(path: str, *, method: str = "GET", token: str | None = None, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Accept": "application/json", "User-Agent": "waos-critical-e2e-smoke/1.0"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise SystemExit(f"{method} {path} failed with {exc.code}: {detail}") from exc

login = request("/api/v1/auth/login", method="POST", body={"email": os.environ["WAOS_E2E_EMAIL"], "password": os.environ["WAOS_E2E_PASSWORD"]})
token = login.get("access_token")
if not token:
    raise SystemExit("critical E2E login did not return access_token")
request("/api/v1/auth/me", token=token)

suffix = str(int(time.time()))
payload = {
    "organization_id": os.environ["WAOS_E2E_ORGANIZATION_ID"],
    "business_name": f"WAOS Critical E2E {suffix}",
    "vertical": "servicios",
    "subvertical": "qa-production-smoke",
    "bot_name": f"Bot Critical E2E {suffix}",
    "primary_objective": "agendar",
    "tone": "amable",
    "language": "es",
    "timezone": "America/Mexico_City",
    "services": ["smoke test"],
    "hours": "Lunes a viernes 09:00-18:00",
    "faqs": [{"q": "¿Esto es un smoke test?", "a": "Sí."}],
    "whatsapp_number": os.environ["WAOS_E2E_WHATSAPP_SANDBOX_PHONE"],
    "publish_now": False,
    "client_request_id": f"critical-e2e-{suffix}",
}
created = request("/api/v1/bots/creation-workflows", method="POST", token=token, body=payload)
bot = created.get("bot") if isinstance(created.get("bot"), dict) else {}
workflow = created.get("workflow") if isinstance(created.get("workflow"), dict) else {}
bot_id = created.get("bot_id") or created.get("id") or bot.get("id")
if not bot_id:
    raise SystemExit(f"critical E2E bot creation did not return bot_id: {created}")
status = str(created.get("workflow_status") or workflow.get("status") or "ready")
if status not in {"ready", "completed", "done"}:
    raise SystemExit(f"critical E2E workflow not ready: {status}")
read_back = request(f"/api/v1/bots/{bot_id}", token=token)
if str(read_back.get("id") or (read_back.get("bot") or {}).get("id")) != str(bot_id):
    raise SystemExit("critical E2E created bot could not be read back")
print("critical E2E ok")
