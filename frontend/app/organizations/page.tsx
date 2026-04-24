import Link from "next/link";
import { updateOrganizationVerticalAction } from "@/app/actions/organizations";
import { switchOrganizationAction } from "@/app/actions/selection";
import BotScopeSwitcher from "../components/BotScopeSwitcher";
import OrganizationSwitcher from "../components/OrganizationSwitcher";
import { ContextTip, EmptyActionState, SuccessState } from "@/app/components/feedback";
import { Shell } from "@/app/components/layout/shell";
import { ModuleCard, Section, StatCard } from "@/app/components/primitives/cards";
import ReactiveVerticalConfigurator from "../components/ReactiveVerticalConfigurator";
import { getCurrentBotId, getSession } from "../lib/session";
import { safeText } from "../lib/ui";
import { getBots } from "@/app/lib/data/bots";
import { getStrongestVerticals, getVerticalCatalog, getVerticalProfile } from "@/app/lib/data/verticals";

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }

export default async function OrganizationsPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const source = first(params.source) || "";
  const [session, selectedBotId] = await Promise.all([getSession(), getCurrentBotId()]);
  const organizations = session?.user.organizations || [];
  const selectedOrg = organizations.find((item) => item.id === session?.organizationId) || null;
  const [verticals, strongestVerticals, bots, currentVertical] = await Promise.all([
    getVerticalCatalog(),
    getStrongestVerticals(),
    getBots(),
    getVerticalProfile(selectedOrg?.vertical, undefined, selectedOrg?.subvertical, selectedOrg?.id),
  ]);
  const selectedBot = bots.find((item) => item.id === selectedBotId) || null;

  return (
    <Shell title="Confirmar contexto" subtitle="Aquí fijas el tenant, el bot de trabajo y la vertical sin defaults silenciosos. El producto solo opera cuando el contexto queda explícito.">
      {source === "login" ? <ContextTip title="Paso final del acceso">Tu cuenta ve varias organizaciones. Antes de entrar al producto, confirma cuál vas a operar para que el contexto cargue bots, inbox, integraciones y releases correctos.</ContextTip> : null}
      {source === "context-lock" ? <ContextTip title="Cambio de contexto explícito">Este flujo ya no infiere tenant, bot ni vertical. Primero eliges el tenant, luego el bot y solo después entras a las pantallas críticas.</ContextTip> : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatCard label="Organizaciones visibles" value={String(organizations.length)} hint="Contextos a los que esta cuenta puede entrar" icon="client" tone="green" />
        <StatCard label="Bots visibles" value={String(bots.length)} hint="Asistentes del tenant activo" icon="bot" tone="blue" />
        <StatCard label="Industrias base" value={String(verticals.length)} hint="Catalogo habilitado para super admin" icon="layers" tone="blue" />
        <StatCard label="Organización activa" value={safeText(selectedOrg?.name, "sin seleccionar")} hint="Sobre esta organización se aplican los cambios" icon="target" tone="gold" />
        <StatCard label="Bot activo" value={safeText(selectedBot?.name, "sin seleccionar")} hint="Contexto operativo para módulos por bot" icon="wand" tone="slate" />
      </div>

      <Section title="Tenant de trabajo" subtitle="Elige una organización para cargar bots, integraciones, inbox y releases con el contexto correcto." icon="client">
        {organizations.length ? (
          <OrganizationSwitcher organizations={organizations.map((item) => ({ id: item.id, name: item.name, vertical: item.vertical }))} selectedId={session?.organizationId || null} redirectTo="/organizations" action={switchOrganizationAction} />
        ) : (
          <EmptyActionState title="No hay organizaciones disponibles" description="Esta cuenta todavia no tiene organizaciones asignadas o no pudimos cargarlas." />
        )}
      </Section>

      <Section title="Bot de trabajo" subtitle="Después de fijar el tenant, elige explícitamente el bot que vas a operar. Integraciones, vacantes, releases y otras vistas ya no caen al primer bot disponible." icon="bot" aside={selectedOrg ? <BotScopeSwitcher bots={bots} selectedBotId={selectedBotId} redirectTo="/organizations" /> : null}>
        {!selectedOrg ? (
          <EmptyActionState title="Primero selecciona un tenant" description="El selector de bot se habilita cuando el tenant ya quedó fijado. Así evitamos mezclar bots de otro contexto." />
        ) : selectedBot ? (
          <SuccessState title={`Bot seleccionado: ${safeText(selectedBot.name)}`} description="Este bot queda como alcance explícito para las pantallas que operan sobre un asistente concreto." actions={<Link href="/bots" className="primary-btn">Ver inventario de bots</Link>} />
        ) : bots.length ? (
          <EmptyActionState title="Falta seleccionar un bot" description="Ya quedó fijo el tenant, pero todavía no elegiste el bot activo. Hazlo aquí antes de volver a integraciones, vacantes o cualquier flujo crítico." primaryAction={<Link href="/bots" className="primary-btn">Abrir bots</Link>} />
        ) : (
          <EmptyActionState title="Todavía no hay bots en este tenant" description="Crea el primer bot antes de operar módulos atados a un asistente específico." primaryAction={<Link href="/bot-studio" className="primary-btn">Crear bot</Link>} />
        )}
      </Section>

      <Section title="Aplicar industria a la organización activa" subtitle="Este formulario actualiza la organización seleccionada y deja persistidas la industria y el tipo de operación para onboarding, inbox, agenda, comercial y portal cliente." icon="wand">
        {selectedOrg ? (
          <ReactiveVerticalConfigurator
            organizationId={selectedOrg.id}
            organizationName={selectedOrg.name}
            initialVerticalId={selectedOrg.vertical || ""}
            initialSubvertical={selectedOrg.subvertical || currentVertical.selected_subvertical?.name || ""}
            initialVerticalProfile={currentVertical}
            verticals={verticals}
            strongestVerticals={strongestVerticals}
            submitLabel="Guardar industria de la organización"
            redirectTo="/organizations"
            action={updateOrganizationVerticalAction}
            introTitle="La industria de la organización ya reacciona antes de guardar"
            introDescription="Cuando cambias industria, la UI refresca tipos de operación y blueprint al instante. Si no eliges explícitamente la industria y el tipo de operación, la pantalla queda bloqueada y no infiere defaults." 
            previewTitle="Preview operativo de la organización"
          />
        ) : (
          <EmptyActionState title="Primero selecciona una organizacion" description="Sin una organización activa no conviene aplicar industrias porque el cambio debe quedar atado a una organización real." />
        )}
      </Section>

      <Section title="Industrias base habilitadas para super admin" subtitle="Este catálogo ya existe en backend y frontend para que el onboarding, la creación del asistente operativo y el portal cliente hablen el mismo idioma operativo." icon="layers">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {verticals.map((vertical) => (
            <ModuleCard
              key={vertical.id}
              title={vertical.name}
              description={vertical.description || vertical.problem || "Industria lista para operar."}
              icon="wand"
              tone="green"
              footer={<span className="mono-pill">{vertical.recommended_integrations.join(" · ") || "base operativa"}</span>}
            />
          ))}
        </div>
      </Section>
    </Shell>
  );
}
