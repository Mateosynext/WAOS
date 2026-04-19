from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app


def test_public_legal_docs_endpoint_returns_catalog() -> None:
    with TestClient(app) as client:
        response = client.get('/api/public/legal/docs')
    assert response.status_code == 200
    payload = response.json()['data']
    assert payload['owner'] == 'Josue Mendoza Mateo'
    assert payload['count'] >= 20
    assert any(item['slug'] == 'cookies-tracking' for item in payload['documents'])


def test_public_legal_doc_slug_returns_content() -> None:
    with TestClient(app) as client:
        response = client.get('/api/public/legal/docs/cookies-tracking')
    assert response.status_code == 200
    payload = response.json()['data']
    assert payload['slug'] == 'cookies-tracking'
    assert 'Cookies' in payload['title']
    assert 'WAOS' in payload['content']


def test_cookie_consent_and_privacy_request_are_persisted() -> None:
    with TestClient(app) as client:
        consent = client.post(
            '/api/public/legal/consents/cookies',
            json={
                'anonymous_id': 'visitor-test',
                'consent_version': '1.0.0',
                'source': 'cookie_banner',
                'categories': {'necessary': True, 'analytics': True, 'preferences': False, 'marketing': False},
            },
        )
        privacy = client.post(
            '/api/public/legal/privacy-requests',
            json={
                'request_type': 'access',
                'name': 'Persona Prueba',
                'email': 'persona@example.com',
                'message': 'Quiero exportación de mis datos.',
            },
        )
    assert consent.status_code == 200
    assert consent.json()['data']['consent_key'] == 'cookies'
    assert privacy.status_code == 200
    assert privacy.json()['data']['status'] == 'received'
