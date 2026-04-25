from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class IntensityProfile:
    key: str; faq_count: int; policy_count: int; cta_count: int; autofix_rounds: int; simulations: int; strictness: str; enable_tools: bool; enable_templates: bool; enable_proactive: bool; max_cost_usd: float; human_gates: list[str]
PROFILES={
"conservative":IntensityProfile("conservative",3,3,2,0,3,"safe-minimal",False,False,False,0.5,["prices","hours","handoff"]),
"balanced":IntensityProfile("balanced",6,5,4,1,8,"standard",False,True,False,2,["prices","hours","handoff","knowledge"]),
"aggressive":IntensityProfile("aggressive",10,8,6,2,15,"strict",True,True,True,5,["prices","hours","promotions","handoff","tools"]),
"savage":IntensityProfile("savage",14,12,8,3,25,"production-critical",True,True,True,12,["prices","hours","promotions","handoff","legal","medical","tools","whatsapp"]),
"godmode":IntensityProfile("godmode",20,18,10,4,50,"adversarial",True,True,True,25,["admin","prices","hours","promotions","handoff","legal","medical","tools","whatsapp","canary"]),
}
def get_intensity_profile(key: str) -> IntensityProfile: return PROFILES.get(key, PROFILES["balanced"])
