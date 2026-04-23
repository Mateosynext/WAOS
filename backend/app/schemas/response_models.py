from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class FlexibleSchema(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class ResponseMeta(FlexibleSchema):
    request_id: str | None = None
    correlation_id: str | None = None
    organization_id: str | None = None
    bot_id: str | None = None
    total: int | None = None
    limit: int | None = None
    offset: int | None = None


class ApiEnvelope(FlexibleSchema, Generic[T]):
    ok: bool = True
    data: T
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    request_id: str | None = None
    correlation_id: str | None = None


class OrganizationResponse(FlexibleSchema):
    id: str | None = None
    name: str | None = None
    slug: str | None = None
    status: str | None = None
    timezone: str | None = None
    vertical: str | None = None
    subvertical: str | None = None
    tenant_mode: str | None = None
    settings_json: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ConversationMessageResponse(FlexibleSchema):
    id: str | None = None
    conversation_id: str | None = None
    body: str | None = None
    direction: str | None = None
    kind: str | None = None
    source: str | None = None
    status: str | None = None
    created_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationCrossBotMemoryResponse(FlexibleSchema):
    id: str | None = None
    contact_id: str | None = None
    bot_id: str | None = None
    bot_name: str | None = None
    summary: str | None = None
    lead_stage: str | None = None
    lead_score: int | None = None
    memory: dict[str, Any] = Field(default_factory=dict)
    last_updated_at: str | None = None


class ConversationDetailResponse(FlexibleSchema):
    conversation: FlexibleSchema | dict[str, Any] | None = None
    contact: FlexibleSchema | dict[str, Any] | None = None
    memory: FlexibleSchema | dict[str, Any] | None = None
    bot: FlexibleSchema | dict[str, Any] | None = None
    tags: list[str] = Field(default_factory=list)
    latest_summary: dict[str, Any] | None = None
    cross_bot_memory: list[ConversationCrossBotMemoryResponse] = Field(default_factory=list)
    messages: list[ConversationMessageResponse] = Field(default_factory=list)


class ConversationListItemResponse(FlexibleSchema):
    id: str | None = None
    organization_id: str | None = None
    bot_id: str | None = None
    contact_id: str | None = None
    status: str | None = None
    assigned_user_id: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    bot_name: str | None = None
    current_intent: str | None = None
    lead_stage: str | None = None
    lead_score: int | None = None
    summary: str | None = None
    next_action: str | None = None
    followup_at: str | None = None
    priority_score: int | None = None
    priority_band: str | None = None
    next_best_action: str | None = None
    requires_human: bool | None = None
    attention_class: str | None = None
    stalled: bool | None = None
    work_queue_role: str | None = None
    work_queue_reason: str | None = None
    sla_status: str | None = None
    sla_due_at: str | None = None
    sla_target_minutes: int | None = None
    sla_overdue_minutes: int | None = None
    latest_message_preview: str | None = None
    last_inbound_at: str | None = None
    last_outbound_at: str | None = None


class ConversationQueueSummaryResponse(FlexibleSchema):
    role_key: str | None = None
    count: int | None = None
    requires_human: int | None = None
    stalled: int | None = None
    sla_breached: int | None = None
    top_priority: int | None = None


class ConversationWorkQueuesData(FlexibleSchema):
    organization_id: str | None = None
    queues: list[ConversationQueueSummaryResponse] = Field(default_factory=list)


class ConversationOwnershipOwnerResponse(FlexibleSchema):
    user_id: str | None = None
    role: str | None = None
    full_name: str | None = None
    open_count: int | None = None
    human_takeover_count: int | None = None


class ConversationOwnershipData(FlexibleSchema):
    organization_id: str | None = None
    unassigned_open: int | None = None
    owners: list[ConversationOwnershipOwnerResponse] = Field(default_factory=list)


class ConversationAssignmentResultResponse(FlexibleSchema):
    conversation_id: str | None = None
    assigned_user_id: str | None = None
    queue_role: str | None = None
    priority_score: int | None = None


class ConversationAutoAssignData(FlexibleSchema):
    organization_id: str | None = None
    assigned_count: int | None = None
    assignments: list[ConversationAssignmentResultResponse] = Field(default_factory=list)


class ConversationQueueResponse(FlexibleSchema):
    role_key: str | None = None
    reason: str | None = None


class ConversationSlaResponse(FlexibleSchema):
    status: str | None = None
    due_at: str | None = None
    target_minutes: int | None = None
    overdue_minutes: int | None = None


class ConversationDecisionSupportData(FlexibleSchema):
    conversation_id: str | None = None
    next_best_action: str | None = None
    priority_score: int | None = None
    priority_band: str | None = None
    confidence_score: int | None = None
    confidence_band: str | None = None
    queue: ConversationQueueResponse | None = None
    sla: ConversationSlaResponse | None = None
    explanation: dict[str, Any] = Field(default_factory=dict)
    risk_flags: list[dict[str, Any]] = Field(default_factory=list)
    takeover_brief: dict[str, Any] | None = None
    failed_takeover: dict[str, Any] | None = None
    reactivation_guardrails: dict[str, Any] | None = None
    reply_suggestion: dict[str, Any] | None = None


class ConversationMessageMutationResponse(FlexibleSchema):
    message: FlexibleSchema | dict[str, Any] | None = None
    outbox_id: str | None = None
    conversation: FlexibleSchema | dict[str, Any] | None = None


class ConversationReactivationData(FlexibleSchema):
    conversation: FlexibleSchema | dict[str, Any] | None = None
    reactivation: dict[str, Any] = Field(default_factory=dict)


class LeadMemoryResponse(FlexibleSchema):
    id: str | None = None
    organization_id: str | None = None
    contact_id: str | None = None
    bot_id: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    bot_name: str | None = None
    lead_stage: str | None = None
    lead_score: int | None = None
    interest: str | None = None
    objections: str | None = None
    summary: str | None = None
    next_action: str | None = None
    followup_at: str | None = None
    last_updated_at: str | None = None


class OnboardingSummaryCounts(FlexibleSchema):
    channels: int | None = None
    bots: int | None = None
    catalog_items: int | None = None
    appointments: int | None = None
    conversations: int | None = None
    messages: int | None = None
    payments: int | None = None


class OnboardingSummaryData(FlexibleSchema):
    organization_id: str | None = None
    bot_id: str | None = None
    tenant_mode: str | None = None
    vertical: str | None = None
    counts: OnboardingSummaryCounts | None = None
    progress: dict[str, int] = Field(default_factory=dict)
    readiness_score: int | None = None
    blockers: list[dict[str, Any]] = Field(default_factory=list)
    next_step: dict[str, Any] | None = None
    checklist: list[dict[str, Any]] = Field(default_factory=list)
    first_value_at: str | None = None


class OnboardingPayloadResponse(FlexibleSchema):
    pass


class OperationalBotSummaryResponse(FlexibleSchema):
    id: str | None = None
    name: str | None = None
    status: str | None = None
    ai_paused: bool | None = None
    current_state: str | None = None
    operational_state: str | None = None
    temp_unavailability_message: str | None = None
    operational_resume_at: str | None = None


class OperationalControlCountsResponse(FlexibleSchema):
    authorized_numbers: int | None = None
    recent_commands: int | None = None
    scheduled_actions: int | None = None
    alerts_open: int | None = None
    blocked_slots_today: int | None = None
    upcoming_appointments: int | None = None


class OperationalCommandResponse(FlexibleSchema):
    id: str | None = None
    organization_id: str | None = None
    bot_id: str | None = None
    source_channel: str | None = None
    actor_user_id: str | None = None
    actor_phone_e164: str | None = None
    detected_intent: str | None = None
    status: str | None = None
    risk_level: str | None = None
    requires_confirmation: bool | None = None
    confirmation_code: str | None = None
    approved_by_user_id: str | None = None
    approval_note: str | None = None
    parsed_entities: dict[str, Any] = Field(default_factory=dict)
    resolved_scope: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None
    scheduled_for: str | None = None
    executed_at: str | None = None
    undoable_until: str | None = None


class OperationalAuthorizedNumberResponse(FlexibleSchema):
    id: str | None = None
    organization_id: str | None = None
    bot_id: str | None = None
    phone_e164: str | None = None
    role: str | None = None
    allowed_intents: list[str] = Field(default_factory=list)
    scope: dict[str, Any] = Field(default_factory=dict)
    status: str | None = None
    verified_at: str | None = None
    last_used_at: str | None = None
    updated_at: str | None = None
    scope_summary: str | None = None


class OperationalScheduledActionResponse(FlexibleSchema):
    id: str | None = None
    action_type: str | None = None
    execute_at: str | None = None
    status: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class OperationalAppointmentResponse(FlexibleSchema):
    id: str | None = None
    scheduled_for: str | None = None
    status: str | None = None
    conversation_id: str | None = None
    contact_id: str | None = None


class OperationalOverrideResponse(FlexibleSchema):
    id: str | None = None
    override_type: str | None = None
    start_at: str | None = None
    end_at: str | None = None
    reason: str | None = None
    scope: dict[str, Any] = Field(default_factory=dict)
    status: str | None = None


class OperationalAlertResponse(FlexibleSchema):
    id: str | None = None
    severity: str | None = None
    alert_type: str | None = None
    title: str | None = None
    body: str | None = None
    status: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    command_id: str | None = None


class OperationalSummaryResponse(FlexibleSchema):
    organization_id: str | None = None
    bot_id: str | None = None
    bot: OperationalBotSummaryResponse | None = None
    counts: OperationalControlCountsResponse | None = None
    authorized_numbers: list[OperationalAuthorizedNumberResponse] = Field(default_factory=list)
    recent_commands: list[OperationalCommandResponse] = Field(default_factory=list)
    scheduled_actions: list[OperationalScheduledActionResponse] = Field(default_factory=list)
    alerts: list[OperationalAlertResponse] = Field(default_factory=list)
    upcoming_appointments: list[OperationalAppointmentResponse] = Field(default_factory=list)


class OperationalAvailabilitySummaryResponse(FlexibleSchema):
    appointments: int | None = None
    blocked_ranges: int | None = None
    open_exceptions: int | None = None


class OperationalAvailabilityResponse(FlexibleSchema):
    day: str | None = None
    start_at: str | None = None
    end_at: str | None = None
    appointments: list[OperationalAppointmentResponse] = Field(default_factory=list)
    overrides: list[OperationalOverrideResponse] = Field(default_factory=list)
    summary: OperationalAvailabilitySummaryResponse | None = None


class OperationalMetricCountResponse(FlexibleSchema):
    total: int | None = None
    executed: int | None = None
    failed: int | None = None
    awaiting_confirmation: int | None = None
    high_risk: int | None = None
    ambiguous: int | None = None
    rate_limited: int | None = None
    reverted: int | None = None
    alerts_open: int | None = None


class OperationalIntentMetricResponse(FlexibleSchema):
    intent: str | None = None
    count: int | None = None


class OperationalStatusMetricResponse(FlexibleSchema):
    status: str | None = None
    count: int | None = None


class OperationalMetricsResponse(FlexibleSchema):
    window_days: int | None = None
    summary: OperationalMetricCountResponse | None = None
    intents: list[OperationalIntentMetricResponse] = Field(default_factory=list)
    statuses: list[OperationalStatusMetricResponse] = Field(default_factory=list)


class OperationalCommandPreviewResponse(FlexibleSchema):
    ok: bool | None = None
    status: str | None = None
    reply_text: str | None = None
    intent: str | None = None
    entities: dict[str, Any] = Field(default_factory=dict)
    impact: dict[str, Any] = Field(default_factory=dict)
    requires_confirmation: bool | None = None
    requires_second_approval: bool | None = None


class OperationalRescheduleBatchResponse(FlexibleSchema):
    ok: bool | None = None
    status: str | None = None
    summary: str | None = None
    intent: str | None = None
    impact: dict[str, Any] = Field(default_factory=dict)
    plan: list[dict[str, Any]] = Field(default_factory=list)
    command: OperationalCommandResponse | None = None


class OutcomeExposureResponse(FlexibleSchema):
    id: str | None = None
    organization_id: str | None = None
    bot_id: str | None = None
    conversation_id: str | None = None
    contact_id: str | None = None
    source_type: str | None = None
    channel: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    sent_at: str | None = None
    created_at: str | None = None


class OutcomeEventResponse(FlexibleSchema):
    id: str | None = None
    organization_id: str | None = None
    bot_id: str | None = None
    event_name: str | None = None
    event_category: str | None = None
    outcome_direction: str | None = None
    value_number: float | None = None
    value_text: str | None = None
    value: dict[str, Any] = Field(default_factory=dict)
    event_timestamp: str | None = None
    created_at: str | None = None


class OutcomeScorecardResponse(FlexibleSchema):
    id: str | None = None
    organization_id: str | None = None
    bot_id: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    scorecard_window: str | None = None
    computed_at: str | None = None
    traffic_count: int | None = None
    primary_metric: str | None = None
    primary_metric_value: float | None = None
    outcome_score: float | None = None
    confidence_score: float | None = None
    guardrail_state: str | None = None
    recommendation: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    guardrails: dict[str, Any] = Field(default_factory=dict)
    rationale: dict[str, Any] = Field(default_factory=dict)


class OutcomeDecisionResponse(FlexibleSchema):
    id: str | None = None
    organization_id: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    decision_type: str | None = None
    status: str | None = None
    recommendation: str | None = None
    previous_state: dict[str, Any] = Field(default_factory=dict)
    new_state: dict[str, Any] = Field(default_factory=dict)
    evidence_snapshot: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class OutcomeRecordExposureData(FlexibleSchema):
    exposure: OutcomeExposureResponse | None = None


class OutcomeRecordEventData(FlexibleSchema):
    event: OutcomeEventResponse | None = None
    deduped: bool | None = None
    attribution_created: int | None = None
    scorecards_created: int | None = None


class OutcomeRecordOperatorSignalData(FlexibleSchema):
    event: OutcomeEventResponse | None = None
    scorecards_created: int | None = None


class OutcomeScorecardsData(FlexibleSchema):
    items: list[OutcomeScorecardResponse] = Field(default_factory=list)
    count: int | None = None


class OutcomeEntityDetailData(FlexibleSchema):
    entity_type: str | None = None
    entity_id: str | None = None
    latest_scorecard: OutcomeScorecardResponse | None = None
    scorecards: list[OutcomeScorecardResponse] = Field(default_factory=list)
    decisions: list[OutcomeDecisionResponse] = Field(default_factory=list)
    attribution: list[dict[str, Any]] = Field(default_factory=list)


class OutcomeDecisionsData(FlexibleSchema):
    items: list[OutcomeDecisionResponse] = Field(default_factory=list)
    count: int | None = None


class OutcomeAttributionData(FlexibleSchema):
    items: list[dict[str, Any]] = Field(default_factory=list)
    count: int | None = None


class OutcomeRecomputeData(FlexibleSchema):
    organization_id: str | None = None
    bot_id: str | None = None
    windows: list[str] = Field(default_factory=list)
    scorecards_created: int | None = None
    computed_at: str | None = None
