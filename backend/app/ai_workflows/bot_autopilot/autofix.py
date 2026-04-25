SAFE_AUTOFIX_ALLOWED=["estructurar CTAs","completar FAQs genéricas seguras","crear placeholders","crear handoff matrix","crear policies seguras","qualification questions"]
SAFE_AUTOFIX_FORBIDDEN=["inventar precios","inventar horarios","inventar promociones","inventar integraciones","inventar testimonios","inventar permisos legales","inventar certificados","inventar resultados médicos"]
def classify_blocker(blocker: str) -> str: return blocker
