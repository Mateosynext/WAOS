type QueryStateInput = {
  wizardId?: string | null;
  botId?: string | null;
  organizationId?: string | null;
  verticalId?: string | null;
  subvertical?: string | null;
  primaryObjective?: string | null;
};

function routeParam(value: unknown) {
  const raw = String(value ?? "").trim();
  const normalized = raw.toLowerCase();
  if (!raw || raw === "-" || normalized === "null" || normalized === "undefined" || normalized === "nan") return "";
  return raw;
}

export function searchState(data: QueryStateInput) {
  return {
    wizard_id: routeParam(data.wizardId),
    bot: routeParam(data.botId),
    organization_id: routeParam(data.organizationId),
    vertical: routeParam(data.verticalId),
    subvertical: routeParam(data.subvertical),
    primary_objective: routeParam(data.primaryObjective),
  };
}

export function buildWizardAwareRouteQuery(data: QueryStateInput, wizardIdOverride?: string | null) {
  const override = routeParam(wizardIdOverride);
  return searchState({
    ...data,
    wizardId: override || routeParam(data.wizardId),
  });
}
