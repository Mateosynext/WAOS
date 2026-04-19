from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from .config import settings
from .world_class import circuit_allow, circuit_breaker_summary, circuit_record_failure, circuit_record_success

T = TypeVar("T")


@dataclass(frozen=True)
class CircuitBreakerPolicy:
    provider: str
    failure_threshold: int
    open_minutes: int


def provider_policy(provider: str) -> CircuitBreakerPolicy:
    normalized = str(provider or "unknown").strip().lower()
    if normalized in {"meta", "meta_whatsapp", "whatsapp", "meta_graph"}:
        return CircuitBreakerPolicy(
            provider="meta_whatsapp",
            failure_threshold=settings.meta_circuit_failure_threshold,
            open_minutes=settings.meta_circuit_open_minutes,
        )
    if normalized in {"openai", "ai"}:
        return CircuitBreakerPolicy(
            provider="openai",
            failure_threshold=settings.openai_circuit_failure_threshold,
            open_minutes=settings.openai_circuit_open_minutes,
        )
    return CircuitBreakerPolicy(provider=normalized or "unknown", failure_threshold=3, open_minutes=2)


def circuit_guard(
    conn,
    *,
    provider: str,
    circuit_key: str,
    organization_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[bool, dict[str, Any], CircuitBreakerPolicy]:
    policy = provider_policy(provider)
    merged_metadata = {**(metadata or {})}
    if organization_id:
        merged_metadata.setdefault("organization_id", organization_id)
    allowed, state = circuit_allow(
        conn,
        provider=policy.provider,
        circuit_key=circuit_key,
        failure_threshold=policy.failure_threshold,
        open_minutes=policy.open_minutes,
    )
    if merged_metadata:
        state = {**state, "metadata": merged_metadata}
    return allowed, state, policy


def record_provider_success(
    conn,
    *,
    provider: str,
    circuit_key: str,
    organization_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = provider_policy(provider)
    merged_metadata = {**(metadata or {})}
    if organization_id:
        merged_metadata.setdefault("organization_id", organization_id)
    return circuit_record_success(conn, provider=policy.provider, circuit_key=circuit_key, metadata=merged_metadata)


def record_provider_failure(
    conn,
    *,
    provider: str,
    circuit_key: str,
    error_text: str,
    organization_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = provider_policy(provider)
    merged_metadata = {**(metadata or {})}
    if organization_id:
        merged_metadata.setdefault("organization_id", organization_id)
    return circuit_record_failure(
        conn,
        provider=policy.provider,
        circuit_key=circuit_key,
        error_text=error_text,
        failure_threshold=policy.failure_threshold,
        open_minutes=policy.open_minutes,
        metadata=merged_metadata,
    )


def run_with_circuit(
    conn,
    *,
    provider: str,
    circuit_key: str,
    operation: Callable[[], T],
    organization_id: str | None = None,
    success_metadata: dict[str, Any] | None = None,
    failure_metadata: dict[str, Any] | None = None,
) -> tuple[bool, T | None, dict[str, Any]]:
    allowed, state, _policy = circuit_guard(
        conn,
        provider=provider,
        circuit_key=circuit_key,
        organization_id=organization_id,
        metadata=failure_metadata,
    )
    if not allowed:
        return False, None, state
    try:
        result = operation()
    except Exception as exc:
        breaker = record_provider_failure(
            conn,
            provider=provider,
            circuit_key=circuit_key,
            error_text=str(exc),
            organization_id=organization_id,
            metadata=failure_metadata,
        )
        return False, None, breaker
    breaker = record_provider_success(
        conn,
        provider=provider,
        circuit_key=circuit_key,
        organization_id=organization_id,
        metadata=success_metadata,
    )
    return True, result, breaker


def circuit_snapshot(conn, *, provider: str | None = None) -> dict[str, Any]:
    normalized = provider_policy(provider).provider if provider else None
    return circuit_breaker_summary(conn, provider=normalized)
