import Link from "next/link";
import { Shell } from "@/app/components/layout/shell";
import { AiCommandCenter } from "@/features/ai-command-center/AiCommandCenter";
import { requireSession } from "@/app/lib/session";
import { getBots } from "@/app/lib/data/bots";
import { cleanRouteSearchValue } from "@/features/bot-studio/domain/flowConfig";

type SearchParams = Record<string, string | string[] | undefined>;
function firstParam(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] || "" : value || ""; }
function cleanParam(value: string | string[] | undefined) { return cleanRouteSearchValue(firstParam(value)); }
async function safeBots() { try { return await getBots(); } catch { return []; } }

export default async function BotStudioPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const resolvedParams = (await searchParams) ?? {};
  const runId = cleanParam(resolvedParams.run_id);
  const [session, bots] = await Promise.all([requireSession(), safeBots()]);
  const organizations = (session?.user.organizations || []).map((item) => ({ id: item.id, name: item.name }));
  const botOptions = bots.map((bot) => ({ id: bot.id, name: bot.name || bot.business_name || bot.id }));
  return (
    <Shell title="WAOS AI Command Center" subtitle="Describe el negocio; WAOS construye, valida y prepara el agente de WhatsApp para producción con aprobación humana." action={<><Link href="/bots" className="secondary-btn">Ver bots</Link><Link href="/launch-center" className="secondary-btn">Launch Center</Link></>}>
      <AiCommandCenter organizations={organizations} bots={botOptions} initialRunId={runId || null} />
    </Shell>
  );
}
