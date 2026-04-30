from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_POLICY_MARKERS = (
    "Render is a backend deploy gate only, not full-stack certification.",
    "Production deploys must be promoted only from CI-certified tags/build artifacts that passed scripts/validate_release_in_ci.sh.",
)
REQUIRED_BACKEND_BUILD_STEPS = (
    "python scripts/validate_render_env.py",
    "python scripts/validate_release_candidate.py",
    "python scripts/check_repo_hygiene.py",
    "python scripts/release_gate.py",
)
FORBIDDEN_RENDER_CERTIFICATION_STEPS = (
    "scripts/validate_release_in_ci.sh",
    "npm ci",
    "npm run build",
    "npm run typecheck",
    "npm audit",
)


def _render_files() -> list[Path]:
    candidates = [ROOT / "render.yaml", ROOT / "backend" / "render.yaml"]
    seen: set[Path] = set()
    existing: list[Path] = []
    for path in candidates:
        resolved = path.resolve()
        if resolved not in seen and path.exists():
            existing.append(path)
            seen.add(resolved)
    return existing


def _build_command_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip().startswith("buildCommand:")]


def _check_text(path: Path) -> None:
    text = path.read_text()
    if "APP_ENV\n        value: production" in text and "STARTUP_DB_REQUIRED\n        value: false" in text:
        raise SystemExit(f"{path}: STARTUP_DB_REQUIRED=false is forbidden in production")
    for marker in REQUIRED_POLICY_MARKERS:
        if marker not in text:
            raise SystemExit(f"{path}: missing Render certification policy marker: {marker}")


def _check_services_text_only(path: Path) -> None:
    text = path.read_text()
    service_count = text.count("  - type: web") + text.count("  - type: worker")
    if service_count < 1:
        raise SystemExit(f"{path}: missing Render web/worker services")
    if text.count("rootDir: backend") < service_count:
        raise SystemExit(f"{path}: every Render web/worker service must keep rootDir=backend")
    build_commands = _build_command_lines(text)
    if len(build_commands) < service_count:
        raise SystemExit(f"{path}: missing buildCommand for one or more Render services")
    for line in build_commands:
        for step in REQUIRED_BACKEND_BUILD_STEPS:
            if step not in line:
                raise SystemExit(f"{path}: buildCommand missing backend deploy gate step: {step}")
        for forbidden in FORBIDDEN_RENDER_CERTIFICATION_STEPS:
            if forbidden in line:
                raise SystemExit(f"{path}: buildCommand must not include full-stack certification step {forbidden!r}")
    if text.count("buildFilter:\n      paths:\n        - backend/**") < service_count:
        raise SystemExit(f"{path}: every Render web/worker service must keep buildFilter.paths=['backend/**']")


def main() -> None:
    files = _render_files()
    if not files:
        raise SystemExit("render.yaml not found")
    for item in files:
        _check_text(item)
        _check_services_text_only(item)
    print("render env ok; backend-only Render deploy gate policy enforced")


if __name__ == "__main__":
    main()
