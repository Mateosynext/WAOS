"use client";

import { useEffect, useMemo } from "react";
import { AiCommandPrompt } from "./AiCommandPrompt";
import { AiRunTimeline } from "./AiRunTimeline";
import { AiGeneratedArtifacts } from "./AiGeneratedArtifacts";
import { AiReadinessPanel } from "./AiReadinessPanel";
import { HumanConfirmationPanel } from "./HumanConfirmationPanel";
import { LaunchActionsPanel } from "./LaunchActionsPanel";
import { useBotAutopilotRun } from "./useBotAutopilotRun";
import { useAiWorkflowStream } from "./useAiWorkflowStream";

type Option = { id: string; name?: string; label?: string };

export function AiCommandCenter({ organizations, bots, initialRunId }: { organizations: Option[]; bots: Option[]; initialRunId?: string | null }) {
  const workflow = useBotAutopilotRun(initialRunId);
  const stream = useAiWorkflowStream(workflow.runId);

  useEffect(() => {
    if (initialRunId) void workflow.refresh(initialRunId);
  }, [initialRunId]);

  const streamedResult = useMemo(() => {
    return (stream.terminalEvent?.payload_json as Record<string, any> | undefined) || null;
  }, [stream.terminalEvent]);

  useEffect(() => {
    if (stream.terminalEvent && workflow.runId) void workflow.refresh(workflow.runId);
  }, [stream.terminalEvent, workflow.runId]);

  const workflowPayload = workflow.run as Record<string, any> | null;
  const run = streamedResult || workflowPayload?.result || workflowPayload?.run?.result_json || workflowPayload || null;
  const confirmations = (workflowPayload?.human_confirmations as any[]) || (run?.human_confirmations as any[]) || (run?.go_live_readiness as any)?.human_confirmations_required;

  async function submit(input: any) {
    await workflow.start(input);
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
      <div className="grid gap-6">
        <AiCommandPrompt organizations={organizations} bots={bots} loading={workflow.loading} disabled={!organizations.length} onSubmit={submit} />
        {workflow.error ? <p className="rounded-2xl border p-3 text-sm text-[color:var(--warning-text)]">{workflow.error}</p> : null}
        {stream.error ? <p className="rounded-2xl border p-3 text-sm text-[color:var(--warning-text)]">{stream.error}</p> : null}
        <AiRunTimeline events={stream.events} connected={stream.connected} />
        <AiGeneratedArtifacts run={run} />
        <HumanConfirmationPanel runId={workflow.runId} items={confirmations} onConfirmed={() => workflow.refresh()} />
        <LaunchActionsPanel runId={workflow.runId} readiness={run?.go_live_readiness as any} onChanged={() => workflow.refresh()} />
      </div>
      <div className="grid content-start gap-6">
        <AiReadinessPanel readiness={run?.go_live_readiness as any} />
        <section className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 text-sm">
          <strong>Cost / provider</strong>
          <p>Cost estimate, provider missing y fallbacks se leen del workflow run y de los eventos reales.</p>
          <p>Run: {workflow.runId || "sin iniciar"}</p>
          <p>Status: {String((run as any)?.status || (workflowPayload?.run as any)?.status || "idle")}</p>
        </section>
      </div>
    </div>
  );
}
