import Link from "next/link";
import { Shell } from "@/app/components/layout/shell";
import { AiOpsInspector } from "@/features/ai-ops/AiOpsInspector";

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] || "" : value || ""; }

export default async function AiOpsPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const runId = first(params.run_id);
  return (
    <Shell title="AI Operations Inspector" subtitle="Runs, steps, eventos, prompts versionados, modelos, costos, simulation failures, readiness, runtime turns y riesgos." action={<Link href="/bot-studio" className="primary-btn">AI Command Center</Link>}>
      <AiOpsInspector initialRunId={runId || null} />
    </Shell>
  );
}
