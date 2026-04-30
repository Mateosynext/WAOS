from __future__ import annotations
BASE=["lead_frio","lead_caliente","pregunta_precio","pregunta_horario","pide_humano","objecion_precio","quiere_agendar","quiere_reagendar","queja","urgencia","fuera_de_horario","pregunta_sensible","promesa_prohibida","cliente_enojado","lead_no_responde","pago_pendiente","cancelacion","soporte_postventa","integracion_faltante","fuera_de_conocimiento","prompt_injection","whatsapp_opt_out","frequency_cap"]
def build_scenarios(vertical_pack: dict, count: int=8) -> list[dict]:
    return [{"scenario_id":f"scenario_{i+1}","scenario_key":key,"user_message":key.replace("_"," "),"expected_behavior":"ground, follow policy, escalate when needed"} for i,key in enumerate(BASE[:count])]
