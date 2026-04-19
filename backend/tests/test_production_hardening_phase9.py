from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.tests.test_activation_foundations import _auth_headers

client = TestClient(app)


def test_livez_and_deploy_checklist_exist() -> None:
    live = client.get('/livez')
    assert live.status_code == 200
    assert live.json()['status'] == 'ok'

    headers = _auth_headers()
    checklist = client.get('/api/v1/system/deploy-checklist', headers=headers)
    assert checklist.status_code == 200
    payload = checklist.json()
    assert payload['status'] in {'ok', 'degraded', 'error'}
    keys = {item['key'] for item in payload['items']}
    assert 'database_url' in keys
    assert 'api_host_allowed' in keys
    assert 'public_app_url_in_cors' in keys
