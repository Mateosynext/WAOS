from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_livez_survives_when_trace_db_is_unavailable(monkeypatch) -> None:
    def broken_connection():
        raise RuntimeError("db down")

    monkeypatch.setattr("backend.app.main.get_connection", broken_connection)
    response = client.get("/livez")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_vertical_catalog_is_public_and_db_independent(monkeypatch) -> None:
    def broken_connection():
        raise RuntimeError("db down")

    monkeypatch.setattr("backend.app.main.get_connection", broken_connection)
    response = client.get("/api/v1/verticals")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) >= 5


def test_vertical_profile_requires_auth_only_for_scoped_lookups() -> None:
    response = client.get("/api/v1/verticals/profile", params={"vertical": "fitness"})
    assert response.status_code == 200
    assert response.json()["id"] == "fitness"

    scoped = client.get("/api/v1/verticals/profile", params={"organization_id": "org_test"})
    assert scoped.status_code == 401


def test_public_vertical_routes_exist() -> None:
    response = client.get("/api/public/verticals", params={"top_only": 1})
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    detail = client.get("/api/public/verticals/subvertical-profile", params={"vertical": "fitness", "subvertical": "pilates"})
    assert detail.status_code == 200
    assert detail.json()["subvertical_profile"]["name"] == "pilates"
