from __future__ import annotations
AGENTS=["booking","sales","support","collections","recovery","retention","general"]
def generate_agent_policy_pack(vertical_pack: dict, intensity: str="balanced") -> dict:
    policies=[]
    for agent in AGENTS:
        policies.append({"agent_key":agent,"objective":{"booking":"agendar con seguridad","sales":"convertir sin inventar ofertas","support":"resolver FAQ grounded","collections":"recordar pagos con límites"}.get(agent,"operar intención"),"allowed_actions":["responder FAQ grounded","tag_contact","handoff_to_human"],"forbidden_actions":["inventar precios","inventar descuentos","confirmar cita sin calendario","ejecutar pago sin confirmación"],"required_context":["business_profile","knowledge_plan","policy_pack"],"handoff_triggers":vertical_pack.get("escalation_rules",[]),"max_actions_per_contact":3,"confirmation_required_actions":["book_appointment","create_payment_link","reschedule"],"risk_phrases":vertical_pack.get("prohibited_claims",[]),"escalation_sla":"same_business_day","memory_scope":"bot_contact","outcome_targets":["appointment_scheduled","sale_closed","human_handoff"]})
    return {"agents":policies,"policy_version":"agent_policy_pack.v1","runtime":"agent_policy_runtime"}
