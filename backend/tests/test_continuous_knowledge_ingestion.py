from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ALLOW_SQLITE_FOR_TESTS", "true")

from backend.app.agent_runtime import build_grounded_context
from backend.app.db import SCHEMA_PATH, fetch_one
from backend.app.knowledge_runtime import search_governed_knowledge
from backend.app.live_knowledge_runtime import (
    list_knowledge_source_connections,
    run_knowledge_source_sync,
    upsert_knowledge_source_connection,
)
from backend.app.migrations import apply_migrations


def _conn():
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    conn = sqlite3.connect(tmp.name)
    conn.row_factory = sqlite3.Row
    conn.executescript(Path(SCHEMA_PATH).read_text())
    apply_migrations(conn)
    return conn, tmp.name


def test_continuous_source_sync_publishes_live_knowledge_and_traceability() -> None:
    conn, name = _conn()
    try:
        source = upsert_knowledge_source_connection(
            conn,
            organization_id="org_live",
            bot_id="bot_live",
            source_key="pricing-site",
            connector_key="url",
            label="Pricing page",
            source_uri="https://example.com/pricing",
            owner_user_id="user_owner",
            watch_mode="polling",
            publish_policy="auto_publish",
            validation_policy={"min_chars": 20},
            metadata={"owner_team": "ops"},
        )
        result = run_knowledge_source_sync(
            conn,
            source_connection_id=source["id"],
            trigger_kind="webhook",
            items=[
                {
                    "id": "price-april",
                    "title": "Lista de precios",
                    "content_text": "Consulta general $899 MXN. Promoción vigente esta semana.",
                    "updated_at": "2026-04-17T10:00:00Z",
                    "supports": ["pricing", "payment"],
                }
            ],
            full_refresh=True,
        )
        assert result["run"]["status"] in {"completed", "completed_with_warnings"}
        hits = search_governed_knowledge(
            conn,
            organization_id="org_live",
            bot_id="bot_live",
            query="precio consulta",
            intent="pricing",
            limit=3,
        )
        assert hits
        trace = hits[0]["traceability"]
        assert trace["source_connection_id"] == source["id"]
        assert trace["publication_state"] == "published"
        assert trace["owner_user_id"] == "user_owner"
        assert trace["source_updated_at"] == "2026-04-17T10:00:00Z"
    finally:
        conn.close()
        Path(name).unlink(missing_ok=True)


def test_full_refresh_versions_changed_item_and_invalidates_missing_publication() -> None:
    conn, name = _conn()
    try:
        source = upsert_knowledge_source_connection(
            conn,
            organization_id="org_live",
            bot_id="bot_live",
            source_key="ops-drive",
            connector_key="drive",
            label="Drive ops",
            owner_user_id="ops_owner",
            watch_mode="polling",
        )
        run_knowledge_source_sync(
            conn,
            source_connection_id=source["id"],
            items=[
                {"id": "hours", "title": "Horarios", "content_text": "Lunes a viernes de 9 a 18 horas.", "updated_at": "2026-04-17T09:00:00Z"},
                {"id": "faq", "title": "FAQ ingreso", "content_text": "Traer identificación oficial y llegar 10 minutos antes.", "updated_at": "2026-04-17T09:05:00Z"},
            ],
            full_refresh=True,
        )
        second = run_knowledge_source_sync(
            conn,
            source_connection_id=source["id"],
            items=[
                {"id": "hours", "title": "Horarios", "content_text": "Lunes a sábado de 9 a 19 horas.", "updated_at": "2026-04-18T09:00:00Z"},
            ],
            full_refresh=True,
        )
        assert second["run"]["items_invalidated"] == 1
        version_row = fetch_one(
            conn,
            "SELECT version_number FROM knowledge_document_versions WHERE document_id = (SELECT id FROM knowledge_documents WHERE source_key = ?) AND is_current = 1",
            (f"live.{source['id']}.hours",),
        )
        assert version_row == {"version_number": 2}
        invalidated = fetch_one(
            conn,
            "SELECT state FROM knowledge_source_publications WHERE source_connection_id = ? AND external_item_key = ?",
            (source["id"], "faq"),
        )
        assert invalidated == {"state": "invalidated"}
    finally:
        conn.close()
        Path(name).unlink(missing_ok=True)


def test_runtime_grounding_uses_live_published_source_without_manual_config() -> None:
    conn, name = _conn()
    try:
        source = upsert_knowledge_source_connection(
            conn,
            organization_id="org_live",
            bot_id="bot_live",
            source_key="form-faq",
            connector_key="form",
            label="Internal FAQ form",
            owner_user_id="cx_owner",
        )
        run_knowledge_source_sync(
            conn,
            source_connection_id=source["id"],
            items=[
                {
                    "id": "faq-1",
                    "title": "Ubicación",
                    "answers": {"pregunta": "¿Dónde están?", "respuesta": "Estamos en Reforma 100, piso 8."},
                    "updated_at": "2026-04-17T11:00:00Z",
                }
            ],
        )
        grounded = build_grounded_context(
            text="donde estan",
            memory={"current_intent": "location"},
            bot_config={"identity": {"business_name": "WAOS", "language": "es"}, "business_knowledge": {}},
            conn=conn,
            organization_id="org_live",
            bot_id="bot_live",
            contact_id="ct_live",
            conversation_id="conv_live",
        )
        assert grounded["coverage"]["governed_knowledge"] is True
        assert grounded["traceability"]
        assert grounded["traceability"][0]["source_connection_id"] == source["id"]
        sources = list_knowledge_source_connections(conn, organization_id="org_live", bot_id="bot_live")
        assert sources[0]["publication_counts"]["published"] >= 1
    finally:
        conn.close()
        Path(name).unlink(missing_ok=True)
