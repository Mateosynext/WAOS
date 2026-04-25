# WAOS Frontend AI-First Refactor

Cambios:
- `/bot-studio` deja de mostrar Create/Reconfigure cards, “Crear desde cero” y “Rutas canónicas”.
- `frontend/features/ai-command-center/` concentra prompt, stream, artifacts, readiness, human confirmations y launch actions.
- `AiSetupAssistant` ya no usa timers falsos.
- `/bots`, `/onboarding`, home y releases usan copy AI-first (“Crear con IA”, “Construir agente con IA”).
