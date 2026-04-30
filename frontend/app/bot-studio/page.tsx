import Link from "next/link";
import { Shell } from "@/app/components/layout/shell";
import { UiMessage } from "@/app/components/UiMessage";
import { AiCommandCenter } from "@/features/ai-command-center/AiCommandCenter";
import { requireSession } from "@/app/lib/session";
import { getBots } from "@/app/lib/data/bots";
import { getVerticalCatalog } from "@/app/lib/data/verticals";
import { cleanRouteSearchValue } from "@/features/bot-studio/domain/flowConfig";

// Bot Studio may still render in degraded mode, but never silently: every
// backend/catalog failure is surfaced to the operator before an empty list can
// be mistaken for "no bots" or "no verticales".
type SearchParams = Record<string, string | string[] | undefined>;
type LoadResult<T> = { data: T; error: string | null };

function firstParam(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] || "" : value || ""; }
function cleanParam(value: string | string[] | undefined) { return cleanRouteSearchValue(firstParam(value)); }
function loadErrorMessage(source: string, error: unknown) {
  const message = error instanceof Error ? error.message : String(error || "unknown error");
  return `${source}: ${message}`;
}
async function loadWithNotice<T>(source: string, loader: () => Promise<T>, fallback: T): Promise<LoadResult<T>> {
  try {
    return { data: await loader(), error: null };
  } catch (error) {
    return { data: fallback, error: loadErrorMessage(source, error) };
  }
}

export default async function BotStudioPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const resolvedParams = (await searchParams) ?? {};
  const runId = cleanParam(resolvedParams.run_id);
  const [session, botsResult, verticalsResult] = await Promise.all([
    requireSession(),
    loadWithNotice("bots", getBots, []),
    loadWithNotice("verticals", getVerticalCatalog, []),
  ]);
  const organizations = (session?.user.organizations || []).map((item) => ({ id: item.id, name: item.name, vertical: item.vertical || null, subvertical: item.subvertical || null, timezone: item.timezone || null }));
  const botOptions = botsResult.data.map((bot) => ({ id: bot.id, name: bot.name || bot.business_name || bot.id }));
  const safeVerticals = verticalsResult.data;
  const verticals = safeVerticals;
  const warnings = [botsResult.error, verticalsResult.error].filter(Boolean) as string[];
  return (
    <Shell title="WAOS AI Command Center" subtitle="Describe el negocio; WAOS construye, valida y prepara el agente de WhatsApp para produccion con aprobacion humana." action={<><Link href="/bots" className="secondary-btn">Ver bots</Link><Link href="/launch-center" className="secondary-btn">Launch Center</Link></>}>
      <div className="grid gap-4">
        {warnings.length ? (
          <UiMessage title="Bot Studio cargó con datos incompletos" tone="warning">
            <p>No se mostrará una lista vacía como si fuera estado real. Revisa backend/API antes de operar.</p>
            <ul className="mt-2 list-disc pl-5">{warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
          </UiMessage>
        ) : null}
        <AiCommandCenter organizations={organizations} bots={botOptions} verticals={verticals} initialRunId={runId || null} />
      </div>
    </Shell>
  );
}
