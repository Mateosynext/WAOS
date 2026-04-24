import type { CreateRouteStep, ReconfigureRouteStep, RouteStep } from "./flowConfig";
import type { WizardInstance, WizardMode, WizardValidationSnapshot } from "./wizardTypes";

const CREATE_ROUTE_ORDER: CreateRouteStep[] = ["context", "identity", "offer", "knowledge", "integrations", "review", "validate", "apply", "success"];
const RECONFIGURE_ROUTE_ORDER: ReconfigureRouteStep[] = ["select", "diff", "dry-run", "confirm", "result"];

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
    detail: "El wizard todavía no tiene una validación fresca para la revisión actual.",
  },
  success: {
    title: "Resultado listo",
    detail: "El flujo ya terminó.",
  },
};

const RECONFIGURE_ROUTE_MESSAGES: Record<ReconfigureRouteStep, { title: string; detail: string }> = {
  select: {
    title: "Selecciona un bot",
    detail: "La reconfiguración necesita un bot explícito antes de seguir.",
  },
  diff: {
    title: "Diff no disponible",
    detail: "Selecciona y prepara un bot antes de abrir el diff.",
  },
  "dry-run": {
    title: "Dry run bloqueado",
    detail: "Primero prepara el diff del bot seleccionado.",
  },
  confirm: {
    title: "Confirmación bloqueada",
    detail: "Necesitas un dry run verde y fresco para esta revisión antes de confirmar.",
  },
  result: {
    title: "Resultado no disponible",
    detail: "El resultado solo se puede abrir después de un apply real.",
  },
};

export type WizardValidationFreshness = {
  wizardRevision?: number | null;
  validatedWizardRevision?: number | null;
};

export type WizardRouteGuardResult =
  | { ok: true }
  | { ok: false; blockingRoute: RouteStep; title: string; detail: string; reason: string };

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

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

function createRouteRank(step: RouteStep | CreateRouteStep | null | undefined) {
  return CREATE_ROUTE_ORDER.indexOf((step || "") as CreateRouteStep);
}

function reconfigureRouteRank(step: RouteStep | ReconfigureRouteStep | null | undefined) {
  return RECONFIGURE_ROUTE_ORDER.indexOf((step || "") as ReconfigureRouteStep);
}

function isWizardApplied(wizard?: WizardInstance | null, hasAppliedWizard?: boolean) {
  return Boolean(hasAppliedWizard || String(wizard?.status || "").trim().toLowerCase() === "applied" || wizard?.applied_at);
}

export function resolveCreateBlockingRoute(wizard?: WizardInstance | null): CreateRouteStep | null {
  const diagnosticsStep = String(wizard?.diagnostics?.first_incomplete_required_step || "").trim().toLowerCase();
  const currentStep = String(wizard?.current_step || "").trim().toLowerCase();
  return BACKEND_STEP_TO_ROUTE[diagnosticsStep] || BACKEND_STEP_TO_ROUTE[currentStep] || null;
}

export function getCreateRouteMessage(step: CreateRouteStep) {
  return REQUIRED_FIELD_MESSAGES[step] || REQUIRED_FIELD_MESSAGES.review;
}

