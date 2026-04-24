import type { WizardSubverticalProfile } from "@/features/bot-studio/domain/wizardTypes";
import type { CreateContextViewModel, CreateIntegrationsViewModel, CreateReviewViewModel } from "./createScreenTypes";

export function unique(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.map((item) => String(item || "").trim()).filter(Boolean)));
}

export function lines(value: string) {
  return unique(value.split(/\r?\n/).map((item) => item.trim()));
}

export function subverticalProfiles(state: Pick<CreateContextViewModel, "verticalProfile" | "blueprint">): WizardSubverticalProfile[] {
  if (state.verticalProfile?.subvertical_profiles?.length) {
    return state.verticalProfile.subvertical_profiles.map((item) => ({
      id: item.id || item.name,
      name: item.name,
      strength_score: item.strength_score,
      promise: item.promise,
      buyer: item.buyer,
      growth_motion: item.growth_motion,
      monetizes: item.monetizes,
      qualification_questions: item.qualification_questions,
      objections: item.objections,
      service_bundle: item.service_bundle,
      automation_priorities: item.automation_priorities,
      kpi_pack: item.kpi_pack,
      launch_assets: item.launch_assets,
      recommended_commands: item.recommended_commands,
    }));
  }
  if (state.blueprint?.selected_subvertical?.name) return [state.blueprint.selected_subvertical];
  return unique([
    state.blueprint?.selected_subvertical?.name,
    ...(state.blueprint?.profile?.recommended_subverticals || []),
    ...(state.blueprint?.profile?.subverticals || []),
  ]).map((name) => ({ id: name.toLowerCase().replace(/[^a-z0-9]+/g, "-"), name }));
}

export function recommendedIntegrations(state: Pick<CreateIntegrationsViewModel, "blueprint">) {
  return unique((state.blueprint?.setup?.wizard?.recommended_integrations || []).map((item) => item.name || item.provider || item.integration_key));
}

export function recommendedPlaybooks(state: Pick<CreateReviewViewModel, "blueprint">) {
  return unique((state.blueprint?.setup?.wizard?.recommended_playbooks || []).map((item) => item.label || item.key));
}
