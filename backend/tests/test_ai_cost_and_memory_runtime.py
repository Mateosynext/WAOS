from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.ai import generate_response
from backend.app.db import execute, get_connection, init_db
from backend.app.main import app
from backend.app.runtime_settings import write_global_settings
from backend.app.utils import to_json
from backend.app.world_class import (
    append_memory_episode,
    ensure_world_class_schema,
    index_bot_knowledge,
    record_ai_usage,
    search_knowledge_embeddings_cached,
)
from backend.tests.test_activation_foundations import _auth_headers


client = TestClient(app)


def test_ai_dashboard_includes_cache_memory_and_profiles() -> None:
    headers = _auth_headers()
    init_db()
    write_global_settings(
        {
            "global_policy": "balanced",
            "default_model": "gpt-4o-mini",
            "freeze_minutes_after_takeover": 30,
            "ai_optimization": {
                "semantic_cache_similarity_generation": 0.95,
                "knowledge_search_cache_ttl_seconds": 7200,
            },
            "memory_runtime": {
                "episodic_memory_enabled": True,
                "cross_bot_intelligence_enabled": True,
            },
        }
    )
    with get_connection() as conn:
        ensure_world_class_schema(conn)
        record_ai_usage(
            conn,
            organization_id="org_activation",
            bot_id="bot_activation",
            conversation_id="conv_activation",
            model="gpt-4o-mini",
            operation="generation",
            prompt_tokens=80,
            completion_tokens=24,
            latency_ms=210,
            cache_hit=True,
            metadata={"source": "test"},
        )
        append_memory_episode(
            conn,
            organization_id="org_activation",
            contact_id="ct_activation",
            bot_id=None,
            conversation_id="conv_activation",
            source_message_id="msg_activation",
            episode_type="faq",
            summary_text="Cliente preguntó por duración del tratamiento y mostró intención alta.",
            metadata={"cross_bot": True, "bot_scope": "cross_bot"},
            score=88,
        )
        execute(
            conn,
            "UPDATE bots SET config_draft_json = ? WHERE id = ?",
            (
                to_json(
                    {
                        "identity": {"language": "es"},
                        "business_knowledge": {
                            "faqs": [{"q": "¿Cuánto dura el tratamiento?", "a": "Dura entre 45 y 60 minutos."}],
                            "hours": "Lun a Vie 9am a 6pm",
                        },
                    }
                ),
                "bot_activation",
            ),
        )
        index_bot_knowledge(
            conn,
            organization_id="org_activation",
            bot_id="bot_activation",
            bot_config={
                "business_knowledge": {
                    "faqs": [{"q": "¿Cuánto dura el tratamiento?", "a": "Dura entre 45 y 60 minutos."}],
                    "hours": "Lun a Vie 9am a 6pm",
                }
            },
        )
        first = search_knowledge_embeddings_cached(
            conn,
            organization_id="org_activation",
            bot_id="bot_activation",
            query="duración tratamiento",
            limit=3,
            ttl_seconds=7200,
        )
        assert first
        second = search_knowledge_embeddings_cached(
            conn,
            organization_id="org_activation",
            bot_id="bot_activation",
            query="duración tratamiento",
            limit=3,
            ttl_seconds=7200,
        )
        assert second[0]["cache_hit"] is True
        conn.commit()

    response = client.get(
        "/api/v1/ai/dashboard",
        params={"organization_id": "org_activation", "bot_id": "bot_activation"},
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["cache"]["totals"]["entries"] >= 1
    assert payload["memory_runtime"]["totals"]["episodes"] >= 1
    assert payload["optimization_profile"]["knowledge_search_cache_ttl_seconds"] == 7200
    assert payload["memory_profile"]["episodic_memory_enabled"] is True


def test_generate_response_can_shortcut_to_instant_knowledge() -> None:
    init_db()
    with get_connection() as conn:
        ensure_world_class_schema(conn)
        bot_config = {
            "identity": {"language": "es"},
            "business_knowledge": {
                "faqs": [{"q": "¿cuánto dura un blanqueamiento?", "a": "El blanqueamiento dura entre 45 y 60 minutos."}],
                "hours": "Lun a Vie 9am a 6pm",
                "location": "Av. Reforma 123",
            },
        }
        index_bot_knowledge(conn, organization_id="org_activation", bot_id="bot_activation", bot_config=bot_config)
        append_memory_episode(
            conn,
            organization_id="org_activation",
            contact_id="ct_activation",
            bot_id=None,
            conversation_id="conv_activation",
            source_message_id="msg_activation",
            episode_type="preference",
            summary_text="Hace 3 días pidió información sobre blanqueamiento y horarios de tarde.",
            metadata={"cross_bot": True, "bot_scope": "cross_bot"},
            score=91,
        )
        memory = {
            "lead_stage": "qualified",
            "lead_score": 70,
            "_contact_id": "ct_activation",
        }
        response_text, payload = generate_response(
            "¿cuánto dura un blanqueamiento?",
            {"intent": "faq", "lead_stage": "qualified"},
            bot_config,
            memory,
            recent_messages=[{"direction": "inbound", "body": "Hola"}],
            conn=conn,
            organization_id="org_activation",
            bot_id="bot_activation",
            contact_id="ct_activation",
            conversation_id="conv_activation",
        )
        assert "45 y 60 minutos" in response_text
        assert payload["generator_source"] == "instant_knowledge"
        assert payload["episodic_memory"]


def test_ai_stream_preview_endpoint_returns_sse_events() -> None:
    headers = _auth_headers()
    init_db()
    with get_connection() as conn:
        ensure_world_class_schema(conn)
        execute(
            conn,
            "UPDATE bots SET config_draft_json = ? WHERE id = ?",
            (
                to_json(
                    {
                        "identity": {"language": "es"},
                        "business_knowledge": {
                            "hours": "Lun a Vie 9am a 6pm",
                            "location": "Av. Reforma 123",
                        },
                    }
                ),
                "bot_activation",
            ),
        )
        conn.commit()

    response = client.get(
        "/api/v1/conversations/conv_activation/ai/stream-preview",
        params={"message": "¿Cuál es su horario?"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: meta" in response.text
    assert "event: chunk" in response.text
    assert "event: done" in response.text
