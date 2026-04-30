from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_release_handoff_documents_openai_secret_as_blocking_requirement():
    handoff = (ROOT / "docs" / "WAOS_RELEASE_CANDIDATE_HANDOFF.md").read_text()

    assert "OPENAI_API_KEY" in handoff
    assert "GitHub Actions secret" in handoff
    assert "certificación productiva debe fallar" in handoff
    assert "production-certification-from-zip" in handoff


def test_ai_eval_readiness_documents_live_secret_release_checklist():
    readiness = (ROOT / "docs" / "AI_EVALS_PRODUCTION_READINESS_P1_3_2026-04-29.md").read_text()

    assert "Requisito bloqueante de release" in readiness
    assert "OPENAI_API_KEY" in readiness
    assert "Settings -> Secrets and variables -> Actions" in readiness
    assert "WAOS_REQUIRE_LIVE_AI_EVALS=1" in readiness
    assert "WAOS_AI_EVAL_LIVE=1" in readiness
