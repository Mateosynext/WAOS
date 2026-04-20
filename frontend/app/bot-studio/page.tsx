import Link from "next/link";
import { ContextTip, EmptyActionState, Section, Shell } from "../components";
import { apiFetchOrDefault } from "../lib/api";
import { requireSession } from "../lib/session";
import { getBots, getStrongestVerticals, getVerticalCatalog, getVerticalProfile } from "../lib/waos";
import BotStudioWizardClient from "./BotStudioWizardClient";
import type { WizardBlueprint, WizardInstance, WizardMode } from "./wizard-types";

type SearchParams = Record<string, string | string[] | undefined>;

function firstParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] || "" : value || "";
}

function pickCatalogSubvertical(profile?: { selected_subvertical?: { name?: string }; recommended_subverticals?: string[]; subvertical_profiles?: Array<{ name?: string }>; subverticals?: string[] } | null) {
  return profile?.selected_subvertical?.name || "";
}

async function getInitialBlueprint(args: {
  organizationId: string;
  verticalId: string;
  subvertical: string;
  primaryObjective: string;
  botId?: string;
}) {
  const params = new URLSearchParams();
  params.set("organization_id", args.organizationId);
  params.set("vertical_id", args.verticalId);
  params.set("primary_objective", args.primaryObjective || "agendar");
  if (args.subvertical) params.set("subvertical", args.subvertical);
  if (args.botId) params.set("bot_id", args.botId);
  return apiFetchOrDefault<WizardBlueprint | null>(`/api/v1/onboarding/wizard/blueprint?${params.toString()}`, null);
}

