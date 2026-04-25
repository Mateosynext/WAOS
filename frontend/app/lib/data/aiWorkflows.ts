import "server-only";
import { apiFetch } from "@/app/lib/api";

export type AiWorkflowRun = Record<string, unknown>;
export async function getAiWorkflow(runId: string) { return apiFetch<AiWorkflowRun>(`/api/v1/ai/workflows/${encodeURIComponent(runId)}`); }
export async function listAiOpsRuns() { return apiFetch<AiWorkflowRun>(`/api/v1/internal/ai-ops/runs`); }
