from __future__ import annotations

from typing import Any, TypedDict


class ClassificationResult(TypedDict, total=False):
    intent: str
    urgency_level: str
    urgency_score: int
    requested_human: bool
    score_delta: int
    _classifier_source: str


class ExecutionPlan(TypedDict, total=False):
    intent: str
    objectives: list[str]
    risk_flags: list[dict[str, Any]]
    tool_orchestration: dict[str, Any]


class GroundedContext(TypedDict, total=False):
    source_count: int
    coverage: dict[str, Any]
    grounding_mode: str
    sources: list[dict[str, Any]]


class GeneratedCandidate(TypedDict, total=False):
    text: str
    source: str
    verification: dict[str, Any]
    score_total: float
    selected: bool


class RankedReply(TypedDict, total=False):
    selected_variant: str
    candidates: list[GeneratedCandidate]
    candidate_count: int
    summary: dict[str, Any]


class VerificationResult(TypedDict, total=False):
    status: str
    issues: list[dict[str, Any]]


class MemoryDelta(TypedDict, total=False):
    lead_stage: str
    lead_score: int
    summary: str


class PipelineResult(TypedDict, total=False):
    classification: ClassificationResult
    grounded_context: GroundedContext
    plan: ExecutionPlan
    decision: dict[str, Any]
    verification: VerificationResult
    post_send_evaluation: dict[str, Any]
    self_state: dict[str, Any]
    response_message: dict[str, Any] | None
    updated_memory: dict[str, Any]
    jobs: list[dict[str, Any]]
    error: str | None
    execution_run: dict[str, Any]
