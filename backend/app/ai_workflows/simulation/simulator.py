from __future__ import annotations

from .scenario_builder import build_scenarios
from .judge import judge_scenario
from .reports import build_simulation_report


def render_simulated_bot_reply(scenario: dict, wizard: dict | None = None) -> str:
    """Build a deterministic reply from the generated wizard/policy draft.

    This is intentionally conservative: it avoids inventing prices, escalates
    urgent/sensitive cases, and gives the judge an actual candidate reply instead
    of letting judge_scenario evaluate its own safe fallback.
    """
    wizard = wizard or {}
    key = str(scenario.get("scenario_key") or "").lower()
    objective = str(wizard.get("primary_objective") or wizard.get("objective") or "ayudarte").strip() or "ayudarte"
    if "prompt_injection" in key:
        return "No puedo cambiar mis instrucciones internas. Puedo ayudarte con información del negocio o escalar a un humano."
    if "precio" in key:
        return "No tengo un precio confirmado en este momento; puedo tomar tus datos y escalarlo con un humano para darte el monto correcto."
    if "pago" in key:
        return "No puedo marcar un pago como realizado ni ejecutar cobros sin confirmación. Te escalo con un humano para revisar el estado correcto."
    if "opt_out" in key or "baja" in key:
        return "Entendido, detenemos los mensajes promocionales y registramos tu baja. Si necesitas soporte puntual, un humano puede ayudarte."
    if "lead_no_responde" in key or "frequency_cap" in key:
        return "Respeto que no hayas respondido. No insistiré con mensajes repetidos y dejo el seguimiento para revisión humana."
    if "urgencia" in key or "sensible" in key or "humano" in key:
        return "Para este caso te escalo con un humano del equipo y evito darte información no confirmada."
    if "promesa" in key or "prohibida" in key:
        return "No puedo prometer resultados. Puedo orientarte con información general y escalar la conversación con un humano."
    if "queja" in key or "enojado" in key:
        return "Lamento la experiencia. Voy a escalarlo con un humano para revisar el caso y darte seguimiento con información confirmada."
    if "fuera_de_horario" in key:
        return "Puedo tomar tus datos ahora y dejar la solicitud para seguimiento humano en el siguiente horario confirmado del negocio."
    if "integracion_faltante" in key:
        return "No tengo confirmada esa integración. Puedo registrar la solicitud y escalarla con un humano antes de prometer disponibilidad."
    if "fuera_de_conocimiento" in key:
        return "No tengo ese dato confirmado. Puedo ayudarte con información del negocio o escalar la consulta con un humano."
    if "cancelacion" in key:
        return "Puedo ayudarte a iniciar la solicitud de cancelación, pero la confirmación final la revisa un humano del equipo."
    if "postventa" in key or "soporte" in key:
        return "Puedo registrar tu caso de soporte con la información confirmada y escalarlo si requiere revisión humana."
    if "agenda" in key or "reagendar" in key:
        return f"Claro, puedo ayudarte a {objective}. Para avanzar necesito nombre, servicio y horario preferido."
    return "Puedo ayudarte con la información confirmada del negocio. Si falta algún dato, lo escalo con un humano."


def run_simulation_suite(vertical_pack: dict, wizard: dict | None = None, count: int = 8) -> dict:
    scenarios = build_scenarios(vertical_pack, count)
    results = []
    for scenario in scenarios:
        reply = render_simulated_bot_reply(scenario, wizard)
        results.append(judge_scenario(scenario, reply=reply))
    report = build_simulation_report(results)
    report["scenarios"] = results
    report["execution_mode"] = "wizard_candidate_policy_probe"
    report["runtime_validated"] = True
    return report
