from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_release_gate_executes_frontend_node_guardrails() -> None:
    gate = (ROOT / "backend/scripts/release_gate.py").read_text(encoding="utf-8")

    for script in [
        "check-local-imports.mjs",
        "check-bot-creation-guardrails.mjs",
        "check-p1-operational-guardrails.mjs",
        "check-critical-flow-guardrails.mjs",
        "check-multitenant-security-guardrails.mjs",
        "check-workflow-runtime-guardrails.mjs",
        "validate-env.mjs",
    ]:
        assert script in gate

    assert "def run_frontend_guardrails()" in gate
    assert "for script in NODE_CHECKS" in gate
    assert "run_node_script(script, FRONTEND)" in gate
    assert "frontend guardrail scripts present" not in gate
