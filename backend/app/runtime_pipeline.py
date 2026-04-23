from __future__ import annotations

from typing import Any

from .ai_runtime.classification import call_openai_classification, heuristic_classify
from .ai_runtime.planning import decide_action
from .ai_runtime.runtime_generation import render_runtime_reply
from .ai_runtime.generation import generate_response
from .ai_runtime.runtime_planning import select_runtime_action
from .talent_runtime import detect_talent_intent


def understand_message(text: str, memory: dict[str, Any], bot_config: dict[str, Any], *, conn=None, organization_id: str | None = None, bot_id: str | None = None, conversation_id: str | None = None) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    talent = detect_talent_intent(text, memory, bot_config)
    if talent:
        attempts.append({"step": "talent", "used": True, "status": "ok"})
        return {"classification": {**talent, "_classifier_source": "talent", "_fallback_chain": ["talent"]}, "source": "talent", "fallback_chain": attempts}
    openai_result = call_openai_classification(conn, organization_id=organization_id, bot_id=bot_id, conversation_id=conversation_id, text=text, bot_config=bot_config, memory=memory)
    attempts.append({"step": "openai", "used": bool(openai_result), "status": "ok" if openai_result else "fallback"})
    if openai_result:
        return {"classification": {**openai_result, "_classifier_source": "openai", "_fallback_chain": ["openai"]}, "source": "openai", "fallback_chain": attempts}
    heuristic = heuristic_classify(text, memory, bot_config)
    return {"classification": {**heuristic, "_classifier_source": "heuristic", "_fallback_chain": ["openai", "heuristic"]}, "source": "heuristic", "fallback_chain": attempts + [{"step": "heuristic", "used": True, "status": "ok"}]}


def decide_runtime_action(*, conversation: dict[str, Any], bot: dict[str, Any], classification: dict[str, Any], memory: dict[str, Any], bot_config: dict[str, Any], execution_plan: dict[str, Any] | None = None) -> dict[str, Any]:
    if execution_plan is None:
        return decide_action(conversation=conversation, bot=bot, classification=classification, memory=memory, bot_config=bot_config)
    return select_runtime_action(conversation=conversation, bot=bot, classification=classification, memory=memory, bot_config=bot_config, execution_plan=execution_plan)


def generate_runtime_reply(text: str, classification: dict[str, Any], bot_config: dict[str, Any], memory: dict[str, Any], recent_messages: list[dict[str, Any]], *, conn=None, organization_id: str | None = None, bot_id: str | None = None, contact_id: str | None = None, conversation_id: str | None = None, recent_voice_notes: list[dict[str, Any]] | None = None, language_config: dict[str, Any] | None = None, execution_plan: dict[str, Any] | None = None, grounded_context: dict[str, Any] | None = None) -> dict[str, Any]:
    if execution_plan is None or grounded_context is None:
        response_text, payload = generate_response(text, classification, bot_config, memory, recent_messages, conn=conn, organization_id=organization_id, bot_id=bot_id, contact_id=contact_id, conversation_id=conversation_id, recent_voice_notes=recent_voice_notes, language_config=language_config)
        return {"text": response_text, "payload": payload, "source": payload.get("generator_source") or "heuristic", "fallback_chain": payload.get("generator_fallback_chain") or ["heuristic"]}
    return render_runtime_reply(text, classification, bot_config, memory, recent_messages, execution_plan=execution_plan, grounded_context=grounded_context, conn=conn, organization_id=organization_id, bot_id=bot_id, contact_id=contact_id, conversation_id=conversation_id, recent_voice_notes=recent_voice_notes, language_config=language_config)
