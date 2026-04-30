from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict
WorkflowStatus = Literal["pending","running","waiting_for_provider","waiting_for_human_confirmation","waiting_for_integration","waiting_for_whatsapp_approval","paused_cost_limit","completed","completed_partial","failed","retryable_failed","stale","cancelled"]
StepStatus = Literal["pending","running","completed","skipped","failed","retrying","blocked","waiting_human","waiting_provider"]
Intensity = Literal["conservative","balanced","aggressive","savage","godmode"]
class WorkflowRunRecord(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str; organization_id: str; bot_id: str | None = None; wizard_id: str | None = None; user_id: str | None = None
    workflow_type: str = "bot_autopilot"; status: WorkflowStatus = "pending"; intensity: Intensity = "balanced"; prompt: str = ""
    current_step: str | None = None; progress: int = 0; config_json: dict[str, Any] = Field(default_factory=dict)
    result_json: dict[str, Any] = Field(default_factory=dict); error_json: dict[str, Any] = Field(default_factory=dict); cost_estimate_usd: float = 0.0
class WorkflowEvent(BaseModel):
    id: str | None = None; run_id: str; event_type: str; message: str = ""; progress: int = 0; entity_type: str | None = None; entity_id: str | None = None; payload_json: dict[str, Any] = Field(default_factory=dict)
