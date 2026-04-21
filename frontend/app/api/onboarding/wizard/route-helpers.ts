import { NextResponse } from "next/server";

const NO_STORE_HEADERS = { "Cache-Control": "no-store" };

const WIZARD_ERROR_MESSAGES: Record<string, string> = {
  dry_run_required: "Debes correr un dry run vigente antes de aplicar la reconfiguración.",
  dry_run_blocked: "El dry run actual sigue bloqueando el apply. Resuelve conflictos o vuelve a validar antes de aplicar.",
  wizard_revision_conflict: "Este wizard cambió mientras estabas guardando. Recarga el estado y vuelve a intentar.",
};

type WizardRouteErrorShape = {
  code?: unknown;
  status?: unknown;
  request_id?: unknown;
  requestId?: unknown;
  correlation_id?: unknown;
  correlationId?: unknown;
  error_type?: unknown;
  type?: unknown;
  detail?: unknown;
  message?: unknown;
};

function resolveWizardErrorCode(error: unknown, message: string) {
  const explicit = typeof (error as WizardRouteErrorShape | null)?.code === "string" ? String((error as WizardRouteErrorShape).code) : "";
  if (explicit) return explicit;
  return /^[a-z0-9_]+$/i.test(message) ? message : "";
}

function resolveWizardStatus(error: unknown) {
  const candidate = (error as WizardRouteErrorShape | null)?.status;
  return typeof candidate === "number" && Number.isFinite(candidate) && candidate > 0 ? candidate : 500;
}

function resolveWizardRequestMeta(error: unknown) {
  const value = error as WizardRouteErrorShape | null;
  const requestId = typeof value?.request_id === "string" ? value.request_id : typeof value?.requestId === "string" ? value.requestId : crypto.randomUUID();
  const correlationId = typeof value?.correlation_id === "string" ? value.correlation_id : typeof value?.correlationId === "string" ? value.correlationId : requestId;
  const errorType = typeof value?.error_type === "string" ? value.error_type : typeof value?.type === "string" ? value.type : error instanceof Error ? error.name : "WizardRouteError";
  return { requestId, correlationId, errorType };
}

function resolveWizardDetail(error: unknown, fallbackMessage: string, code: string) {
  const explicit = typeof (error as WizardRouteErrorShape | null)?.detail === "string" ? String((error as WizardRouteErrorShape).detail) : "";
  const rawMessage = explicit || (error instanceof Error ? error.message : fallbackMessage);
  if (code && WIZARD_ERROR_MESSAGES[code]) return WIZARD_ERROR_MESSAGES[code];
  return rawMessage || fallbackMessage;
}

export async function wizardRouteResponse<T>(load: () => Promise<T>, fallbackMessage: string) {
  try {
    const payload = await load();
    return NextResponse.json(payload, { headers: NO_STORE_HEADERS });
  } catch (error) {
    const tentativeMessage = error instanceof Error ? error.message : fallbackMessage;
    const code = resolveWizardErrorCode(error, tentativeMessage);
    const detail = resolveWizardDetail(error, fallbackMessage, code);
    const status = resolveWizardStatus(error);
    const { requestId, correlationId, errorType } = resolveWizardRequestMeta(error);
    return NextResponse.json(
      {
        detail,
        code: code || undefined,
        status,
        error_type: errorType,
        request_id: requestId,
        correlation_id: correlationId,
      },
      {
        status,
        headers: {
          ...NO_STORE_HEADERS,
          "X-Request-Id": requestId,
          "X-Correlation-Id": correlationId,
          "X-Error-Code": code || "unknown_error",
          "X-Error-Type": errorType,
        },
      },
    );
  }
}
