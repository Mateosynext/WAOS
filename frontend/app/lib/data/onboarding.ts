import type { ActivationSummaryContract } from "../contracts/onboarding";
import { normalizeActivationSummary } from "../contracts/onboarding";
import { fetchRecord, orgQuery, selectedBotId } from "./shared";

export async function getActivationSummary(botId?: string): Promise<ActivationSummaryContract> {
  const query = await orgQuery();
  const currentBotId = await selectedBotId(botId);
  const botSuffix = currentBotId ? `&bot_id=${encodeURIComponent(currentBotId)}` : "";
  return fetchRecord(`/api/v1/onboarding/summary?${query}${botSuffix}`, { counts: {}, progress: {}, blockers: [], checklist: [], next_step: {}, feature_flags: {} }, normalizeActivationSummary);
}
