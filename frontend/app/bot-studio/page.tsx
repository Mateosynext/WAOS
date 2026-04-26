import Link from "next/link";
import { Shell } from "@/app/components/layout/shell";
import { AiCommandCenter } from "@/features/ai-command-center/AiCommandCenter";
import { requireSession } from "@/app/lib/session";
import { getBots } from "@/app/lib/data/bots";
import { getVerticalCatalog } from "@/app/lib/data/verticals";
import { cleanRouteSearchValue } from "@/features/bot-studio/domain/flowConfig";
import type { AiCommandVerticalOption } from "@/features/ai-command-center/types";

type SearchParams = Record<string, string | string[] | undefined>;
function firstParam(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] || "" : value || ""; }
function cleanParam(value: string | string[] | undefined) { return cleanRouteSearchValue(firstParam(value)); }
async function safeBots() { try { return await getBots(); } catch { return []; } }
async function safeVerticals(): Promise<AiCommandVerticalOption[]> {
  try {
    const catalog = await getVerticalCatalog(false);
    return catalog.map((vertical) => ({
      id: vertical.id,
      name: vertical.name,
      short_name: vertical.short_name || null,
      description: vertical.description || vertical.problem || vertical.ten_x_narrative || null,
      subverticals: vertical.subverticals || [],
      recommended_subverticals: vertical.recommended_subverticals || [],
      subvertical_profiles: (vertical.subvertical_profiles || []).map((profile) => ({
        name: profile.name,
        promise: profile.promise,
        buyer: profile.buyer,
        growth_motion: profile.growth_motion,
      })),
    }));
  } catch {
    return [];
  }
}

export default async function BotStudioPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const resolvedParams = (await searchParams) ?? {};
  const runId = cleanParam(resolvedParams.run_id);
  const [session, bots, verticals] = await Promise.all([requireSession(), safeBots(), safeVerticals()]);
  const organizations = (session?.user.organizations || []).map((item) => ({ id: item.id, name: item.name }));
  const botOptions = bots.map((bot) => ({ id: bot.id, name: bot.name || bot.business_name || bot.id }));
  return (
    <Shell title="WAOS AI Command Center" subtitle="Describe el negocio; WAOS construye, valida y prepara el agente de WhatsApp para producción con aprobación humana." action={<><Link href="/bots" className="secondary-btn">Ver bots</Link><Link href="/launch-center" className="secondary-btn">Launch Center</Link></>}>
      <AiCommandCenter organizations={organizations} bots={botOptions} verticals={verticals} initialRunId={runId || null} />
    </Shell>
  );
}
