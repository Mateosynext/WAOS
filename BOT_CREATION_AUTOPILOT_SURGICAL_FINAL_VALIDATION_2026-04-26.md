# WAOS Bot Creation / Autopilot Surgical Final Validation

Fecha: 2026-04-26

## Objetivo

Aplicar el parche quirúrgico sobre `waos_bot_creation_hardened.zip` y dejar el ZIP final con el flujo de creación/inicio de bots blindado contra el error observado en producción:

```txt
TypeError: Object of type ValueError is not JSON serializable
POST /api/v1/ai/bot-autopilot?async_mode=true
intensity: "godmode"
AI_ENABLE_GODMODE=false
```

## Corrección aplicada

### 1. Autopilot ya no rechaza `godmode` con un `ValueError`

Archivo:

```txt
backend/app/ai_workflows/bot_autopilot/schemas.py
```

Comportamiento final:

- Si llega `intensity: "godmode"` y `AI_ENABLE_GODMODE=false`, el backend normaliza:
  - `requested_intensity = "godmode"`
  - `intensity/effective_intensity = "savage"`
  - `safety_warnings += ["godmode_disabled_downgraded_to_savage"]`
- Si llega `auto_apply=true`, el backend normaliza:
  - `auto_apply = false`
  - `safety_warnings += ["auto_apply_disabled_for_autopilot_start"]`
- Si llega una intensidad desconocida, se normaliza a:
  - `intensity/effective_intensity = "balanced"`
  - `safety_warnings += ["invalid_intensity_downgraded_to_balanced"]`

### 2. El workflow usa siempre `effective_intensity`

Archivo:

```txt
backend/app/ai_workflows/bot_autopilot/service.py
```

El run se crea y ejecuta con la intensidad efectiva segura. El valor pedido por el cliente se conserva solo para auditoría.

### 3. El renderer global de errores quedó JSON-safe

Archivo:

```txt
backend/app/errors.py
```

`RequestValidationError.errors()` pasa por `_json_safe()` antes de ir a `JSONResponse`. Si Pydantic vuelve a incluir `ctx.error = ValueError(...)`, se convierte a string y no rompe el render del error.

### 4. Frontend reforzado

Archivos:

```txt
frontend/features/ai-command-center/AiCommandCenter.tsx
frontend/features/ai-command-center/types.ts
```

El frontend:
- degrada `godmode` a `savage` si `NEXT_PUBLIC_AI_ENABLE_GODMODE !== "true"`;
- fuerza `auto_apply: false`;
- muestra `safety_warnings` devueltos por backend.

## Validación ejecutada

Resultado: **11/11 PASS**

```txt
static: tenant isolation on workflow endpoints .............. PASS
static: background failures keep telemetry .................. PASS
static: apply recomputed and canary requires apply .......... PASS
static: persistence redacts/bounds json payloads ............ PASS
static: frontend stream and launch resilience ............... PASS
static: guided apply requires fresh dry run before creation . PASS
static: autopilot godmode normalized not rejected ........... PASS
static: global error renderer has last line defense ......... PASS
runtime: exact Render payload normalizes safely ............. PASS
runtime: RequestValidationError ctx.error is JSON-safe ...... PASS
syntax: all backend Python files parse ...................... PASS
```

## Payload exacto del log validado

```json
{
  "organization_id": "bootstrap_org_8218bd9d4e044dd58254aa2d55edae05",
  "bot_id": null,
  "user_description": "Vendedor de agentes operativos inteligentes, debe ayudar al cliente que necesita por que lo necesita, y de ser necesario debe actuar como su negocio.",
  "vertical_id": "waos bot",
  "subvertical": "waos bot",
  "primary_objective": "vender",
  "language": "es",
  "timezone": "America/Mexico_City",
  "intensity": "godmode",
  "auto_apply": false,
  "max_cost_usd": 12
}
```

Resultado validado:

```json
{
  "requested_intensity": "godmode",
  "effective_intensity": "savage",
  "intensity": "savage",
  "auto_apply": false,
  "safety_warnings": ["godmode_disabled_downgraded_to_savage"]
}
```

## Nota

No se cambió el contrato de lanzamiento seguro: `auto_apply` sigue bloqueado y human-gated. El fix evita que el inicio del Autopilot falle por una intensidad no habilitada y evita que cualquier error de validación vuelva a convertirse en un 500 por serialización.
