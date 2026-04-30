from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_reproducible_zip_ci_runs_frontend_node_tests() -> None:
    ci = (ROOT / "scripts" / "validate_release_in_ci.sh").read_text(encoding="utf-8")

    assert 'run_with_timeout "frontend npm ci"' in ci
    assert 'run_with_timeout "frontend SCA npm audit"' in ci
    assert 'npm audit --audit-level="$NPM_AUDIT_LEVEL"' in ci
    assert 'run_with_timeout "frontend typecheck"' in ci
    assert 'run_with_timeout "frontend production build"' in ci
    assert 'test -s .next/BUILD_ID' in ci
    assert 'run_with_timeout "frontend node tests"' in ci
    assert 'npm run test:node' in ci


def test_github_workflow_runs_frontend_node_tests() -> None:
    workflow = (ROOT / ".github/workflows/waos-release-validation.yml").read_text(encoding="utf-8")

    assert "npm ci --no-audit --no-fund" in workflow
    assert "npm audit --audit-level=moderate" in workflow
    assert "npm run typecheck" in workflow
    assert "npm run build" in workflow
    assert "test -s .next/BUILD_ID" in workflow
    assert "npm run test:node" in workflow


def test_frontend_certification_gap_is_documented() -> None:
    handoff = (ROOT / "docs" / "WAOS_RELEASE_CANDIDATE_HANDOFF.md").read_text(encoding="utf-8")
    doc = (ROOT / "docs" / "FRONTEND_CERTIFICATION_REQUIREMENT_P1_7_2026-04-30.md").read_text(encoding="utf-8")

    for required in [
        "npm ci --no-audit --no-fund",
        "npm audit --audit-level=moderate",
        "npm run typecheck",
        "npm run build",
        "npm run test:node",
        "no se considera certificado",
    ]:
        assert required in handoff or required in doc
