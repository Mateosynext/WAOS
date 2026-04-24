import Link from "next/link";
import { redirect } from "next/navigation";
import { ContextTip, EmptyActionState } from "@/app/components/feedback";
import { Shell } from "@/app/components/layout/shell";
import { Section } from "@/app/components/primitives/cards";
import { BotStudioRoute } from "@/features/bot-studio/BotStudioRoute";
import { buildBotStudioHref, cleanRouteSearchValue, getFirstRouteStep, normalizeRouteStep } from "@/features/bot-studio/domain/flowConfig";
import { loadBotStudioRoute } from "@/features/bot-studio/server/loadBotStudioRoute";

type SearchParams = Record<string, string | string[] | undefined>;
function firstParam(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] || "" : value || ""; }
function cleanParam(value: string | string[] | undefined) { return cleanRouteSearchValue(firstParam(value)); }

export default async function Page({ params, searchParams }: { params: Promise<{ mode: string; slug?: string[] }>; searchParams?: Promise<SearchParams> }) {
  const { mode: rawMode, slug = [] } = await params;
  const resolvedParams = (await searchParams) ?? {};
  const mode = rawMode === "reconfigure" ? "reconfigure" : "create";
  const requestedStep = slug[0] || "";
  const normalizedStep = normalizeRouteStep(mode, requestedStep) || normalizeRouteStep(mode, cleanParam(resolvedParams?.step)) || getFirstRouteStep(mode);
  if (!requestedStep) redirect(buildBotStudioHref(mode, normalizedStep, { wizard_id: cleanParam(resolvedParams?.wizard_id), bot: cleanParam(resolvedParams?.bot), organization_id: cleanParam(resolvedParams?.organization_id), vertical: cleanParam(resolvedParams?.vertical), subvertical: cleanParam(resolvedParams?.subvertical), primary_objective: cleanParam(resolvedParams?.primary_objective) }));
  const model = await loadBotStudioRoute({ mode, botId: cleanParam(resolvedParams?.bot), wizardId: cleanParam(resolvedParams?.wizard_id), organizationId: cleanParam(resolvedParams?.organization_id), verticalId: cleanParam(resolvedParams?.vertical), subvertical: cleanParam(resolvedParams?.subvertical), primaryObjective: cleanParam(resolvedParams?.primary_objective), step: normalizedStep });
  if (mode === "create" && normalizedStep === "context" && !model.verticals.length) return <Shell title="Bot Studio" subtitle="El flujo por etapas necesita catálogo de industrias." action={<Link href="/verticals" className="secondary-btn">Abrir industrias</Link>}><EmptyActionState title="Catálogo no disponible" description="No llegaron verticales al frontend, así que Bot Studio no puede renderizar la selección inicial." primaryAction={<Link href="/verticals" className="primary-btn">Revisar catálogo</Link>} /></Shell>;
  return <Shell title="Bot Studio" subtitle={mode === "create" ? "Create ahora vive como un flujo modular por pantallas." : "Reconfigure ahora vive en un flujo corto y separado."} action={<><Link href="/bot-studio" className="secondary-btn">Ver entradas</Link><Link href="/bots" className="secondary-btn">Ver bots</Link></>}><ContextTip title="Patrón de navegación activo">Una pantalla = una sola decisión principal. El paso actual aísla su contexto y mantiene progreso visible.</ContextTip><Section title={mode === "create" ? "Flujo de creación modular" : "Flujo de reconfiguración modular"} subtitle={mode === "create" ? "Cada etapa vive en su propia route." : "El cambio sobre bots existentes ya no reutiliza la misma vista pesada de create."} icon="wand"><BotStudioRoute {...model} routeMode={mode} routeStep={normalizedStep} /></Section></Shell>;
}
