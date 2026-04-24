import type { WizardMode } from "./wizardTypes";

export type CreateRouteStep = "context" | "identity" | "offer" | "knowledge" | "integrations" | "review" | "validate" | "apply" | "success";
export type ReconfigureRouteStep = "select" | "diff" | "dry-run" | "confirm" | "result";
export type RouteStep = CreateRouteStep | ReconfigureRouteStep;
export type FlowStepDefinition = { key: RouteStep; label: string; description: string; mode: WizardMode };

export const CREATE_FLOW_STEPS: FlowStepDefinition[] = [
  { key: "context", label: "Contexto", description: "Define organización, industria, subvertical y objetivo.", mode: "create" },
  { key: "identity", label: "Identidad", description: "Configura nombre, tono y datos base del bot.", mode: "create" },
  { key: "offer", label: "Oferta", description: "Captura servicios, ofertas y CTA principales.", mode: "create" },
  { key: "knowledge", label: "Knowledge", description: "Separa FAQs, políticas y fuentes de conocimiento.", mode: "create" },
  { key: "integrations", label: "Integraciones", description: "Define integraciones, handoff y reglas operativas.", mode: "create" },
  { key: "review", label: "Review", description: "Revisa el setup completo antes de validar.", mode: "create" },
  { key: "validate", label: "Validación", description: "Ejecuta dry run y checklist de salida.", mode: "create" },
  { key: "apply", label: "Apply", description: "Confirma y aplica el cambio operativo.", mode: "create" },
  { key: "success", label: "Resultado", description: "Cierra el flujo y decide la siguiente acción.", mode: "create" },
];

export const RECONFIGURE_FLOW_STEPS: FlowStepDefinition[] = [
  { key: "select", label: "Seleccionar", description: "Elige qué bot se va a reconfigurar.", mode: "reconfigure" },
  { key: "diff", label: "Diff", description: "Aísla el cambio propuesto frente al estado actual.", mode: "reconfigure" },
  { key: "dry-run", label: "Dry run", description: "Valida el impacto antes de confirmar.", mode: "reconfigure" },
  { key: "confirm", label: "Confirmar", description: "Confirma la reconfiguración a aplicar.", mode: "reconfigure" },
  { key: "result", label: "Resultado", description: "Entrega el resultado y siguientes acciones.", mode: "reconfigure" },
];

const LEGACY_STEP_MAP: Record<string, RouteStep> = {
  scope: "context", basics: "identity", offer: "offer", knowledge: "knowledge", integrations: "integrations", review: "review", dry_run: "validate", confirm: "apply", publish: "success", simulate: "validate",
};

export function getFlowSteps(mode: WizardMode) { return mode === "reconfigure" ? RECONFIGURE_FLOW_STEPS : CREATE_FLOW_STEPS; }
export function getFirstRouteStep(mode: WizardMode): RouteStep { return getFlowSteps(mode)[0]?.key || (mode === "reconfigure" ? "select" : "context"); }
export function normalizeRouteStep(mode: WizardMode, value: string | null | undefined): RouteStep | null {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized) return null;
  const allowed = new Set(getFlowSteps(mode).map((item) => item.key));
  if (allowed.has(normalized as RouteStep)) return normalized as RouteStep;
  const legacy = LEGACY_STEP_MAP[normalized];
  return legacy && allowed.has(legacy) ? legacy : null;
}
export function getStepMeta(mode: WizardMode, step: RouteStep) { return getFlowSteps(mode).find((item) => item.key === step) || getFlowSteps(mode)[0]; }
export function getPreviousRouteStep(mode: WizardMode, step: RouteStep): RouteStep | null { const s=getFlowSteps(mode); const i=s.findIndex((item)=>item.key===step); return i>0 ? s[i-1]?.key || null : null; }
export function getNextRouteStep(mode: WizardMode, step: RouteStep): RouteStep | null { const s=getFlowSteps(mode); const i=s.findIndex((item)=>item.key===step); return i>=0 && i<s.length-1 ? s[i+1]?.key || null : null; }
export function cleanRouteSearchValue(value: unknown) {
  const raw = String(value ?? "").trim();
  const normalized = raw.toLowerCase();
  return raw && raw !== "-" && normalized !== "null" && normalized !== "undefined" && normalized !== "nan" ? raw : "";
}

export function buildBotStudioHref(mode: WizardMode, step: RouteStep, searchParams?: Record<string,string|null|undefined>) {
  const params = new URLSearchParams();
  Object.entries(searchParams || {}).forEach(([key, value]) => {
    const rendered = cleanRouteSearchValue(value);
    if (rendered) params.set(key, rendered);
  });
  const query = params.toString();
  return `/bot-studio/${mode}/${step}${query ? `?${query}` : ""}`;
}
