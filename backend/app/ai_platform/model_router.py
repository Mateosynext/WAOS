from __future__ import annotations
import time
from dataclasses import dataclass
TASKS={"intent_normalization":("openai","gpt-4.1-mini","gpt-4o-mini"),"vertical_detection":("openai","gpt-4.1-mini","gpt-4o-mini"),"wizard_generation":("openai","gpt-4.1","gpt-4.1-mini"),"business_profile":("openai","gpt-4.1-mini","gpt-4o-mini"),"policy_generation":("openai","gpt-4.1","gpt-4.1-mini"),"compliance_review":("openai","gpt-4.1","gpt-4.1-mini"),"simulation_generation":("openai","gpt-4.1-mini","gpt-4o-mini"),"simulation_judge":("openai","gpt-4.1","gpt-4.1-mini"),"autofix":("openai","gpt-4.1","gpt-4.1-mini"),"whatsapp_template_generation":("openai","gpt-4.1-mini","gpt-4o-mini"),"runtime_reply_generation":("openai","gpt-4.1-mini","gpt-4o-mini"),"grounding_verification":("openai","gpt-4.1","gpt-4.1-mini"),"memory_summarization":("openai","gpt-4.1-mini","gpt-4o-mini"),"outcome_analysis":("openai","gpt-4.1-mini","gpt-4o-mini"),"proactive_recommendation":("openai","gpt-4.1-mini","gpt-4o-mini")}
@dataclass
class ModelSelection:
    task: str; provider: str; model: str; fallback_model: str; timeout_ms: int=30000; prompt_version: str="v1"; json_mode: bool=True; cache_hit: bool=False; fallback_used: bool=False; latency_ms: int=0; cost_estimate_usd: float=0.0
class ModelRouter:
    def select(self, task: str, *, json_mode: bool=True) -> ModelSelection:
        provider, model, fallback = TASKS.get(task, TASKS["intent_normalization"]); t=time.perf_counter(); return ModelSelection(task,provider,model,fallback,json_mode=json_mode,latency_ms=int((time.perf_counter()-t)*1000))
model_router=ModelRouter()
