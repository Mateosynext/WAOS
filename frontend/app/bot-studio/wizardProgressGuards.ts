import type { CreateRouteStep, RouteStep } from "./flowConfig";
import type { WizardInstance, WizardValidationSnapshot } from "./wizard-types";

const CREATE_ROUTE_ORDER: CreateRouteStep[] = ["context", "identity", "offer", "knowledge", "integrations", "review", "validate", "apply", "success"];

const BACKEND_STEP_TO_ROUTE: Record<string, CreateRouteStep> = {
  vertical_fit: "context",
  business_basics: "identity",
  catalog_offer: "offer",
  knowledge_seed: "knowledge",
  integrations_rules: "integrations",
  launch_review: "review",
};

const REQUIRED_FIELD_MESSAGES: Record<CreateRouteStep, { title: string; detail: string }> = {
  context: {
    title: "Contexto incompleto",
    detail: "Confirma organización, industria y tipo de operación antes de continuar.",
  },
  identity: {
    title: "Identidad guardada parcialmente",
    detail: "Faltan nombre del negocio, nombre del bot, tono, idioma o zona horaria para cerrar este paso.",
  },
  offer: {
    title: "Oferta guardada parcialmente",
    detail: "Falta al menos un servicio y un CTA principal para avanzar a knowledge.",
  },
  knowledge: {
    title: "Knowledge guardado parcialmente",
    detail: "Faltan FAQs válidas, políticas o fuentes de conocimiento para cerrar este paso.",
  },
  integrations: {
    title: "Integraciones guardadas parcialmente",
    detail: "Falta elegir integraciones o definir cuándo debe escalar a humano.",
  },
  review: {
    title: "Review todavía no quedó listo",
    detail: "El backend todavía no dejó el wizard preparado para validar. Revisa los pasos pendientes.",
  },
  validate: {
    title: "Validación pendiente",
    detail: "Corre un dry run fresco y revisa el gate antes de pasar a apply.",
  },
  apply: {
    title: "Apply bloqueado",
    detail: "El wizard todavía no tiene una validación lista para aplicar.",
  },
  success: {
    title: "Resultado listo",
    detail: "El flujo ya terminó.",
  },
};

function unique(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.map((item) => String(item || "").trim()).filter(Boolean)));
}

function textBlock(value: unknown) {
  return unique(String(value || "").split(/\r?\n/).map((item) => item.trim()));
}

function faqEntries(value: unknown) {
  return String(value || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [question, ...rest] = line.split("|");
      return { q: String(question || "").trim(), a: rest.join("|").trim() };
    })
    .filter((item) => item.q && item.a);
}

function routeRank(step: RouteStep | CreateRouteStep | null | undefined) {
  return CREATE_ROUTE_ORDER.indexOf((step || "") as CreateRouteStep);
}

export function resolveCreateBlockingRoute(wizard?: WizardInstance | null): CreateRouteStep | null {
  const diagnosticsStep = String(wizard?.diagnostics?.first_incomplete_required_step || "").trim().toLowerCase();
  const currentStep = String(wizard?.current_step || "").trim().toLowerCase();
  return BACKEND_STEP_TO_ROUTE[diagnosticsStep] || BACKEND_STEP_TO_ROUTE[currentStep] || null;
}

export function getCreateRouteMessage(step: CreateRouteStep) {
  return REQUIRED_FIELD_MESSAGES[step] || REQUIRED_FIELD_MESSAGES.review;
}

export function getCreateClientIncompleteMessage(step: CreateRouteStep) {
  return getCreateRouteMessage(step);
}

export function isCreateStepClientReady(step: RouteStep, state: Record<string, unknown>) {
  if (step === "context") return Boolean(state.selectedOrganizationId && state.selectedVerticalId && state.selectedSubvertical);
  if (step === "identity") return Boolean(state.businessName && state.botName && state.tone && state.language && state.timezone);
  if (step === "offer") return textBlock(state.servicesText).length > 0 && textBlock(state.primaryCtasText).length > 0;
  if (step === "knowledge") return faqEntries(state.faqText).length > 0 && textBlock(state.policiesText).length > 0 && textBlock(state.knowledgeSourcesText).length > 0;
  if (step === "integrations") return Array.isArray(state.selectedIntegrationKeys) && state.selectedIntegrationKeys.length > 0 && textBlock(state.escalateWhenText).length > 0;
  return true;
}

export function canAdvanceAfterCreateSave(currentStep: CreateRouteStep, saved: WizardInstance) {
  if (currentStep === "review") return { ok: true as const, blockingRoute: null };
  const blockingRoute = resolveCreateBlockingRoute(saved);
  const nextRank = routeRank(nextCreateRoute(currentStep));
  const blockingRank = routeRank(blockingRoute);
  if (!blockingRoute || nextRank < 0 || blockingRank >= nextRank) {
    return { ok: true as const, blockingRoute: null };
  }
  return { ok: false as const, blockingRoute };
}

export function nextCreateRoute(step: CreateRouteStep): CreateRouteStep | null {
  const index = CREATE_ROUTE_ORDER.indexOf(step);
  if (index < 0 || index >= CREATE_ROUTE_ORDER.length - 1) return null;
  return CREATE_ROUTE_ORDER[index + 1] || null;
}

export function isSnapshotApplyReady(snapshot?: WizardValidationSnapshot | null) {
  if (!snapshot) return false;
  if (snapshot.apply_ready === true) return true;
  return String(snapshot.gate?.status || "").trim().toLowerCase() === "green";
}
