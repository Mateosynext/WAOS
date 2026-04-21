import type {
  ClientOperationsAlertContract,
  ClientOperationsAvailabilityContract,
  ClientOperationsMetricsContract,
  ClientOperationsSummaryContract,
} from "../contracts/portal";
import {
  normalizeClientOperationsAlert,
  normalizeClientOperationsAvailability,
  normalizeClientOperationsMetrics,
  normalizeClientOperationsSummary,
} from "../contracts/portal";
import { fetchArray, fetchRecord } from "./shared";

export type ClientOperationsData = {
  summary: ClientOperationsSummaryContract;
  availability: ClientOperationsAvailabilityContract;
  metrics: ClientOperationsMetricsContract;
  alerts: ClientOperationsAlertContract[];
};

export async function getClientOperationsData(organizationId: string, botId: string): Promise<ClientOperationsData> {
  const query = `organization_id=${encodeURIComponent(organizationId)}&bot_id=${encodeURIComponent(botId)}`;
  const summaryEndpoint = `/api/v1/client/operations/summary?${query}`;
  const availabilityEndpoint = `/api/v1/client/operations/availability?${query}&day=today`;
  const metricsEndpoint = `/api/v1/client/operations/metrics?${query}&window_days=7`;
  const alertsEndpoint = `/api/v1/client/operations/alerts?${query}`;

  const [summary, availability, metrics, alerts] = await Promise.all([
    fetchRecord(summaryEndpoint, { bot: {}, counts: {}, recent_commands: [], authorized_numbers: [], scheduled_actions: [], upcoming_appointments: [] }, normalizeClientOperationsSummary),
    fetchRecord(availabilityEndpoint, { summary: {}, appointments: [], overrides: [] }, normalizeClientOperationsAvailability),
    fetchRecord(metricsEndpoint, { summary: {}, intents: [], statuses: [] }, normalizeClientOperationsMetrics),
    fetchArray(alertsEndpoint, [], normalizeClientOperationsAlert),
  ]);

  return { summary, availability, metrics, alerts };
}
