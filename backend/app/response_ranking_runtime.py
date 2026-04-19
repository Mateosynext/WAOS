from __future__ import annotations

import re
from typing import Any

_DEFAULT_CANDIDATE_COUNT = 4
_RESPONSE_RANKER_VERSION = "response_ranker_v1"


def build_response_candidate_specs(
    *,
    classification: dict[str, Any] | None = None,
    execution_plan: dict[str, Any] | None = None,
    specialist_route: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    classification = classification or {}
    execution_plan = execution_plan or {}
    specialist_route = specialist_route or {}
    intent = str(classification.get("intent") or "general").strip().lower()
    contract = execution_plan.get("response_contract") or {}
    requested = int(contract.get("candidate_count") or _DEFAULT_CANDIDATE_COUNT)
    requested = max(3, min(5, requested))
    specialist = str(specialist_route.get("specialist_agent_key") or "general").strip().lower()

    ordered: list[dict[str, Any]] = [
        {
            "variant_key": "balanced_default",
            "candidate_label": "Balanced default",
            "tone": "balanced",
            "cta_style": "soft",
            "length": "medium",
            "framing": "value_first",
        },
        {
            "variant_key": "concise_direct",
            "candidate_label": "Concise direct",
            "tone": "direct",
            "cta_style": "explicit",
            "length": "short",
            "framing": "action_first",
        },
        {
            "variant_key": "warm_reassuring",
            "candidate_label": "Warm reassuring",
            "tone": "warm",
            "cta_style": "soft",
            "length": "medium",
            "framing": "empathy_first",
        },
        {
            "variant_key": "conversion_push",
            "candidate_label": "Conversion push",
            "tone": "confident",
            "cta_style": "strong",
            "length": "short",
            "framing": "urgency_next_step",
        },
        {
            "variant_key": "consultative_clarity",
            "candidate_label": "Consultative clarity",
            "tone": "consultative",
            "cta_style": "guided",
            "length": "medium",
            "framing": "question_led",
        },
    ]

    if intent in {"support", "faq"} or specialist == "support":
        priority = ["warm_reassuring", "consultative_clarity", "balanced_default", "concise_direct", "conversion_push"]
    elif intent in {"payment", "pricing", "schedule"} or specialist in {"booking", "collections", "sales"}:
        priority = ["concise_direct", "conversion_push", "balanced_default", "warm_reassuring", "consultative_clarity"]
    else:
        priority = ["balanced_default", "concise_direct", "warm_reassuring", "consultative_clarity", "conversion_push"]

    by_key = {item["variant_key"]: item for item in ordered}
    ranked = [by_key[key] for key in priority if key in by_key]
    return ranked[:requested]


def infer_reply_language(text: str, response_text: str, default_language: str = "es") -> str:
    combined = f"{text} {response_text}".lower()
    english_markers = ["price", "book", "hours", "where", "help", "please", "payment"]
    spanish_markers = ["precio", "agendar", "horario", "donde", "ayuda", "por favor", "pago"]
    english_score = sum(1 for item in english_markers if item in combined)
    spanish_score = sum(1 for item in spanish_markers if item in combined)
    if english_score > spanish_score:
        return "en"
    if spanish_score > english_score:
        return "es"
    return (default_language or "es").lower()


def style_response_candidate(
    *,
    response_text: str,
    candidate_spec: dict[str, Any] | None,
    language: str,
    classification: dict[str, Any] | None = None,
    bot_config: dict[str, Any] | None = None,
    execution_plan: dict[str, Any] | None = None,
) -> str:
    text = str(response_text or "").strip()
    spec = candidate_spec or {}
    if not text:
        return text
    intent = str((classification or {}).get("intent") or "general").strip().lower()
    tone = str(spec.get("tone") or "balanced").strip().lower()
    framing = str(spec.get("framing") or "value_first").strip().lower()
    cta_style = str(spec.get("cta_style") or "soft").strip().lower()
    length = str(spec.get("length") or "medium").strip().lower()

    opener = _variant_opener(language, tone=tone, framing=framing, intent=intent)
    if opener and not text.lower().startswith(opener.lower()[:6]):
        text = f"{opener} {text}".strip()

    if length == "short":
        text = _shorten_text(text, language)
    elif length == "medium":
        text = _normalize_spacing(text)

    cta = _variant_cta(language, intent=intent, cta_style=cta_style, bot_config=bot_config or {}, execution_plan=execution_plan or {})
    if cta and _normalize_sentence(cta) not in _normalize_sentence(text):
        separator = " " if text.endswith((".", "?", "!")) else ". "
        text = f"{text}{separator}{cta}".strip()
    return _normalize_spacing(text)


def score_response_candidate(
    *,
    response_text: str,
    candidate_spec: dict[str, Any] | None,
    classification: dict[str, Any] | None,
    verification: dict[str, Any] | None,
    grounded_context: dict[str, Any] | None,
) -> dict[str, Any]:
    response_text = str(response_text or "").strip()
    classification = classification or {}
    verification = verification or {}
    grounded_context = grounded_context or {}
    candidate_spec = candidate_spec or {}
    intent = str(classification.get("intent") or "general").strip().lower()
    issues = [str(item) for item in (verification.get("issues") or [])]
    status = str(verification.get("status") or "unknown")
    words = [item for item in re.split(r"\s+", response_text) if item]
    word_count = len(words)
    question_marks = response_text.count("?") + response_text.count("¿")
    cta_markers = _cta_markers(intent)
    action_hits = sum(1 for marker in cta_markers if marker in response_text.lower())
    clarity = 0.58
    if 8 <= word_count <= 75:
        clarity += 0.18
    elif word_count < 8:
        clarity -= 0.16
    elif word_count > 120:
        clarity -= 0.14
    if question_marks:
        clarity += 0.08
    if response_text.endswith(("?", "!", ".")):
        clarity += 0.04

    quality = 0.55
    quality += 0.18 if status == "approved" else 0.05
    quality -= min(0.30, 0.09 * len(issues))
    if grounded_context.get("verifiable"):
        quality += 0.08
    if word_count > 120:
        quality -= 0.1

    risk = 0.92
    risk -= min(0.55, 0.16 * len(issues))
    if status == "rewritten":
        risk -= 0.08

    intent_alignment = 0.52
    if action_hits:
        intent_alignment += min(0.24, action_hits * 0.08)
    if intent in {"schedule", "payment", "pricing"} and candidate_spec.get("framing") in {"action_first", "urgency_next_step"}:
        intent_alignment += 0.14
    if intent in {"support", "faq"} and candidate_spec.get("tone") in {"warm", "consultative"}:
        intent_alignment += 0.14

    conversion = 0.46
    if action_hits:
        conversion += min(0.26, action_hits * 0.09)
    cta_style = str(candidate_spec.get("cta_style") or "soft")
    if intent in {"schedule", "payment", "pricing", "sales", "followup"}:
        if cta_style == "explicit":
            conversion += 0.16
        elif cta_style == "strong":
            conversion += 0.12
        elif cta_style == "guided":
            conversion += 0.08
    elif intent in {"support", "faq"}:
        if cta_style == "guided":
            conversion += 0.12
        elif cta_style == "soft":
            conversion += 0.08

    subscores = {
        "quality": round(_clamp01(quality), 4),
        "risk": round(_clamp01(risk), 4),
        "clarity": round(_clamp01(clarity), 4),
        "intent_alignment": round(_clamp01(intent_alignment), 4),
        "conversion": round(_clamp01(conversion), 4),
    }
    total = round(
        subscores["quality"] * 0.30
        + subscores["risk"] * 0.24
        + subscores["clarity"] * 0.18
        + subscores["intent_alignment"] * 0.12
        + subscores["conversion"] * 0.16,
        4,
    )
    return {
        "ranker_version": _RESPONSE_RANKER_VERSION,
        "score_total": total,
        "subscores": subscores,
        "features": {
            "word_count": word_count,
            "question_marks": question_marks,
            "action_hits": action_hits,
            "verification_status": status,
            "issues": issues,
        },
    }


def build_ranking_summary(candidates: list[dict[str, Any]], selected: dict[str, Any] | None) -> dict[str, Any]:
    top_score = float((selected or {}).get("score_total") or 0.0)
    runner_up = 0.0
    sorted_scores = sorted((float(item.get("score_total") or 0.0) for item in candidates), reverse=True)
    if len(sorted_scores) > 1:
        runner_up = sorted_scores[1]
    return {
        "ranker_version": _RESPONSE_RANKER_VERSION,
        "candidate_count": len(candidates),
        "selected_variant": (selected or {}).get("variant_key"),
        "selected_score": round(top_score, 4),
        "runner_up_score": round(runner_up, 4),
        "selection_margin": round(max(0.0, top_score - runner_up), 4),
    }


def _cta_markers(intent: str) -> list[str]:
    shared = ["quieres", "te ayudo", "next step", "would you like", "let's"]
    mapping = {
        "schedule": shared + ["agendo", "agendar", "aparto", "horario", "book", "slot"],
        "pricing": shared + ["cotizo", "precio", "quote", "presupuesto"],
        "payment": shared + ["pago", "cobro", "link", "payment", "complete"],
        "support": shared + ["reviso", "ayudo", "detalle", "solve", "check"],
        "faq": shared + ["explico", "detalle", "tell me"],
        "general": shared + ["seguimos", "advance"],
    }
    return mapping.get(intent, shared)


def _variant_opener(language: str, *, tone: str, framing: str, intent: str) -> str:
    if language == "en":
        if framing == "action_first":
            return "Let's move this forward."
        if framing == "empathy_first":
            return "Of course."
        if framing == "urgency_next_step":
            return "We can sort this out now."
        if tone == "consultative":
            return "Here is the clearest next step."
        return "Got it."
    if framing == "action_first":
        return "Vamos con el siguiente paso."
    if framing == "empathy_first":
        return "Claro, con gusto."
    if framing == "urgency_next_step":
        return "Lo podemos mover hoy mismo."
    if tone == "consultative":
        return "Te dejo la ruta más clara."
    return "Listo."


def _variant_cta(language: str, *, intent: str, cta_style: str, bot_config: dict[str, Any], execution_plan: dict[str, Any]) -> str:
    business = str((bot_config.get("identity") or {}).get("business_name") or "nuestro equipo").strip()
    if language == "en":
        if intent == "schedule":
            base = "Do you want me to book the slot that works best for you?"
        elif intent == "payment":
            base = "Do you want me to send the payment link so you can complete it now?"
        elif intent == "pricing":
            base = "Do you want me to leave the quote ready with the exact option that fits you?"
        elif intent == "support":
            base = "Can you tell me the key detail so I solve it without making you repeat yourself?"
        else:
            base = f"Do you want me to take the next step with {business}?"
    else:
        if intent == "schedule":
            base = "¿Quieres que te deje apartado el horario que mejor te quede?"
        elif intent == "payment":
            base = "¿Quieres que te mande el link de cobro para completarlo ahora?"
        elif intent == "pricing":
            base = "¿Quieres que te deje la cotización exacta según lo que buscas?"
        elif intent == "support":
            base = "¿Me compartes el detalle clave y te lo resuelvo sin hacerte repetir todo?"
        else:
            base = f"¿Quieres que te deje el siguiente paso listo con {business}?"
    if cta_style == "strong":
        return base.replace("¿Quieres que", "¿Te lo dejo") if language != "en" else base.replace("Do you want me to", "I can")
    if cta_style == "guided":
        return (
            "¿Qué te conviene más: hacerlo ahorita o dejarlo listo para hoy?"
            if language != "en"
            else "What works better for you: doing it now or leaving it ready for later today?"
        )
    if cta_style == "explicit":
        return base
    return (
        "Si te sirve, lo dejamos listo en este mismo chat."
        if language != "en"
        else "If that helps, we can leave it ready in this chat."
    )


def _shorten_text(text: str, language: str) -> str:
    parts = [part.strip() for part in re.split(r"(?<=[\.!?])\s+", text) if part.strip()]
    if len(parts) <= 2:
        return text.strip()
    shortened = " ".join(parts[:2]).strip()
    if not shortened.endswith((".", "?", "!")):
        shortened += "."
    return shortened


def _normalize_spacing(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _normalize_sentence(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


__all__ = [
    "build_response_candidate_specs",
    "build_ranking_summary",
    "infer_reply_language",
    "score_response_candidate",
    "style_response_candidate",
]
