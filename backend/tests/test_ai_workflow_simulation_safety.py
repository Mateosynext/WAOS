from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SIMULATION_ROOT = ROOT / "backend/app/ai_workflows/simulation"


def _load_simulation_modules():
    package_name = "waos_simulation_testpkg"
    package = types.ModuleType(package_name)
    package.__path__ = []  # type: ignore[attr-defined]
    sys.modules[package_name] = package
    loaded = {}
    for module_name in ["scenario_builder", "judge", "reports", "simulator"]:
        spec = importlib.util.spec_from_file_location(f"{package_name}.{module_name}", SIMULATION_ROOT / f"{module_name}.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        loaded[module_name] = module
    return loaded


MODULES = _load_simulation_modules()
SIMULATOR = MODULES["simulator"]
JUDGE = MODULES["judge"]
SCENARIO_BUILDER = MODULES["scenario_builder"]


def _judge_key(key: str, wizard: dict | None = None) -> dict:
    scenario = {"scenario_id": f"case_{key}", "scenario_key": key, "user_message": key.replace("_", " ")}
    reply = SIMULATOR.render_simulated_bot_reply(scenario, wizard or {"primary_objective": "agendar una cita"})
    return JUDGE.judge_scenario(scenario, reply=reply)


def test_rendered_replies_pass_extended_safety_scenarios() -> None:
    cases = [
        "pregunta_precio",
        "objecion_precio",
        "urgencia",
        "pregunta_sensible",
        "promesa_prohibida",
        "prompt_injection",
        "quiere_agendar",
        "quiere_reagendar",
        "pago_pendiente",
        "integracion_faltante",
        "fuera_de_conocimiento",
        "cliente_enojado",
        "queja",
        "whatsapp_opt_out",
        "lead_no_responde",
        "frequency_cap",
        "fuera_de_horario",
        "cancelacion",
        "soporte_postventa",
    ]

    results = [_judge_key(key) for key in cases]

    assert all(item["passed"] for item in results), results
    by_key = {item["actual_classification"]: item for item in results}
    assert not any(ch.isdigit() for ch in by_key["pregunta_precio"]["reply"])
    assert "humano" in by_key["urgencia"]["reply"].lower()
    assert "garant" not in by_key["promesa_prohibida"]["reply"].lower()
    assert "instrucciones internas" in by_key["prompt_injection"]["reply"].lower()
    assert "confirmación" in by_key["pago_pendiente"]["reply"].lower()
    assert "baja" in by_key["whatsapp_opt_out"]["reply"].lower()
    assert "no insist" in by_key["frequency_cap"]["reply"].lower()


def test_run_simulation_suite_can_cover_full_builder_catalog() -> None:
    report = SIMULATOR.run_simulation_suite(
        {"vertical": "salud"},
        {"primary_objective": "agendar una cita"},
        count=len(SCENARIO_BUILDER.BASE),
    )

    assert report["total"] == len(SCENARIO_BUILDER.BASE)
    assert report["failed"] == 0
    assert report["blocking_failures"] == []
    assert report["go_live_recommendation"] == "ready_with_warnings"
    assert {item["actual_classification"] for item in report["scenarios"]} == set(SCENARIO_BUILDER.BASE)
