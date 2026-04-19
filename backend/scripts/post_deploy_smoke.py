from __future__ import annotations
import json, os, sys
from urllib import request, error
BASE_URL = os.getenv("BASE_URL", "").rstrip("/")
SMOKE_EMAIL = os.getenv("SMOKE_EMAIL", "")
SMOKE_PASSWORD = os.getenv("SMOKE_PASSWORD", "")
def fetch_json(url: str, method: str = "GET", payload: dict | None = None, headers: dict[str, str] | None = None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items(): req.add_header(key, value)
    with request.urlopen(req, timeout=20) as resp: return resp.getcode(), json.loads(resp.read().decode("utf-8"))
def main() -> None:
    if not BASE_URL: raise SystemExit("BASE_URL is required")
    code, live = fetch_json(f"{BASE_URL}/livez"); assert code == 200 and live.get("status") == "ok", live
    code, health = fetch_json(f"{BASE_URL}/healthz"); assert code == 200 and health.get("status") in {"ok", "degraded"}, health
    code, ready = fetch_json(f"{BASE_URL}/readyz"); assert code in {200, 503}, ready
    code, checklist = fetch_json(f"{BASE_URL}/api/v1/system/deploy-checklist"); assert code == 200 and checklist.get("status") in {"ok", "degraded", "error"}, checklist
    result = {"livez": live, "healthz": health, "readyz": ready, "deploy_checklist": checklist}
    if SMOKE_EMAIL and SMOKE_PASSWORD:
        code, login = fetch_json(f"{BASE_URL}/api/v1/auth/login", method="POST", payload={"email": SMOKE_EMAIL, "password": SMOKE_PASSWORD})
        assert code == 200, login
        token = login.get("access_token"); assert token, login
        code, matrix = fetch_json(f"{BASE_URL}/api/v1/access/matrix", headers={"Authorization": f"Bearer {token}"})
        assert code == 200, matrix
        result["access_matrix"] = {"current_user_role": matrix.get("current_user_role")}
    print(json.dumps({"ok": True, **result}, indent=2, ensure_ascii=False))
if __name__ == "__main__":
    try: main()
    except error.HTTPError as exc:
        print(exc.read().decode("utf-8"), file=sys.stderr)
        raise
