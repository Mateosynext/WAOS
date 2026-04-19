from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ALLOW_SQLITE_FOR_TESTS", "true")

from backend.app.agent_runtime import build_grounded_context, verify_runtime_reply, plan_runtime_execution
from backend.app.db import SCHEMA_PATH, fetch_one
from backend.app.knowledge_runtime import ingest_knowledge_document, search_governed_knowledge, sync_config_knowledge
from backend.app.migrations import apply_migrations


def _conn():
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    conn = sqlite3.connect(tmp.name)
    conn.row_factory = sqlite3.Row
    conn.executescript(Path(SCHEMA_PATH).read_text())
    apply_migrations(conn)
    return conn, tmp.name


def test_governed_knowledge_versioning_and_traceable_search() -> None:
    conn, name = _conn()
    try:
        first = ingest_knowledge_document(
            conn,
            organization_id="org_1",
            bot_id="bot_1",
            title="Refund policy",
            source_kind="policy",
            source_key="legal.refund-policy",
            content_text="Refunds are processed within 5 business days.",
            domain="legal",
            source_uri="https://example.com/refunds",
            freshness_window_days=14,
            supports=["payment", "support"],
        )
        second = ingest_knowledge_document(
            conn,
            organization_id="org_1",
            bot_id="bot_1",
            title="Refund policy",
            source_kind="policy",
            source_key="legal.refund-policy",
            content_text="Refunds are processed within 3 business days.",
            domain="legal",
            source_uri="https://example.com/refunds",
            freshness_window_days=14,
            supports=["payment", "support"],
        )
        assert first["version"]["version_number"] == 1
        assert second["version"]["version_number"] == 2

        hits = search_governed_knowledge(
            conn,
            organization_id="org_1",
            bot_id="bot_1",
            query="How long do refunds take?",
            intent="payment",
            limit=3,
        )
        assert hits
        assert hits[0]["traceability"]["source_kind"] == "policy"
        assert hits[0]["traceability"]["version_number"] == 2
        assert hits[0]["freshness_status"] in {"fresh", "aging"}
    finally:
        conn.close()
        Path(name).unlink(missing_ok=True)



def test_sync_config_knowledge_invalidates_removed_catalog_entries() -> None:
    conn, name = _conn()
    try:
        first = sync_config_knowledge(
            conn,
            organization_id="org_1",
            bot_id="bot_1",
            bot_config={
                "business_knowledge": {
                    "prices": [{"name": "Consulta", "price": "$700 MXN"}],
                    "hours": "Lunes a viernes de 9 a 18",
                }
            },
        )
        assert "config.price.0" in first["active_source_keys"]

        second = sync_config_knowledge(
            conn,
            organization_id="org_1",
            bot_id="bot_1",
            bot_config={"business_knowledge": {"hours": "Lunes a viernes de 9 a 18"}},
        )
        assert "config.price.0" in second["invalidated_source_keys"]
        row = fetch_one(
            conn,
            "SELECT status, invalidated_reason FROM knowledge_documents WHERE organization_id = ? AND bot_id = ? AND source_key = ?",
            ("org_1", "bot_1", "config.price.0"),
        )
        assert row == {"status": "invalidated", "invalidated_reason": "config_removed_or_changed"}
    finally:
        conn.close()
        Path(name).unlink(missing_ok=True)



def test_grounded_context_exposes_governed_traceability_and_fresh_support() -> None:
    conn, name = _conn()
    try:
        sync_config_knowledge(
            conn,
            organization_id="org_1",
            bot_id="bot_1",
            bot_config={
                "business_knowledge": {
                    "prices": [{"name": "Consulta", "price": "$799 MXN"}],
                    "faqs": [{"q": "¿Dónde están?", "a": "En Reforma 100"}],
                },
                "identity": {"business_name": "WAOS Clinic", "language": "es"},
            },
        )
        grounded = build_grounded_context(
            text="Quiero saber el precio",
            memory={"current_intent": "pricing"},
            bot_config={
                "identity": {"business_name": "WAOS Clinic", "language": "es"},
                "business_knowledge": {"prices": [{"name": "Consulta", "price": "$799 MXN"}]},
            },
            conn=conn,
            organization_id="org_1",
            bot_id="bot_1",
            contact_id="ct_1",
            conversation_id="conv_1",
        )
        assert grounded["coverage"]["governed_knowledge"] is True
        assert grounded["support_status"]["pricing"] == "fresh"
        assert grounded["traceability"]
        assert grounded["traceability"][0]["source_key"].startswith("config.")
    finally:
        conn.close()
        Path(name).unlink(missing_ok=True)



def test_verifier_rewrites_pricing_when_only_governed_source_is_stale() -> None:
    conn, name = _conn()
    try:
        sync_config_knowledge(
            conn,
            organization_id="org_1",
            bot_id="bot_1",
            bot_config={
                "identity": {"business_name": "WAOS Clinic", "language": "es"},
                "business_knowledge": {"prices": [{"name": "Consulta", "price": "$799 MXN"}]},
            },
        )
        conn.execute(
            "UPDATE knowledge_document_versions SET freshness_status = 'stale' WHERE organization_id = ? AND bot_id = ? AND is_current = 1",
            ("org_1", "bot_1"),
        )
        grounded = build_grounded_context(
            text="precio",
            memory={"current_intent": "pricing"},
            bot_config={"identity": {"business_name": "WAOS Clinic", "language": "es"}, "business_knowledge": {}},
            conn=conn,
            organization_id="org_1",
            bot_id="bot_1",
            contact_id="ct_1",
            conversation_id="conv_1",
        )
        plan = plan_runtime_execution(
            text="precio",
            conversation={"human_takeover": 0},
            bot={"status": "active"},
            classification={"intent": "pricing", "requested_human": False, "urgency_score": 10},
            memory={"current_intent": "pricing"},
            bot_config={"identity": {"business_name": "WAOS Clinic", "language": "es"}, "business_knowledge": {}},
            grounded_context=grounded,
        )
        verification = verify_runtime_reply(
            text="precio",
            response_text="Sí, el precio es $799 MXN.",
            classification={"intent": "pricing"},
            grounded_context=grounded,
            bot_config={"identity": {"business_name": "WAOS Clinic", "language": "es"}},
            execution_plan=plan,
        )
        assert grounded["support_status"]["pricing"] == "stale"
        assert verification["status"] == "rewritten"
        assert "invent" in verification["response_text"].lower() or "confirm" in verification["response_text"].lower()
    finally:
        conn.close()
        Path(name).unlink(missing_ok=True)
