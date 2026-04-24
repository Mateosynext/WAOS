import Link from "next/link";
import { redirect } from "next/navigation";
import { ContextTip, EmptyActionState } from "@/app/components/feedback";
import { Shell } from "@/app/components/layout/shell";
import { ModuleCard, Section } from "@/app/components/primitives/cards";
import { buildBotStudioHref, cleanRouteSearchValue, getFirstRouteStep, normalizeRouteStep } from "@/features/bot-studio/domain/flowConfig";

type SearchParams = Record<string, string | string[] | undefined>;
function firstParam(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] || "" : value || ""; }
function cleanParam(value: string | string[] | undefined) { return cleanRouteSearchValue(firstParam(value)); }

export default async function BotStudioPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const resolvedParams = (await searchParams) ?? {};
  const routeMode = cleanParam(resolvedParams?.mode);
  const routeBotId = cleanParam(resolvedParams?.bot);
  const routeWizardId = cleanParam(resolvedParams?.wizard_id);
  const routeStep = cleanParam(resolvedParams?.step);
  const routeOrganizationId = cleanParam(resolvedParams?.organization_id);
  const routeVerticalId = cleanParam(resolvedParams?.vertical);
  const routeSubvertical = cleanParam(resolvedParams?.subvertical);
  const routePrimaryObjective = cleanParam(resolvedParams?.primary_objective);
  if (routeMode || routeBotId || routeWizardId || routeStep) {
    const mode = routeMode === "reconfigure" || (!routeMode && routeBotId) ? "reconfigure" : "create";
    const normalizedStep = normalizeRouteStep(mode, routeStep) || getFirstRouteStep(mode);
    redirect(buildBotStudioHref(mode, normalizedStep, { wizard_id: routeWizardId, bot: routeBotId, organization_id: routeOrganizationId, vertical: routeVerticalId, subvertical: routeSubvertical, primary_objective: routePrimaryObjective }));
  }
  return <Shell title="Bot Studio" subtitle="Bot Studio ahora separa create y reconfigure en flujos propios por pantalla." action={<><Link href="/bots" className="secondary-btn">Ver asistentes operativos</Link><Link href="/launch-center" className="secondary-btn">Ver launch center</Link></>}><ContextTip title="Nueva regla del flujo">Create y reconfigure ya no comparten la misma mega vista. Cada paso vive en su propia ruta y aísla una sola decisión para que el avance sea limpio, legible y profesional.</ContextTip><Section title="Elegir flujo" subtitle="Arranca desde un flujo limpio." icon="wand"><div className="grid gap-4 xl:grid-cols-2"><ModuleCard title="Create" description="Contexto → identidad → oferta → knowledge → integraciones → review → validación → apply → resultado." icon="bot" tone="green" footer={<Link href="/bot-studio/create/context" className="primary-btn">Crear desde cero</Link>} /><ModuleCard title="Reconfigure" description="Seleccionar bot → diff → dry run → confirmación → resultado." icon="refresh" tone="blue" footer={<Link href="/bot-studio/reconfigure/select" className="primary-btn">Reconfigurar bot</Link>} /></div></Section><Section title="Rutas canónicas" subtitle="La navegación ahora es explícita y estable." icon="route"><div className="grid gap-4 xl:grid-cols-2"><div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4 text-sm leading-7 text-[color:var(--text-secondary)]"><div className="font-semibold text-[color:var(--text-primary)]">Create</div><div className="mt-3">/bot-studio/create/context</div><div>/bot-studio/create/identity</div><div>/bot-studio/create/offer</div><div>/bot-studio/create/knowledge</div><div>/bot-studio/create/integrations</div><div>/bot-studio/create/review</div><div>/bot-studio/create/validate</div><div>/bot-studio/create/apply</div><div>/bot-studio/create/success</div></div><div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4 text-sm leading-7 text-[color:var(--text-secondary)]"><div className="font-semibold text-[color:var(--text-primary)]">Reconfigure</div><div className="mt-3">/bot-studio/reconfigure/select</div><div>/bot-studio/reconfigure/diff</div><div>/bot-studio/reconfigure/dry-run</div><div>/bot-studio/reconfigure/confirm</div><div>/bot-studio/reconfigure/result</div></div></div></Section><EmptyActionState title="Entradas antiguas siguen funcionando" description="Las URLs viejas con query params redirigen a la ruta canónica del paso correspondiente." primaryAction={<Link href="/bot-studio/create/context" className="primary-btn">Ir a create</Link>} secondaryAction={<Link href="/bot-studio/reconfigure/select" className="secondary-btn">Ir a reconfigure</Link>} /></Shell>;
}
