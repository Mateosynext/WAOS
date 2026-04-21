import type { DeadLettersContract, IntegrationCenterContract, IntegrationContract, IntegrationEventContract, IntegrationObservabilityContract, RuntimeCallbackContract, SchedulerOverviewContract, SecretContract, SyncRunContract } from "../contracts/integrations";
import { normalizeDeadLetters, normalizeIntegration, normalizeIntegrationCenter, normalizeIntegrationEvent, normalizeIntegrationObservability, normalizeRuntimeCallback, normalizeSchedulerOverview, normalizeSecret, normalizeSyncRun } from "../contracts/integrations";
import type { RateLimitPolicyContract, SecurityPolicyContract, SSOProviderContract } from "../contracts/auth";
import { normalizeRateLimitPolicy, normalizeSecurityPolicy, normalizeSSOProvider } from "../contracts/auth";
import { apiFetchOrDefault } from "../api";
import { fetchArray, fetchRecord, orgQuery } from "./shared";

export async function getIntegrations(): Promise<IntegrationContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/integrations?${query}`, [], normalizeIntegration);
}

export async function getSecrets(): Promise<SecretContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/secrets?${query}`, [], normalizeSecret);
}

export async function getIntegrationCenter(): Promise<IntegrationCenterContract> {
  const query = await orgQuery();
  return fetchRecord(`/api/v1/integrations/center?${query}`, { summary: {}, integrations: [], observability: {}, recent_sync_runs: [], failed_receipts: [], retry_hotspots: [], dependency_map: [] }, normalizeIntegrationCenter);
}

export async function getScheduler(): Promise<SchedulerOverviewContract> {
  const query = await orgQuery();
  return fetchRecord(`/api/v1/runtime/scheduler?${query}`, { due_now: 0, next_job: null, counts: [], stale_locks: 0, integration_due_now: 0, next_integration: null, integration_retries: 0 }, normalizeSchedulerOverview);
}

export async function getRateLimits(): Promise<RateLimitPolicyContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/rate-limits?${query}`, [], normalizeRateLimitPolicy);
}

export async function getAccessMatrix() {
  return apiFetchOrDefault<Record<string, unknown>>(`/api/v1/access/matrix`, { current_user_role: "unknown", roles: {} });
}

export async function getSecurityPolicy(): Promise<SecurityPolicyContract> {
  const query = await orgQuery();
  return fetchRecord(`/api/v1/security/policies?${query}`, { organization_id: null, require_mfa: false, require_sso: false, session_ttl_minutes: 0, webhook_signature_required: false, strict_idempotency: false, ip_allowlist: [], allowed_origins: [] }, normalizeSecurityPolicy);
}

export async function getSSOProviders(): Promise<SSOProviderContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/security/sso?${query}`, [], normalizeSSOProvider);
}

export async function getRuntimeCallbacks(): Promise<RuntimeCallbackContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/runtime/callbacks?${query}`, [], normalizeRuntimeCallback);
}

export async function getDeadLetters(): Promise<DeadLettersContract> {
  const query = await orgQuery();
  return fetchRecord(`/api/v1/operations/dead-letters?${query}`, { jobs: [], outbox: [] }, normalizeDeadLetters);
}

export async function getIntegrationSyncRuns(): Promise<SyncRunContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/integrations/sync-runs?${query}`, [], normalizeSyncRun);
}

export async function getIntegrationEvents(): Promise<IntegrationEventContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/integrations/events?${query}`, [], normalizeIntegrationEvent);
}

export async function getIntegrationObservability(): Promise<IntegrationObservabilityContract> {
  const query = await orgQuery();
  return fetchRecord(`/api/v1/integrations/observability?${query}`, { totals: {}, latest_error: null, providers: [], recent: [] }, normalizeIntegrationObservability);
}

export async function getGoogleCalendars(integrationId: string | null | undefined): Promise<Array<Record<string, unknown>>> {
  if (!integrationId) return [];
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/integrations/${integrationId}/oauth/google/calendars`, []);
}

export async function getSystemStatus() {
  return apiFetchOrDefault<Record<string, unknown>>(`/api/v1/system/status`, {
    status: "unknown",
    environment: "development",
    version: "-",
    checks: [],
    launch_checks: [],
    config: {},
  });
}

export async function getHealth() {
  return apiFetchOrDefault<Record<string, unknown>>(`/healthz`, {
    status: "unknown",
    service: "WAOS",
    version: "-",
    environment: "development",
  });
}
