from __future__ import annotations

import argparse
import json
import os
import ssl
import urllib.error
import urllib.request

parser = argparse.ArgumentParser(description="Post-deploy smoke that validates public liveness/readiness endpoints against the deployed API.")
parser.add_argument("--required", action="store_true")
parser.add_argument("--local", action="store_true", help="Kept for backward compatibility; does not downgrade failures when --required is set.")
args = parser.parse_args()

base = os.getenv("WAOS_E2E_BASE_URL", "").rstrip("/")
if not base:
    if args.required:
        raise SystemExit("WAOS_E2E_BASE_URL is required for release smoke")
    print("post deploy smoke skipped: WAOS_E2E_BASE_URL missing")
    raise SystemExit(0)

if args.required and not (base.startswith("https://") or args.local):
    raise SystemExit("WAOS_E2E_BASE_URL must be https:// for required production smoke")

context = ssl.create_default_context()


def get(path: str) -> tuple[int, dict]:
    request = urllib.request.Request(base + path, headers={"Accept": "application/json", "User-Agent": "waos-post-deploy-smoke/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=20, context=context) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(text) if text else {}
            except json.JSONDecodeError:
                payload = {"raw": text[:500]}
            return int(resp.status), payload
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"{path} failed with {exc.code}: {detail}") from exc
    except Exception as exc:  # pragma: no cover - network failure path
        raise SystemExit(f"{path} failed: {exc}") from exc

for path in ["/livez", "/readyz"]:
    status, payload = get(path)
    if status >= 400:
        raise SystemExit(f"{path} failed with {status}: {payload}")
    if path == "/readyz" and args.required:
        ready = payload.get("ready", payload.get("ok", True))
        if ready is False:
            raise SystemExit(f"/readyz returned not ready: {payload}")

print("post deploy smoke ok")
