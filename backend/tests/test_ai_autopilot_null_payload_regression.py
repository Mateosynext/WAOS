from __future__ import annotations

import json

from app.ai_workflows.bot_autopilot.schemas import BotAutopilotRequest
from app.ai_workflows.persistence import _json


def base_payload() -> dict:
    return {
        "organization_id": "org_1",
        "bot_id": None,
        "user_description": "Clinica dental en CDMX que agenda limpiezas y ortodoncia por WhatsApp.",
        "vertical_id": None,
        "subvertical": None,
        "primary_objective": "agendar",
        "language": "es",
        "timezone": "America/Mexico_City",
        "intensity": "balanced",
        "auto_generate_knowledge": True,
        "auto_generate_templates": True,
        "auto_generate_tools": True,
        "auto_run_simulations": True,
        "auto_autofix": True,
        "auto_prepare_go_live": True,
        "auto_apply": False,
        "max_cost_usd": 12,
    }


def test_workflow_config_serializes_optional_bot_id_as_json_null() -> None:
    encoded = _json(base_payload())
    decoded = json.loads(encoded)

    assert decoded["bot_id"] is None
    assert decoded["vertical_id"] is None
    assert decoded["subvertical"] is None


def test_bot_autopilot_request_tolerates_legacy_empty_object_optionals() -> None:
    payload = base_payload()
    payload["bot_id"] = {}
    payload["vertical_id"] = {}
    payload["subvertical"] = {}
    payload["max_cost_usd"] = {}

    request = BotAutopilotRequest.model_validate(payload)

    assert request.bot_id is None
    assert request.vertical_id is None
    assert request.subvertical is None
    assert request.max_cost_usd is None


def test_bot_autopilot_request_tolerates_legacy_empty_object_booleans_and_defaults() -> None:
    payload = base_payload()
    payload.update(
        {
            "primary_objective": {},
            "language": {},
            "timezone": {},
            "auto_generate_knowledge": {},
            "auto_generate_templates": {},
            "auto_generate_tools": {},
            "auto_run_simulations": {},
            "auto_autofix": {},
            "auto_prepare_go_live": {},
            "auto_apply": {},
        }
    )

    request = BotAutopilotRequest.model_validate(payload)

    assert request.primary_objective == "agendar"
    assert request.language == "es"
    assert request.timezone == "America/Mexico_City"
    assert request.auto_generate_knowledge is True
    assert request.auto_generate_templates is True
    assert request.auto_generate_tools is True
    assert request.auto_run_simulations is True
    assert request.auto_autofix is True
    assert request.auto_prepare_go_live is True
    assert request.auto_apply is False


def test_bot_autopilot_request_keeps_human_gate_when_client_sends_auto_apply_true() -> None:
    payload = base_payload()
    payload["auto_apply"] = True

    request = BotAutopilotRequest.model_validate(payload)

    assert request.auto_apply is False
    assert "auto_apply_disabled_for_autopilot_start" in request.safety_warnings