export function getReconfigureRouteMessage(step: ReconfigureRouteStep) {
  return RECONFIGURE_ROUTE_MESSAGES[step] || RECONFIGURE_ROUTE_MESSAGES.select;
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
  const nextRank = createRouteRank(nextCreateRoute(currentStep));
  const blockingRank = createRouteRank(blockingRoute);
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

export function getCurrentWizardRevision(wizard?: WizardInstance | null): number | null {
  return typeof wizard?.wizard_revision === "number" ? wizard.wizard_revision : null;
}

export function getValidatedWizardRevisionFromWizard(wizard?: WizardInstance | null): number | null {
  const validation = asRecord(asRecord(wizard?.answers).dry_run_validation);
  const revision = Number(validation.wizard_revision || 0);
  return Number.isFinite(revision) && revision > 0 ? revision : null;
}

export function isWizardValidationFresh(freshness?: WizardValidationFreshness | null) {
  if (!freshness) return false;
  if (typeof freshness.wizardRevision !== "number") return false;
  if (typeof freshness.validatedWizardRevision !== "number") return false;
  return freshness.validatedWizardRevision === freshness.wizardRevision;
}

export function isSnapshotApplyReady(snapshot?: WizardValidationSnapshot | null, freshness?: WizardValidationFreshness | null) {
  if (!snapshot) return false;
  if (freshness && !isWizardValidationFresh(freshness)) return false;
  if (snapshot.apply_ready === true) return true;
  return String(snapshot.gate?.status || "").trim().toLowerCase() === "green";
}

function createPrerequisiteSteps(step: CreateRouteStep): CreateRouteStep[] {
  const rank = CREATE_ROUTE_ORDER.indexOf(step);
  return rank <= 0 ? [] : CREATE_ROUTE_ORDER.slice(0, rank).filter((item) => ["context", "identity", "offer", "knowledge", "integrations"].includes(item));
}

function firstIncompleteCreatePrerequisite(step: CreateRouteStep, state: Record<string, unknown>): CreateRouteStep | null {
  return createPrerequisiteSteps(step).find((candidate) => !isCreateStepClientReady(candidate, state)) || null;
}

export function canEnterCreateRoute(args: {
  routeStep: CreateRouteStep;
  state: Record<string, unknown>;
  wizard?: WizardInstance | null;
  snapshot?: WizardValidationSnapshot | null;
  validatedWizardRevision?: number | null;
  hasAppliedWizard?: boolean;
}): WizardRouteGuardResult {
  const incompleteClientStep = firstIncompleteCreatePrerequisite(args.routeStep, args.state);
  if (incompleteClientStep) {
    const message = getCreateRouteMessage(incompleteClientStep);
    return { ok: false, blockingRoute: incompleteClientStep, title: message.title, detail: message.detail, reason: "missing_create_prerequisite" };
  }

  if (["validate", "apply", "success"].includes(args.routeStep) && !args.wizard?.id && !args.state.wizardId) {
    const message = getCreateRouteMessage("review");
    return { ok: false, blockingRoute: "review", title: message.title, detail: "Guarda el review antes de abrir validación, apply o resultado.", reason: "missing_wizard" };
  }

  if (args.routeStep === "apply") {
    const wizardRevision = getCurrentWizardRevision(args.wizard) ?? (typeof args.state.wizardRevision === "number" ? args.state.wizardRevision as number : null);
    const fresh = { wizardRevision, validatedWizardRevision: args.validatedWizardRevision ?? getValidatedWizardRevisionFromWizard(args.wizard) };
    if (!isSnapshotApplyReady(args.snapshot || args.wizard?.validation_snapshot || null, fresh)) {
      const message = getCreateRouteMessage("apply");
      return { ok: false, blockingRoute: "validate", title: message.title, detail: message.detail, reason: "missing_fresh_validation" };
    }
  }

  if (args.routeStep === "success" && !isWizardApplied(args.wizard, args.hasAppliedWizard)) {
    const message = getCreateRouteMessage("apply");
    return { ok: false, blockingRoute: "apply", title: message.title, detail: "El resultado se desbloquea únicamente después de aplicar el wizard.", reason: "missing_apply" };
  }

  return { ok: true };
}

export function canEnterReconfigureRoute(args: {
  routeStep: ReconfigureRouteStep;
  selectedBotId?: string | null;
  wizard?: WizardInstance | null;
  snapshot?: WizardValidationSnapshot | null;
  validatedWizardRevision?: number | null;
  hasAppliedWizard?: boolean;
}): WizardRouteGuardResult {
  const hasBot = Boolean(String(args.selectedBotId || args.wizard?.bot_id || "").trim());
  if (args.routeStep !== "select" && !hasBot) {
    const message = getReconfigureRouteMessage("select");
    return { ok: false, blockingRoute: "select", title: message.title, detail: message.detail, reason: "missing_bot" };
  }

  if (["dry-run", "confirm", "result"].includes(args.routeStep) && !args.wizard?.id) {
    const message = getReconfigureRouteMessage("diff");
    return { ok: false, blockingRoute: "diff", title: message.title, detail: message.detail, reason: "missing_wizard" };
  }

  if (args.routeStep === "confirm") {
    const fresh = { wizardRevision: getCurrentWizardRevision(args.wizard), validatedWizardRevision: args.validatedWizardRevision ?? getValidatedWizardRevisionFromWizard(args.wizard) };
    if (!isSnapshotApplyReady(args.snapshot || args.wizard?.validation_snapshot || null, fresh)) {
      const message = getReconfigureRouteMessage("confirm");
      return { ok: false, blockingRoute: "dry-run", title: message.title, detail: message.detail, reason: "missing_fresh_validation" };
    }
  }

  if (args.routeStep === "result" && !isWizardApplied(args.wizard, args.hasAppliedWizard)) {
    const message = getReconfigureRouteMessage("result");
    return { ok: false, blockingRoute: "confirm", title: message.title, detail: message.detail, reason: "missing_apply" };
  }

  return { ok: true };
}

export function canEnterWizardRoute(args: {
  mode: WizardMode;
  routeStep: RouteStep;
  state?: Record<string, unknown>;
  selectedBotId?: string | null;
  wizard?: WizardInstance | null;
  snapshot?: WizardValidationSnapshot | null;
  validatedWizardRevision?: number | null;
  hasAppliedWizard?: boolean;
}): WizardRouteGuardResult {
  if (args.mode === "reconfigure") {
    return canEnterReconfigureRoute({
      routeStep: args.routeStep as ReconfigureRouteStep,
      selectedBotId: args.selectedBotId,
      wizard: args.wizard,
      snapshot: args.snapshot,
      validatedWizardRevision: args.validatedWizardRevision,
      hasAppliedWizard: args.hasAppliedWizard,
    });
  }
  return canEnterCreateRoute({
    routeStep: args.routeStep as CreateRouteStep,
    state: args.state || {},
    wizard: args.wizard,
    snapshot: args.snapshot,
    validatedWizardRevision: args.validatedWizardRevision,
    hasAppliedWizard: args.hasAppliedWizard,
  });
}

export function earlierRoute(mode: WizardMode, left: RouteStep, right: RouteStep): RouteStep {
  if (mode === "reconfigure") return reconfigureRouteRank(left) <= reconfigureRouteRank(right) ? left : right;
  return createRouteRank(left) <= createRouteRank(right) ? left : right;
}
