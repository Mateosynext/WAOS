import type { WizardMode } from "./wizard-types";
import type { WizardUiActiveStep } from "./wizardStepFlow";

export type WizardTelemetryStorage = Pick<Storage, "getItem" | "setItem">;

export type WizardTelemetryContext = {
  mode: WizardMode;
  organizationId?: string;
  botId?: string;
  wizardId?: string;
  verticalId?: string;
  subvertical?: string;
};

export type WizardTimelineEvent = {
  id: string;
  type: string;
  createdAt: string;
  payload?: Record<string, unknown>;
};

export type WizardAutosaveMetricResult = "success" | "error" | "ignored" | "skipped";

export type WizardAutosaveMetrics = {
  attempts: number;
  successes: number;
  errors: number;
  ignored: number;
  skipped: number;
  lastResult: WizardAutosaveMetricResult | null;
  lastDurationMs: number;
  maxDurationMs: number;
  totalDurationMs: number;
  averageDurationMs: number;
  lastStepCount: number;
  updatedAt: string;
};

export type WizardConsistencyRecoveryInput = {
  mode: WizardMode;
  activeStep: WizardUiActiveStep;
  persistedStep?: WizardUiActiveStep | null;
  clientAllowedStep?: WizardUiActiveStep | null;
  wizardStatus?: string | null;
  hasDryRunResult?: boolean;
  hasAppliedWizard?: boolean;
};

export type WizardConsistencyRecovery = {
  step: WizardUiActiveStep;
  reason: string;
  message: string;
};

export const WIZARD_ENTERPRISE_FLAGS = {
  enabled: process.env.NEXT_PUBLIC_WIZARD_ENTERPRISE_GUARDS !== "0",
  telemetryEnabled: process.env.NEXT_PUBLIC_WIZARD_ENTERPRISE_TELEMETRY !== "0",
  autoRecoveryEnabled: process.env.NEXT_PUBLIC_WIZARD_ENTERPRISE_AUTO_RECOVERY !== "0",
} as const;

const TIMELINE_PREFIX = "waos.bot_studio.timeline.v1";
const METRICS_PREFIX = "waos.bot_studio.autosave_metrics.v1";
const MAX_TIMELINE_EVENTS = 120;
const STEP_ORDER: WizardUiActiveStep[] = ["scope", "basics", "offer", "knowledge", "integrations", "review", "dry_run", "confirm", "simulate", "publish"];

function safeText(value: unknown): string {
  return String(value || "").trim();
}

function stepRank(step: WizardUiActiveStep | null | undefined): number {
  if (!step) return -1;
  return STEP_ORDER.indexOf(step);
}

function buildStableContextKey(context: WizardTelemetryContext): string {
  return [
    safeText(context.organizationId) || "org:none",
    safeText(context.botId) || "bot:none",
    safeText(context.wizardId) || "wizard:none",
    safeText(context.verticalId) || "vertical:none",
    safeText(context.subvertical) || "sub:none",
    safeText(context.mode) || "mode:none",
  ].join("|");
}

function storageKey(prefix: string, context: WizardTelemetryContext): string {
  return `${prefix}:${buildStableContextKey(context)}`;
}

