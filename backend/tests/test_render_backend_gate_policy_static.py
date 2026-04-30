from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(rel: str) -> str:
    return (ROOT / rel).read_text()


def test_render_yaml_declares_backend_only_not_full_stack_certification() -> None:
    for rel in ("render.yaml", "backend/render.yaml"):
        text = read(rel)
        assert "Render is a backend deploy gate only, not full-stack certification." in text
        assert "Production deploys must be promoted only from CI-certified tags/build artifacts that passed scripts/validate_release_in_ci.sh." in text
        assert "rootDir: backend" in text
        assert "paths:\n        - backend/**" in text


def test_render_builds_run_backend_policy_gate_but_not_ci_certification() -> None:
    for rel in ("render.yaml", "backend/render.yaml"):
        text = read(rel)
        assert "python scripts/validate_render_env.py" in text
        assert "python scripts/release_gate.py" in text
        assert "bash scripts/validate_release_in_ci.sh" not in text
        assert "npm ci" not in text
        assert "npm run build" not in text
        assert "npm run typecheck" not in text


def test_validate_render_env_enforces_policy_markers() -> None:
    script = read("backend/scripts/validate_render_env.py")
    assert "Render is a backend deploy gate only, not full-stack certification." in script
    assert "CI-certified tags/build artifacts" in script
    assert "FORBIDDEN_RENDER_CERTIFICATION_STEPS" in script
    assert "scripts/validate_release_in_ci.sh" in script
    assert "_check_services_text_only" in script
    assert "rootDir=backend" in script
