from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HARDENING = (ROOT / "backend/app/hardening.py").read_text(encoding="utf-8")
VALIDATOR = (ROOT / "backend/scripts/validate_release_candidate.py").read_text(encoding="utf-8")


def test_body_limit_uses_streaming_cutoff_not_request_body_buffering() -> None:
    assert "await request.body()" not in HARDENING
    assert "async for chunk in request.stream()" in HARDENING
    assert "total += len(chunk)" in HARDENING
    assert "if total > limit" in HARDENING
    assert "request_body_too_large" in HARDENING


def test_bounded_body_is_replayed_downstream_after_validation() -> None:
    assert "def _restore_limited_body" in HARDENING
    assert "request._body = body" in HARDENING
    assert "request._receive = receive" in HARDENING
    assert "request._stream_consumed = False" in HARDENING


def test_release_validator_blocks_regression_to_full_body_read() -> None:
    assert "await request.body()" in VALIDATOR
    assert "body limit must use streaming cutoff" in VALIDATOR
