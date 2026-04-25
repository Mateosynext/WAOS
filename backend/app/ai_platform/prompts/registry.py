from __future__ import annotations
from dataclasses import dataclass
from typing import Any
@dataclass(frozen=True)
class PromptSpec:
    name: str; version: str; purpose: str; system_message: str; input_schema: dict[str, Any]; output_schema: dict[str, Any]; safety_rules: list[str]; examples: list[dict[str, Any]]; prohibited_claims: list[str]; json_only: bool=True
PROMPTS={name:PromptSpec(name=name,version="v1",purpose=f"WAOS {name}",system_message="Return JSON only. Do not invent prices, schedules, promotions, integrations, legal/medical claims or certifications.",input_schema={},output_schema={},safety_rules=["ground sensitive facts","require human confirmation for prices/hours/payments/legal/medical claims","never execute tools during setup"],examples=[],prohibited_claims=["guaranteed results","medical diagnosis","legal guarantee","unconfirmed discount"]) for name in ["intent_normalizer","vertical_detector","business_profile_builder","wizard_answers_builder","autofix_wizard","vertical_intelligence_pack","agent_policy_pack","specialist_agents_config","knowledge_plan","whatsapp_template_pack","tool_execution_plan","simulation_suite_builder","simulation_judge","go_live_readiness","operator_summary","client_summary","runtime_reply","runtime_verifier","memory_curator","outcome_optimizer","proactive_reasoning"]}
def get_prompt(name: str, version: str="v1") -> PromptSpec: return PROMPTS[name]
