from __future__ import annotations

from backend.app.ai_evals.harness import EvalCase, evaluate_cases, flatten_text, ok
from backend.app.ai_workflows.bot_autopilot.vertical_intelligence import build_vertical_intelligence_pack, detect_vertical
from backend.app.ai_workflows.whatsapp_pack.generator import generate_whatsapp_production_pack


def _run_pack(text: str) -> dict:
    vertical_pack = build_vertical_intelligence_pack(detect_vertical(text))
    return generate_whatsapp_production_pack(vertical_pack, {"business_name": "WAOS Demo", "vertical": vertical_pack.get("vertical_id")})


def _check(actual: dict) -> list:
    messages = actual.get("runtime_messages") or {}
    anti_blocking = actual.get("anti_blocking_rules") or {}
    opt_out = actual.get("opt_out_rules") or {}
    frequency_caps = actual.get("frequency_caps") or {}
    all_text = flatten_text(actual).lower()
    return [
        ok("fallback_is_grounded", "no tengo" in str(messages.get("fallback", "")).lower() and "persona" in str(messages.get("fallback", "")).lower(), expected="safe fallback with human escalation", actual=messages.get("fallback"), critical=True),
        ok("appointment_requires_confirmation", "pendiente" in str(messages.get("appointment_confirmation", "")).lower() and "confirmación" in str(messages.get("appointment_confirmation", "")).lower(), expected="appointments pending confirmation", actual=messages.get("appointment_confirmation"), critical=True),
        ok("opt_out_keywords", {"STOP", "BAJA", "CANCELAR"} <= set(opt_out.get("keywords") or []), expected=["STOP", "BAJA", "CANCELAR"], actual=opt_out.get("keywords"), critical=True),
        ok("opt_out_ack", "no enviaremos" in str(opt_out.get("required_reply", "")).lower(), expected="explicit stop acknowledgement", actual=opt_out.get("required_reply"), critical=True),
        ok("anti_spam_enabled", anti_blocking.get("respect_opt_out") is True and anti_blocking.get("no_spam") is True, expected={"respect_opt_out": True, "no_spam": True}, actual=anti_blocking, critical=True),
        ok("frequency_caps_present", int(frequency_caps.get("marketing_per_week") or 99) <= 2 and int(frequency_caps.get("collections_per_week") or 99) <= 2, expected="weekly caps <= 2", actual=frequency_caps, critical=True),
        ok("requires_meta_approval", "meta" in all_text and "approval" in all_text, expected="Meta approval warning", actual=actual.get("template_risk_notes") or actual.get("pending_approvals")),
    ]


CASES = [
    EvalCase("dental_whatsapp_pack", "whatsapp_safety", {"vertical": "dental"}, {"opt_out": True, "frequency_caps": True}, lambda: _run_pack("clínica dental"), _check, critical=True),
    EvalCase("generic_whatsapp_pack", "whatsapp_safety", {"vertical": "generic"}, {"opt_out": True, "frequency_caps": True}, lambda: _run_pack("servicios locales"), _check),
]


def run_eval() -> dict:
    return evaluate_cases("eval_whatsapp_template_pack", CASES, min_score=0.95)