function readJson<T>(storage: WizardTelemetryStorage | null | undefined, key: string, fallback: T): T {
  if (!storage) return fallback;
  try {
    const raw = storage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function writeJson(storage: WizardTelemetryStorage | null | undefined, key: string, value: unknown): void {
  if (!storage) return;
  try {
    storage.setItem(key, JSON.stringify(value));
  } catch {
    // no-op: telemetry must never break the wizard
  }
}

function nowIso(): string {
  return new Date().toISOString();
}


function stableClone(value: unknown): unknown {
  if (Array.isArray(value)) return value.map((item) => stableClone(item));
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return Object.keys(record)
      .sort((left, right) => left.localeCompare(right))
      .reduce<Record<string, unknown>>((acc, key) => {
        acc[key] = stableClone(record[key]);
        return acc;
      }, {});
  }
  return value;
}

export function stableSerializeWizardValue(value: unknown): string {
  return JSON.stringify(stableClone(value));
}

export function fingerprintWizardValue(value: unknown): string {
  const source = stableSerializeWizardValue(value);
  let hash = 2166136261;
  for (let index = 0; index < source.length; index += 1) {
    hash ^= source.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return `fnv1a_${(hash >>> 0).toString(16).padStart(8, "0")}`;
}

export function readWizardTimelineEvents(storage: WizardTelemetryStorage | null | undefined, context: WizardTelemetryContext): WizardTimelineEvent[] {
  return readJson<WizardTimelineEvent[]>(storage, storageKey(TIMELINE_PREFIX, context), []);
}

export function recordWizardTimelineEvent(
  storage: WizardTelemetryStorage | null | undefined,
  context: WizardTelemetryContext,
  event: { type: string; payload?: Record<string, unknown>; createdAt?: string },
): WizardTimelineEvent[] {
  if (!WIZARD_ENTERPRISE_FLAGS.enabled || !WIZARD_ENTERPRISE_FLAGS.telemetryEnabled) return [];
  const current = readWizardTimelineEvents(storage, context);
  const nextEvent: WizardTimelineEvent = {
    id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    type: safeText(event.type) || "wizard.event",
    createdAt: safeText(event.createdAt) || nowIso(),
    payload: event.payload || {},
  };
  const next = [...current, nextEvent].slice(-MAX_TIMELINE_EVENTS);
  writeJson(storage, storageKey(TIMELINE_PREFIX, context), next);
  return next;
}

export function readWizardAutosaveMetrics(storage: WizardTelemetryStorage | null | undefined, context: WizardTelemetryContext): WizardAutosaveMetrics {
  return readJson<WizardAutosaveMetrics>(storage, storageKey(METRICS_PREFIX, context), {
    attempts: 0,
    successes: 0,
    errors: 0,
    ignored: 0,
    skipped: 0,
    lastResult: null,
    lastDurationMs: 0,
    maxDurationMs: 0,
    totalDurationMs: 0,
    averageDurationMs: 0,
    lastStepCount: 0,
    updatedAt: "",
  });
}

export function recordWizardAutosaveMetric(
  storage: WizardTelemetryStorage | null | undefined,
  context: WizardTelemetryContext,
  metric: { result: WizardAutosaveMetricResult; durationMs?: number; stepCount?: number; createdAt?: string },
): WizardAutosaveMetrics {
  if (!WIZARD_ENTERPRISE_FLAGS.enabled || !WIZARD_ENTERPRISE_FLAGS.telemetryEnabled) {
    return readWizardAutosaveMetrics(storage, context);
  }
  const current = readWizardAutosaveMetrics(storage, context);
  const durationMs = Math.max(0, Math.round(Number(metric.durationMs || 0)));
  const next: WizardAutosaveMetrics = {
    ...current,
    attempts: current.attempts + 1,
    successes: current.successes + (metric.result === "success" ? 1 : 0),
    errors: current.errors + (metric.result === "error" ? 1 : 0),
    ignored: current.ignored + (metric.result === "ignored" ? 1 : 0),
    skipped: current.skipped + (metric.result === "skipped" ? 1 : 0),
    lastResult: metric.result,
    lastDurationMs: durationMs,
    maxDurationMs: Math.max(current.maxDurationMs, durationMs),
    totalDurationMs: current.totalDurationMs + durationMs,
    averageDurationMs: 0,
    lastStepCount: Math.max(0, Math.round(Number(metric.stepCount || 0))),
    updatedAt: safeText(metric.createdAt) || nowIso(),
  };
  next.averageDurationMs = next.attempts ? Math.round(next.totalDurationMs / next.attempts) : 0;
  writeJson(storage, storageKey(METRICS_PREFIX, context), next);
  return next;
}

export function deriveWizardConsistencyRecovery(input: WizardConsistencyRecoveryInput): WizardConsistencyRecovery | null {
  if (!WIZARD_ENTERPRISE_FLAGS.enabled || !WIZARD_ENTERPRISE_FLAGS.autoRecoveryEnabled) return null;

  const hasAppliedWizard = Boolean(input.hasAppliedWizard || safeText(input.wizardStatus).toLowerCase() === "applied");

  if (input.mode === "reconfigure") {
    if ((input.activeStep === "dry_run" || input.activeStep === "confirm") && !input.hasDryRunResult) {
      return {
        step: "review",
        reason: "missing_dry_run",
        message: "Se recuperó el wizard en review porque ya no existía un dry run válido.",
      };
    }
    if ((input.activeStep === "publish" || input.activeStep === "simulate") && !hasAppliedWizard) {
      return {
        step: "review",
        reason: "missing_apply",
        message: "Se recuperó el wizard en review porque todavía no había apply real.",
      };
    }
    return null;
  }

  if ((input.activeStep === "publish" || input.activeStep === "simulate") && !hasAppliedWizard) {
    const fallback = input.clientAllowedStep || input.persistedStep || "scope";
    return {
      step: fallback,
      reason: "missing_apply",
      message: "Se recuperó el wizard al último paso seguro porque todavía no existía apply real.",
    };
  }

  if (input.persistedStep && stepRank(input.activeStep) > stepRank(input.persistedStep)) {
    return {
      step: input.persistedStep,
      reason: "ahead_of_persisted_progress",
      message: "Se recuperó el wizard al último paso persistido para evitar brincar más allá del progreso real.",
    };
  }

  if (input.clientAllowedStep && input.clientAllowedStep !== input.activeStep && stepRank(input.clientAllowedStep) < stepRank(input.activeStep)) {
    return {
      step: input.clientAllowedStep,
      reason: "blocked_by_prerequisites",
      message: "Se recuperó el wizard al último paso coherente con los prerrequisitos ya llenos.",
    };
  }

  return null;
}
