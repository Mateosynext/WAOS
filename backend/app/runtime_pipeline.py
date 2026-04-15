from __future__ import annotations

from typing import Any


def understand_message(text: str, memory: dict[str, Any], bot_config: dict[str, Any]) -> dict[str, Any]:
    from .ai import call_openai_classification, heuristic_classify
    from .talent_runtime import detect_talent_intent

    attempts: list[dict[str, Any]] = []
    talent = detect_talent_intent(text, memory, bot_config)
    if talent:
        attempts.append({"step": "talent", "used": True, "status": "ok"})
        return {
            "classification": {**talent, "_classifier_source": "talent", "_fallback_chain": ["talent"]},
            "source": "talent",
            "fallback_chain": attempts,
        }
    openai_result = call_openai_classification(text, bot_config, memory)
    attempts.append({"step": "openai", "used": bool(openai_result), "status": "ok" if openai_result else "fallback"})
    if openai_result:
        return {
            "classification": {**openai_result, "_classifier_source": "openai", "_fallback_chain": ["openai"]},
            "source": "openai",
            "fallback_chain": attempts,
        }
    heuristic = heuristic_classify(text, memory, bot_config)
    return {
        "classification": {**heuristic, "_classifier_source": "heuristic", "_fallback_chain": ["openai", "heuristic"]},
        "source": "heuristic",
        "fallback_chain": attempts + [{"step": "heuristic", "used": True, "status": "ok"}],
    }


def decide_runtime_action(*, conversation: dict[str, Any], bot: dict[str, Any], classification: dict[str, Any], memory: dict[str, Any], bot_config: dict[str, Any]) -> dict[str, Any]:
    from .ai import decide_action

    return decide_action(conversation=conversation, bot=bot, classification=classification, memory=memory, bot_config=bot_config)


def generate_runtime_reply(
    text: str,
    classification: dict[str, Any],
    bot_config: dict[str, Any],
    memory: dict[str, Any],
    recent_messages: list[dict[str, Any]],
    *,
    recent_voice_notes: list[dict[str, Any]] | None = None,
    language_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from .ai import generate_response

    response_text, payload = generate_response(
        text,
        classification,
        bot_config,
        memory,
        recent_messages,
        recent_voice_notes=recent_voice_notes,
        language_config=language_config,
    )
    return {
        "text": response_text,
        "payload": payload,
        "source": payload.get("generator_source") or "heuristic",
        "fallback_chain": payload.get("generator_fallback_chain") or ["heuristic"],
    }
