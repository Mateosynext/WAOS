# WAOS AI Production Audit

## Alcance
Auditoría del repo para convertir WAOS en un AI-Native WhatsApp Agent Operating System. La base existente incluye guided onboarding, AI prefill/autopilot legacy, dry run, autofix, apply, runtimes de multi-agent/policy/tool/outcomes/proactive/optimizer/knowledge/WhatsApp/voice y Bot Studio modular.

## Hallazgos
1. **AI Autopilot actual**: `backend/app/vertical_onboarding_ai_prefill.py` ya tiene `generate_ai_wizard_prefill`, `generate_ai_wizard_autopilot` y `apply_ai_autofix_to_wizard`. Es útil pero síncrono, centrado en wizard y sin workflow run persistente.
2. **Guided onboarding**: `vertical_onboarding_runtime.py` contiene start/dry-run/apply; se reutiliza como capa de compatibilidad.
3. **Dry run**: existe y produce `apply_ready`/snapshot, pero no estaba conectado a simulation suite ni go-live readiness persistente.
4. **Autofix**: existe, pero no separaba explícitamente blockers safe/unsafe para precios, horarios, promociones e integraciones.
5. **Apply**: existe en wizard, pero no tenía release/canary plan ni human gate centralizado por workflow.
6. **WhatsApp runtime**: hay módulos `whatsapp*`, `whatsapp_safety.py`, governance/delivery truth en tests; deben alimentar production pack.
7. **Multi-agent routing**: existe `multi_agent_runtime.py`; faltaba generación de Specialist Agents Config y Agent Policy Pack como artifact.
8. **Policy engine**: existe `agent_policy_runtime.py`, `policy_engine.py`; faltaba policy pack versionado por setup.
9. **Tool execution**: existen módulos `tool_execution*`; faltaba plan de ejecución con preview, idempotency y confirmation rules.
10. **Outcomes closed loop**: existen `outcomes*`; faltaba conectarlo al setup y learning recommendations.
11. **Proactive reasoning**: existe `proactive_reasoning_runtime.py`; faltaban gates WhatsApp/frequency/template en documentación y artifacts.
12. **Knowledge ingestion**: existen `knowledge_runtime/` y `live_knowledge_runtime/`; faltaba Knowledge Grounding Plan.
13. **Voice**: existe `voice_channel_runtime.py` y `telephony_twilio.py`; se documenta como canal adyacente, no camino crítico del autopilot.
14. **Optimizer**: existe `optimizer_runtime.py`; faltaba output de recomendaciones desde outcomes.
15. **Frontend Bot Studio**: `/bot-studio` exponía Create/Reconfigure, “Crear desde cero”, rutas canónicas y pantallas manuales.
16. **Flujo manual visible**: context → identity → offer → knowledge → integrations → review → validate → apply → success seguía público.
17. **Rutas manuales**: siguen como compatibilidad, ahora detrás de `NEXT_PUBLIC_ENABLE_MANUAL_BOT_CREATE`.
18. **Copy confuso**: se reemplazó por AI Command Center y CTAs “Crear con IA”.
19. **Real**: legacy guided onboarding, dry run, autofix, apply, policy/tool/WhatsApp runtimes.
20. **Heurístico**: detección vertical y packs ahora quedan explícitos como artifacts; se separó del apply.
21. **Mock/timers**: `AiSetupAssistant` usaba `setTimeout`; se eliminó para no simular progreso.
22. **Persistencia insuficiente**: no había runs/steps/events/cost ledger; se agregan tablas.
23. **Streaming**: no había SSE de workflow; se agrega endpoint y hook `EventSource`.
24. **Cost control**: se agrega CostGovernor y AI cost ledger.
25. **Inspector**: se agrega base de AI Ops Inspector y endpoints internos.
26. **Tests**: se agregan tests estáticos backend/frontend y eval harness.
27. **Go-live**: se agrega readiness/release/canary plan; apply se bloquea si readiness está blocked.
28. **Reutilizable**: legacy autopilot, dry-run, autofix, policy/tool/knowledge/WhatsApp runtimes.
29. **Refactor**: frontend manual visible, model routing, prompts, workflow events.
30. **Nuevo**: workflow engine, Bot Autopilot 2.0, Simulation Suite, Readiness, packs, AI Command Center, SSE, AI Ops base.
