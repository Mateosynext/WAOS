import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyActionState } from "@/app/components/feedback";
import { Shell } from "@/app/components/layout/shell";
import { Section } from "@/app/components/primitives/cards";
import { BotStudioRoute } from "@/features/bot-studio/BotStudioRoute";
import { buildBotStudioHref, cleanRouteSearchValue, getFirstRouteStep, normalizeRouteStep } from "@/features/bot-studio/domain/flowConfig";
import { loadBotStudioRoute } from "@/features/bot-studio/server/loadBotStudioRoute";

const MANUAL_ENABLED = process.env.NEXT_PUBLIC_ENABLE_MANUAL_BOT_CREATE === "true";
type SearchParams = Record<string, string | string[] | undefined>;
function firstParam(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] || "" : value || ""; }
function cleanParam(value: string | string[] | undefined) { return cleanRouteSearchValue(firstParam(value)); }
function redirectForCreateStep(_step: string, params: SearchParams) { const runId = cleanParam(params.run_id); const wizardId = cleanParam(params.wizard_id); if (!MANUAL_ENABLED) { const query = runId ? `?run_id=${encodeURIComponent(runId)}` : wizardId ? `?wizard_id=${encodeURIComponent(wizardId)}` : ""; redirect(`/bot-studio${query}`); } }

export default async function Page({ params, searchParams }: { params: Promise<{ mode: string; slug?: string[] }>; searchParams?: Promise<SearchParams> }) {
  const { mode: rawMode, slug = [] } = await params; const resolvedParams = (await searchParams) ?? {}; const mode = rawMode === "reconfigure" ? "reconfigure" : "create"; const requestedStep = slug[0] || ""; const normalizedStep = normalizeRouteStep(mode, requestedStep) || normalizeRouteStep(mode, cleanParam(resolvedParams?.step)) || getFirstRouteStep(mode);
  if (mode === "create") redirectForCreateStep(String(normalizedStep), resolvedParams);
  if (!requestedStep) redirect(buildBotStudioHref(mode, normalizedStep, { wizard_id: cleanParam(resolvedParams?.wizard_id), bot: cleanParam(resolvedParams?.bot), organization_id: cleanParam(resolvedParams?.organization_id), vertical: cleanParam(resolvedParams?.vertical), subvertical: cleanParam(resolvedParams?.subvertical), primary_objective: cleanParam(resolvedParams?.primary_objective) }));
  const model = await loadBotStudioRoute({ mode, botId: cleanParam(resolvedParams?.bot), wizardId: cleanParam(resolvedParams?.wizard_id), organizationId: cleanParam(resolvedParams?.organization_id), verticalId: cleanParam(resolvedParams?.vertical), subvertical: cleanParam(resolvedParams?.subvertical), primaryObjective: cleanParam(resolvedParams?.primary_objective), step: normalizedStep });
  if (mode === "create" && normalizedStep === "context" && !model.verticals.length) return <Shell title="AI Command Center" subtitle="El catálogo de industrias no está disponible." action={<Link href="/verticals" className="secondary-btn">Abrir industrias</Link>}><EmptyActionState title="Catálogo no disponible" description="No llegaron verticales al frontend." primaryAction={<Link href="/verticals" className="primary-btn">Revisar catálogo</Link>} /></Shell>;
  return <Shell title={mode === "reconfigure" ? "Reconfigure" : "AI Generated Setup Review"} subtitle={mode === "reconfigure" ? "Reconfigura bots existentes desde su detalle operativo." : "Setup generado por IA detrás de feature flag interno."} action={<><Link href="/bot-studio" className="secondary-btn">AI Command Center</Link><Link href="/bots" className="secondary-btn">Ver bots</Link></>}><Section title={mode === "reconfigure" ? "Reconfiguración" : "Simulation & Go-Live Readiness"} subtitle={mode === "reconfigure" ? "Seleccionar bot → diff → dry run → confirmación → resultado." : "Review generado, readiness y apply seguro."} icon="wand"><BotStudioRoute {...model} routeMode={mode} routeStep={normalizedStep} /></Section></Shell>;
}
