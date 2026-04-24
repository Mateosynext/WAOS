import { safeText } from "@/app/lib/ui";

type QueryStateInput = {
  wizardId?: string | null;
  botId?: string | null;
  organizationId?: string | null;
  verticalId?: string | null;
  subvertical?: string | null;
  primaryObjective?: string | null;
};

export function searchState(data: QueryStateInput) {
  return {
    wizard_id: safeText(data.wizardId),
    bot: safeText(data.botId),
    organization_id: safeText(data.organizationId),
    vertical: safeText(data.verticalId),
    subvertical: safeText(data.subvertical),
    primary_objective: safeText(data.primaryObjective),
  };
}

export function buildWizardAwareRouteQuery(data: QueryStateInput, wizardIdOverride?: string | null) {
  return searchState({ ...data, wizardId: safeText(wizardIdOverride, safeText(data.wizardId)) });
}
