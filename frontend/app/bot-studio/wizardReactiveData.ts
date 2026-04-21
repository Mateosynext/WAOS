import type { VerticalProfileContract } from "../lib/contracts";
import type { WizardBlueprint, WizardMode } from "./wizard-types";

export const WIZARD_BLUEPRINT_ENDPOINT = "/api/onboarding/wizard/blueprint";
export const WIZARD_VERTICAL_PROFILE_ENDPOINT = "/api/onboarding/wizard/vertical-profile";

export type WizardReactiveSelectionRequest = {
  organizationId: string;
  verticalId: string;
  subvertical?: string | null;
  primaryObjective?: string | null;
  mode?: WizardMode;
  botId?: string | null;
};

export type WizardReactiveSelectionResult = {
  blueprint: WizardBlueprint | null;
  verticalProfile: VerticalProfileContract | null;
  errors: string[];
};

function appendIfPresent(params: URLSearchParams, key: string, value: unknown) {
  const rendered = String(value || "").trim();
  if (rendered) params.set(key, rendered);
}

export function buildWizardBlueprintParams(request: WizardReactiveSelectionRequest) {
  const params = new URLSearchParams();
  appendIfPresent(params, "organization_id", request.organizationId);
  appendIfPresent(params, "vertical_id", request.verticalId);
  appendIfPresent(params, "subvertical", request.subvertical);
  appendIfPresent(params, "primary_objective", request.primaryObjective);
  if (request.mode === "reconfigure") appendIfPresent(params, "bot_id", request.botId);
  return params;
}

export function buildWizardVerticalProfileParams(request: WizardReactiveSelectionRequest) {
  const params = new URLSearchParams();
  appendIfPresent(params, "organization_id", request.organizationId);
  appendIfPresent(params, "vertical", request.verticalId);
  appendIfPresent(params, "subvertical", request.subvertical);
  if (request.mode === "reconfigure") appendIfPresent(params, "bot_id", request.botId);
  return params;
}

export function buildWizardBlueprintUrl(request: WizardReactiveSelectionRequest) {
  return `${WIZARD_BLUEPRINT_ENDPOINT}?${buildWizardBlueprintParams(request).toString()}`;
}

export function buildWizardVerticalProfileUrl(request: WizardReactiveSelectionRequest) {
  return `${WIZARD_VERTICAL_PROFILE_ENDPOINT}?${buildWizardVerticalProfileParams(request).toString()}`;
}

async function requestWizardJson<T>(url: string, fallbackMessage: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, {
    method: "GET",
    cache: "no-store",
    credentials: "same-origin",
    signal,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof payload?.detail === "string" ? payload.detail : `${fallbackMessage} (${response.status}).`);
  }
  return payload as T;
}

export function fetchWizardBlueprint(request: WizardReactiveSelectionRequest, signal?: AbortSignal): Promise<WizardBlueprint> {
  return requestWizardJson<WizardBlueprint>(
    buildWizardBlueprintUrl(request),
    "La UI no pudo actualizar el blueprint",
    signal,
  );
}

export function fetchWizardVerticalProfile(request: WizardReactiveSelectionRequest, signal?: AbortSignal): Promise<VerticalProfileContract> {
  return requestWizardJson<VerticalProfileContract>(
    buildWizardVerticalProfileUrl(request),
    "La UI no pudo cargar el perfil vertical",
    signal,
  );
}

export async function loadWizardReactiveSelection(request: WizardReactiveSelectionRequest, signal?: AbortSignal): Promise<WizardReactiveSelectionResult> {
  const [blueprintResult, verticalProfileResult] = await Promise.allSettled([
    fetchWizardBlueprint(request, signal),
    fetchWizardVerticalProfile(request, signal),
  ]);

  const errors: string[] = [];

  if (blueprintResult.status === "rejected") {
    errors.push(blueprintResult.reason instanceof Error ? blueprintResult.reason.message : "No se pudo actualizar el blueprint.");
  }

  if (verticalProfileResult.status === "rejected") {
    errors.push(verticalProfileResult.reason instanceof Error ? verticalProfileResult.reason.message : "No se pudo cargar el perfil vertical.");
  }

  return {
    blueprint: blueprintResult.status === "fulfilled" ? blueprintResult.value : null,
    verticalProfile: verticalProfileResult.status === "fulfilled" ? verticalProfileResult.value : null,
    errors,
  };
}

export function joinWizardReactiveErrors(errors: string[], fallback: string) {
  return errors.length ? errors.join(" ") : fallback;
}


type LatestReactiveSelectionLoader = {
  load(request: WizardReactiveSelectionRequest): Promise<WizardReactiveSelectionResult | null>;
  cancel(): void;
};

export function createLatestWizardReactiveSelectionLoader(
  loader: (request: WizardReactiveSelectionRequest, signal?: AbortSignal) => Promise<WizardReactiveSelectionResult> = loadWizardReactiveSelection,
): LatestReactiveSelectionLoader {
  let controller: AbortController | null = null;
  let sequence = 0;
  return {
    async load(request: WizardReactiveSelectionRequest) {
      sequence += 1;
      const requestVersion = sequence;
      if (controller) controller.abort();
      controller = new AbortController();
      try {
        const result = await loader(request, controller.signal);
        if (requestVersion !== sequence) return null;
        return result;
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") return null;
        throw error;
      }
    },
    cancel() {
      if (controller) controller.abort();
      controller = null;
      sequence += 1;
    },
  };
}
