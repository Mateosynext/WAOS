import Link from "next/link";
import { redirect } from "next/navigation";
import { ContextTip, EmptyActionState, Section, Shell } from "../../../components";
import BotStudioFlowClient from "../../BotStudioFlowClient";
import { buildBotStudioHref, getFirstRouteStep, normalizeRouteStep } from "../../flowConfig";
import { loadBotStudioFlowData } from "../../flowLoader";

type SearchParams = Record<string, string | string[] | undefined>;
function firstParam(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] || "" : value || ""; }

export default async function BotStudioFlowRoute({ params, searchParams }: { params: Promise<{ mode: string; slug?: string[] }>; searchParams?: Promise<SearchParams> }) {
  const { mode: rawMode, slug = [] } = await params;
  const resolvedParams = (await searchParams) ?? {};
  const mode = rawMode === "reconfigure" ? "reconfigure" : "create";
  const requestedStep = slug[0] || "";
  const normalizedStep = normalizeRouteStep(mode, requestedStep) || normalizeRouteStep(mode, firstParam(resolvedParams?.step)) || getFirstRouteStep(mode);
  if (!requestedStep) redirect(buildBotStudioHref(mode, normalizedStep, { wizard_id: firstParam(resolvedParams?.wizard_id), bot: firstParam(resolvedParams?.bot), organization_id: firstParam(resolvedParams?.organization_id), vertical: firstParam(resolvedParams?.vertical), subvertical: firstParam(resolvedParams?.subvertical), primary_objective: firstParam(resolvedParams?.primary_objective) }));
  const flowData = await loadBotStudioFlowData({ mode, botId: firstParam(resolvedParams?.bot), wizardId: firstParam(resolvedParams?.wizard_id), organizationId: firstParam(resolvedParams?.organization_id), verticalId: firstParam(resolvedParams?.vertical), subvertical: firstParam(resolvedParams?.subvertical), primaryObjective: firstParam(resolvedParams?.primary_objective), step: normalizedStep });
  if (!flowData.verticals.length) return <Shell title="Bot Studio" subtitle="El flujo por etapas necesita catálogo de industrias." action={<Link href="/verticals" className="secondary-btn">Abrir industrias</Link>}><EmptyActionState title="Catálogo no disponible" description="No llegaron verticales al frontend, así que Bot Studio no puede renderizar las nuevas rutas por paso." primaryAction={<Link href="/verticals" className="primary-btn">Revisar catálogo</Link>} /></Shell>;
  return <Shell title="Bot Studio" subtitle={mode === "create" ? "Create ahora vive como un flujo modular por pantallas." : "Reconfigure ahora vive en un flujo corto y separado."} action={<><Link href="/bot-studio" className="secondary-btn">Ver entradas</Link><Link href="/bots" className="secondary-btn">Ver bots</Link></>}><ContextTip title="Patrón de navegación activo">Una pantalla = una sola decisión principal. El paso actual aísla su contexto y mantiene progreso visible.</ContextTip><Section title={mode === "create" ? "Flujo de creación modular" : "Flujo de reconfiguración modular"} subtitle={mode === "create" ? "Cada etapa vive en su propia route." : "El cambio sobre bots existentes ya no reutiliza la misma vista pesada de create."} icon="wand"><BotStudioFlowClient {...flowData} routeMode={mode} routeStep={normalizedStep} /></Section></Shell>;
}
