from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "frontend" / "scripts" / "check-local-imports.mjs"


def test_local_import_guardrail_uses_linear_line_scanner_not_global_multiline_regex() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "extractSpecs(source)" in source
    assert "source.split(/\\r?\\n/)" in source
    assert "extractDynamicSpecs(line)" in source
    assert "extractStaticSpec(line)" in source

    forbidden_fragments = [
        "const importPattern",
        "matchAll(importPattern)",
        "/gm",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in source