export default async function BotStudioPage({
  searchParams,
}: {
  searchParams?: Promise<SearchParams>;
}) {
  const resolvedParams = (await searchParams) ?? {};
  const routeBotId = firstParam(resolvedParams?.bot);
  const routeMode = firstParam(resolvedParams?.mode);
  const routeWizardId = firstParam(resolvedParams?.wizard_id);
  const routeStep = firstParam(resolvedParams?.step);
  const routeOrganizationId = firstParam(resolvedParams?.organization_id);
  const routeVerticalId = firstParam(resolvedParams?.vertical);
  const routeSubvertical = firstParam(resolvedParams?.subvertical);
  const routePrimaryObjective = firstParam(resolvedParams?.primary_objective);

  const session = await requireSession();
  const [verticals, strongestVerticals, bots, initialWizard] = await Promise.all([
    getVerticalCatalog(),
    getStrongestVerticals(),
    getBots(),
    routeWizardId ? apiFetchOrDefault<WizardInstance | null>(`/api/v1/onboarding/wizard/${routeWizardId}`, null) : Promise.resolve(null),
  ]);

  const organizations = session?.user.organizations || [];
  const organizationsById = Object.fromEntries(organizations.map((item) => [item.id, item]));
  const routeSelectedBot = bots.find((item) => item.id === routeBotId) || null;
  const initialMode: WizardMode = routeMode === "reconfigure" || Boolean(routeBotId) || Boolean(initialWizard?.bot_id) ? "reconfigure" : "create";
  const initialSelectedBot = initialMode === "reconfigure" ? (routeSelectedBot || (initialWizard?.bot_id ? bots.find((item) => item.id === initialWizard.bot_id) || null : null)) : null;
  const waitingForExplicitBotSelection = initialMode === "reconfigure" && !initialSelectedBot && !initialWizard?.bot_id;
  const explicitWizardOrganization = initialWizard?.organization_id ? organizationsById[initialWizard.organization_id] || null : null;
  const explicitRouteOrganization = routeOrganizationId ? organizationsById[routeOrganizationId] || null : null;
  const botOrganization = initialSelectedBot ? organizationsById[initialSelectedBot.organization_id] || null : null;
  const wizardOrganization = waitingForExplicitBotSelection
    ? null
    : explicitWizardOrganization
      || explicitRouteOrganization
      || botOrganization
      || null;
  const initialOrganizationId = initialMode === "create"
    ? (explicitWizardOrganization?.id || explicitRouteOrganization?.id || "")
    : (wizardOrganization?.id || "");
  const wizardFit = (initialWizard?.answers?.vertical_fit || {}) as Record<string, unknown>;
  const catalogVertical = waitingForExplicitBotSelection
    ? null
    : verticals.find((item) => item.id === String(wizardFit.vertical_id || ""))
      || verticals.find((item) => item.id === routeVerticalId)
      || null;
  const initialVerticalId = catalogVertical?.id || "";
  const initialSubvertical = waitingForExplicitBotSelection
    ? ""
    : String(wizardFit.subvertical || routeSubvertical || initialWizard?.subvertical || pickCatalogSubvertical(catalogVertical));
  const initialPrimaryObjective = waitingForExplicitBotSelection
    ? "agendar"
    : String(wizardFit.primary_objective || routePrimaryObjective || initialWizard?.primary_objective || "agendar");
  const initialSelectedBotId = initialMode === "reconfigure" ? initialSelectedBot?.id || String(initialWizard?.bot_id || "") : "";
  const [initialBlueprint, initialVerticalProfile] = initialOrganizationId && initialVerticalId
    ? await Promise.all([
        getInitialBlueprint({
          organizationId: initialOrganizationId,
          verticalId: initialVerticalId,
          subvertical: initialSubvertical,
          primaryObjective: initialPrimaryObjective,
          botId: initialSelectedBotId || undefined,
        }),
        getVerticalProfile(initialVerticalId, initialSelectedBotId || undefined, initialSubvertical || undefined, initialOrganizationId),
      ])
    : [null, null];

  if (!verticals.length) {
    return (
      <Shell
        title="Bot Studio"
        subtitle="Bot Studio es el único lugar para crear o reconfigurar asistentes operativos. Si falla el catálogo, este módulo no puede sembrar un setup confiable."
        action={<><Link href="/organizations" className="secondary-btn">Organizaciones</Link><Link href="/verticals" className="secondary-btn">Reintentar catálogo</Link></>}
      >
        <EmptyActionState
          title="Catálogo de industrias no disponible"
          description="La sesión está activa, pero la UI no recibió industrias. Revisa el endpoint /api/v1/verticals o vuelve a iniciar sesión."
          primaryAction={<Link href="/verticals" className="primary-btn">Abrir industrias</Link>}
        />
      </Shell>
    );
  }

  return (
    <Shell
      title="Bot Studio"
      subtitle="Bot Studio ya no compite con Onboarding: aquí solo se crea o reconfigura el asistente operativo. El estado vive en un wizard_id de backend y el apply real sale desde este módulo."
      action={<><Link href="/bots" className="secondary-btn">Ver asistentes operativos</Link><Link href="/onboarding" className="secondary-btn">Ver readiness en Onboarding</Link></>}
    >
      <ContextTip title="Qué hace Bot Studio y qué no">
        Bot Studio crea o reconfigura. Onboarding solo mide readiness y checklist; Integraciones conecta y prueba; Releases publica; Inbox opera. Aquí es donde se persisten los pasos, el review y la aplicación final.
      </ContextTip>

      <Section
        title="Crear o reconfigurar desde Bot Studio"
        subtitle="La shell server solo resuelve contexto. El cliente maneja el estado del wizard, persiste con wizard_id en URL y aplica los cambios desde el backend real sin competir con Onboarding ni con Integraciones."
        icon="wand"
      >
        <BotStudioWizardClient
          organizations={organizations}
          verticals={verticals}
          strongestVerticals={strongestVerticals}
          bots={bots}
          initialSelectedBotId={initialSelectedBotId}
          initialMode={initialMode}
          initialOrganizationId={initialOrganizationId}
          initialVerticalId={initialVerticalId}
          initialSubvertical={initialSubvertical}
          initialPrimaryObjective={initialPrimaryObjective}
          initialBlueprint={initialBlueprint}
          initialVerticalProfile={initialVerticalProfile}
          initialWizardId={routeWizardId}
          initialWizard={initialWizard}
          initialStepOverride={routeStep}
        />
      </Section>
    </Shell>
  );
}
