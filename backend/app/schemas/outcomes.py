from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OutcomeExposureRequest(BaseModel):
    organization_id: str
    bot_id: str
    conversation_id: str | None = None
    contact_id: str | None = None
    lead_id: str | None = None
    appointment_id: str | None = None
    payment_id: str | None = None
    message_id: str | None = None
    source_type: str = Field(default="assistant_message")
    channel: str = Field(default="whatsapp")
    prompt_run_id: str | None = None
    prompt_version_id: str | None = None
    flow_id: str | None = None
    flow_version_id: str | None = None
    template_id: str | None = None
    template_version_id: str | None = None
    routing_rule_id: str | None = None
    decision_path_id: str | None = None
    timing_policy_id: str | None = None
    tone_policy_id: str | None = None
    nba_policy_id: str | None = None
    escalation_policy_id: str | None = None
    playbook_id: str | None = None
    playbook_version_id: str | None = None
    handoff_id: str | None = None
    handoff_kind: str | None = None
    specialist_agent_key: str | None = None
    specialist_agent_version: str | None = None
    specialist_prompt_id: str | None = None
    intent_family: str | None = None
    agent_routing_run_id: str | None = None
    policy_profile_key: str | None = None
    policy_profile_version: str | None = None
    policy_evaluation_id: str | None = None
    operator_user_id: str | None = None
    assigned_variant: str | None = None
    vertical: str | None = None
    funnel_stage: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    sent_at: str | None = None


class OutcomeEventRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    conversation_id: str | None = None
    contact_id: str | None = None
    lead_id: str | None = None
    appointment_id: str | None = None
    payment_id: str | None = None
    review_id: str | None = None
    event_name: str
    event_category: str
    event_timestamp: str | None = None
    source_system: str = Field(default="waos")
    external_event_id: str | None = None
    status: str = Field(default="recorded")
    value_number: float | None = None
    value_text: str | None = None
    value: dict[str, Any] = Field(default_factory=dict)
    operator_user_id: str | None = None
    vertical: str | None = None
    funnel_stage: str | None = None
    dedupe_key: str | None = None


class OutcomeOperatorSignalRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    conversation_id: str | None = None
    contact_id: str | None = None
    lead_id: str | None = None
    appointment_id: str | None = None
    payment_id: str | None = None
    signal_name: str
    signal_status: str = Field(default="recorded")
    signal_value: float | None = None
    signal_text: str | None = None
    operator_user_id: str | None = None
    vertical: str | None = None
    funnel_stage: str | None = None
    timestamp: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OutcomeRecomputeRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    windows: list[str] = Field(default_factory=lambda: ["7d", "28d"])
    attribution_window_hours: int = Field(default=168, ge=1, le=24 * 90)


class OutcomeDecisionApplyRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    entity_type: str
    entity_id: str
    action: str
    decision_source: str = Field(default="scorecard")
    reason_code: str
    previous_state: dict[str, Any] = Field(default_factory=dict)
    new_state: dict[str, Any] = Field(default_factory=dict)
    evidence_snapshot: dict[str, Any] = Field(default_factory=dict)


class OutcomeDecisionRollbackRequest(BaseModel):
    organization_id: str
    note: str | None = None
