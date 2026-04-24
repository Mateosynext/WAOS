import type { WizardError, WizardIssue } from "../domain/wizardTypes";

export type WizardRequestOptions = {
  signal?: AbortSignal;
  expectedRevision?: number | null;
  timeoutMs?: number;
};

export type WizardClientOptions = {
  fetcher?: typeof fetch;
  defaultInit?: RequestInit;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function readMessage(payload: unknown, fallback: string) {
  if (!isRecord(payload)) return fallback;
  const detail = payload.detail;
  const message = payload.message;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (typeof message === "string" && message.trim()) return message;
  return fallback;
}

function readStringList(value: unknown) {
  return Array.isArray(value) ? value.map((item) => String(item || "").trim()).filter(Boolean) : [];
}

function readIssues(value: unknown): WizardIssue[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => {
    const record = isRecord(item) ? item : {};
    return {
      key: typeof record.key === "string" ? record.key : undefined,
      field: typeof record.field === "string" ? record.field : undefined,
      message: typeof record.message === "string" ? record.message : readMessage(record, "Validacion pendiente."),
      severity: record.severity === "warning" || record.severity === "error" || record.severity === "blocking" ? record.severity : undefined,
    };
  });
}

export function normalizeWizardError(error: unknown): WizardError {
  if (isWizardError(error)) return error;
  if (error instanceof DOMException && error.name === "AbortError") return { type: "network_error", message: "La solicitud fue cancelada." };
  if (error instanceof TypeError) return { type: "network_error", message: error.message || "No se pudo conectar con el wizard." };
  if (error instanceof Error) return { type: "network_error", message: error.message || "No se pudo completar la solicitud." };
  return { type: "network_error", message: "No se pudo completar la solicitud." };
}

export function isWizardError(error: unknown): error is WizardError {
  return isRecord(error) && typeof error.type === "string" && ["network_error", "revision_conflict", "validation_failed", "partial_failure"].includes(error.type);
}

export function wizardErrorToMessage(error: WizardError): string {
  if (error.type === "revision_conflict") return `La revision cambio en servidor (${error.serverRevision}). Vuelve a validar antes de aplicar.`;
  if (error.type === "validation_failed") return error.issues.length ? error.issues.map((issue) => issue.message).join(" ") : "La validacion fallo.";
  if (error.type === "partial_failure") return `Apply parcial: completados ${error.completed.length}, fallidos ${error.failed.length}.`;
  return error.message;
}

function mergeRequestHeaders(base?: HeadersInit, override?: HeadersInit) {
  const headers = new Headers(base);
  const next = new Headers(override);
  next.forEach((value, key) => headers.set(key, value));
  return headers;
}

async function readJson(response: Response) {
  const text = await response.text().catch(() => "");
  if (!text) return {};
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return { detail: text };
  }
}

export function parseWizardError(status: number, payload: unknown): WizardError {
  const record = isRecord(payload) ? payload : {};
  const explicitType = typeof record.type === "string" ? record.type : typeof record.error_type === "string" ? record.error_type : "";
  const serverRevision = Number(record.serverRevision ?? record.server_revision ?? record.current_revision ?? 0);
  const issues = readIssues(record.issues ?? record.errors ?? record.validation_issues);
  const completed = readStringList(record.completed ?? record.completed_steps ?? record.completed_domains);
  const failed = readStringList(record.failed ?? record.failed_steps ?? record.failed_domains);

  if (status === 409 || explicitType === "revision_conflict") {
    return { type: "revision_conflict", serverRevision: Number.isFinite(serverRevision) && serverRevision > 0 ? serverRevision : 0 };
  }
  if (status === 422 || explicitType === "validation_failed") {
    return { type: "validation_failed", issues };
  }
  if (status === 207 || explicitType === "partial_failure" || failed.length > 0) {
    return { type: "partial_failure", completed, failed };
  }
  return { type: "network_error", message: readMessage(payload, `La solicitud fallo (${status}).`) };
}

export async function requestWizardJson<T>(url: string, init: RequestInit = {}, options: WizardClientOptions = {}): Promise<T> {
  const fetcher = options.fetcher || fetch;
  let response: Response;
  try {
    response = await fetcher(url, {
      cache: "no-store",
      credentials: "same-origin",
      ...options.defaultInit,
      ...init,
      headers: mergeRequestHeaders(options.defaultInit?.headers, init.headers),
    });
  } catch (error) {
    throw normalizeWizardError(error);
  }
  const payload = await readJson(response);
  if (!response.ok) throw parseWizardError(response.status, payload);
  return payload as T;
}
