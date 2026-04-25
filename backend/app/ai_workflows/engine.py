from __future__ import annotations
from dataclasses import dataclass
@dataclass
class WorkflowEngine:
    name: str="waos_ai_workflow_engine"
    supports: tuple[str,...] = ("retry","fallback","timeout","cancel","resume","pause","partial_failure","idempotency","event_streaming","audit_logging","cost_tracking","human_gates","tenant_isolation")
