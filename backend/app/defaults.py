from __future__ import annotations

from copy import deepcopy
from typing import Any

from .config import settings
from .verticals import build_vertical_bot_setup
from .talent_runtime import default_talent_config


def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def default_bot_config(*, business_name: str, vertical: str, bot_name: str, primary_objective: str, tone: str, language: str, timezone: str | None = None, services: list[str] | None = None, hours: str = "", faqs: list[dict] | None = None, whatsapp_number: str = "") -> dict:
    resolved_timezone = timezone or settings.default_timezone
    vertical_setup = build_vertical_bot_setup(vertical, business_name=business_name, bot_name=bot_name, tone=tone, language=language, timezone=resolved_timezone, primary_objective=primary_objective, services=services, faqs=faqs, hours=hours, whatsapp_number=whatsapp_number)
    profile = vertical_setup["profile"]
    base_config = {
        "identity": {"bot_name": bot_name, "business_name": business_name, "vertical": profile["id"], "vertical_label": profile["short_name"], "language": language, "timezone": resolved_timezone},
        "personality": {"formality": "semi-formal", "tone": tone, "response_length": "short", "use_emojis": False, "sales_intensity": "medium", "humor_policy": "light_contextual", "strange_question_policy": "respond_validate_reframe_sell_move", "tone_of_voice_understanding": True, "tone_adaptation": "mirror_lightly_keep_brand", "native_voice_by_language": True, "tone_matrix_by_language": True},
        "objective": {"primary": primary_objective, "secondary": ["responder_faq", "calificar", "reactivar"]},
        "business_knowledge": {"services": services or [], "products": [], "prices": [], "faqs": faqs or [], "policies": [], "hours": hours, "location": "", "promotions": []},
        "rules": {"can_say": ["servicios", "horarios", "precio si existe configurado", "agendar", "humor ligero si ayuda", "reencuadrar preguntas raras al negocio"], "cannot_say": ["datos no configurados", "promesas contractuales", "diagnosticos profesionales"], "escalate_when": ["cliente molesto", "pide humano", "tema sensible"], "objection_handling": ["precio", "tiempo", "confianza"], "conversation_guards": ["nunca quedarse seco", "validar y luego reencauzar", "cerrar con siguiente paso"], "do_not_reply_when": ["human_takeover", "paused", "blocked"], "followup_limits": {"max_attempts": 2, "quiet_hours": "21:00-08:00"}},
        "agenda": {"availability": [hours] if hours else [], "appointment_duration_minutes": 30, "buffer_minutes": 15, "confirmation_rules": "confirmar 24h antes", "reschedule_rules": "permitir una reprogramacion"},
        "followups": {"rules": [{"type": "no_response", "delay_minutes": 120, "max_attempts": 2, "message_template": "Solo dando seguimiento a tu consulta. ¿Te gustaria que te ayude a avanzar?"}, {"type": "post_quote", "delay_minutes": 1440, "max_attempts": 2, "message_template": "Te escribo para saber si quieres retomar la cotizacion o agendar."}]},
        "handoff": {"sensitive_keywords": ["humano", "asesor", "agente", "reclamo", "queja", "molesto"], "high_score_threshold": 80, "strong_buy_signals": ["quiero comprar", "quiero agendar", "me interesa", "listo"], "angry_customer_keywords": ["molesto", "enojado", "queja", "pesimo", "mal servicio"]},
        "integrations": {"whatsapp": {"provider": "meta_cloud_api", "phone_number": whatsapp_number}, "calendar": {"mode": "google_oauth", "sync_strategy": "bidirectional"}, "instagram_dm": {"enabled": True}, "webchat": {"enabled": True}, "webhooks": []},
        "v7_modules": {"commerce": {"payments_in_chat": True, "auto_payment_reminders": True, "auto_payment_confirmation": True, "lead_close_on_payment": True, "receipt_via_whatsapp": True, "abandoned_quote_recovery": True}, "whatsapp_flows": ["precalificacion", "agendar_cita", "cotizacion_guiada", "actualizacion_datos", "encuesta_postventa", "onboarding_cliente"], "seller_mode": {"intent_scoring": True, "close_probability": True, "next_best_action": True, "objection_assist": True, "cooling_alert": True, "advisor_summary": True}, "multilingual": {"bot_language": language, "supported_languages": ["es", "en"], "detect_contact_language": True, "reply_in_detected_language": True, "template_languages": ["es", "en"], "fallback_by_language": True, "fallback_language": "en" if language == "es" else "es", "human_handoff_respects_language": True, "analytics_by_language": True, "tone_matrix_by_language": True, "native_voice_by_language": True}, "voice": {"transcription": True, "intent_from_audio": True, "text_or_audio_response": True, "operator_summary": True, "urgency_and_emotion": True, "tone_of_voice_detection": True, "context_from_vox": True, "use_voice_context_in_replies": True, "voice_memory_window": 3, "vox_context_priority": ["summary", "detected_language", "intent", "urgency_level", "emotion"]}},
        "talent": default_talent_config(),
    }
    vertical_overlay = {"personality": vertical_setup["personality"], "objective": vertical_setup["objective"], "business_knowledge": {**vertical_setup["business_knowledge"], "services": vertical_setup["services"], "faqs": vertical_setup["faqs"]}, "rules": vertical_setup["rules"], "agenda": vertical_setup["agenda"], "followups": vertical_setup["followups"], "handoff": vertical_setup["handoff"], "integrations": vertical_setup["integrations"], "v7_modules": vertical_setup["v7_modules"], "vertical_context": vertical_setup["vertical_context"], "production_readiness": {"default_behavior_seeded": True, "default_templates_seeded": True, "recommended_integrations": profile.get("recommended_integrations", [])}}
    return _merge_dict(base_config, vertical_overlay)
