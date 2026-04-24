import { ModuleCard, Section } from "@/app/components/primitives/cards";
import { DataTable } from "@/app/components/primitives/data-display";
import { Badge } from "@/app/components/primitives/shared";
import { safeText } from "@/app/lib/ui";
import type { VerticalsPageModel } from "@/features/vertical-selection/server/getVerticalsPageModel";

export function VerticalReadiness({ model }: { model: VerticalsPageModel }) {
  const { profile, rows } = model;
  if (!profile) return null;
  return (
    <>
      <Section title="Pipeline, playbook y automatizaciones" subtitle="La operación vertical necesita estados, objeciones, escalamiento y secuencias repetibles." icon="flow">
        <div className="grid gap-4 xl:grid-cols-2">
          {rows.pipelineRows.length ? <DataTable columns={["Pipeline", "Estados"]} rows={rows.pipelineRows} /> : <ModuleCard title="Sin pipeline" description="No hay estados visibles para esta vertical." icon="alert" tone="red" />}
          {rows.automationRows.length ? <DataTable columns={["Automatización", "Trigger", "Objetivo", "Pasos"]} rows={rows.automationRows} /> : <ModuleCard title="Sin automatizaciones" description="No hay secuencias visibles para esta vertical." icon="alert" tone="red" />}
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-3">
          <ModuleCard title="Debe hacer" description={safeText(profile.bot_playbook.must_do.join(" • "), "Sin must-do")} icon="check" tone="green" />
          <ModuleCard title="Debe preguntar" description={safeText(profile.bot_playbook.must_ask.join(" • "), "Sin preguntas")} icon="chat" tone="blue" />
          <ModuleCard title="Escalar cuando" description={safeText(profile.bot_playbook.escalate_when.join(" • "), "Sin reglas")} icon="alert" tone="gold" />
        </div>
      </Section>

      <Section title="Dashboard / KPIs" subtitle="La vertical no se mide por mensajes respondidos, sino por movimiento real del negocio." icon="stats">
        <div className="mb-4 flex flex-wrap items-center gap-2"><Badge tone="green">North star</Badge><span className="text-sm text-slate-300">{safeText(profile.dashboard.north_star, "Sin north star definido")}</span></div>
        {rows.dashboardRows.length ? <DataTable columns={["Sección", "Métricas"]} rows={rows.dashboardRows} /> : <ModuleCard title="Sin métricas" description="No hay dashboard visible para esta vertical." icon="alert" tone="red" />}
        <div className="mt-4 grid gap-4 xl:grid-cols-2">
          <ModuleCard title="KPIs que importan" description={safeText(profile.specialist_layers.kpis_that_matter.join(" • "), "Sin KPIs")} icon="stats" tone="blue" />
          <ModuleCard title="Playbooks por subvertical" description={safeText(profile.domain_contract.vertical_playbooks.join(" • "), "Sin playbooks")} icon="bot" tone="green" />
        </div>
      </Section>

      <Section title="Readiness, evidencia y gaps" subtitle="Elementos accionables para saber si la vertical está lista para venderse y operarse." icon="check">
        <div className="grid gap-4 xl:grid-cols-3">
          <ModuleCard title="Objetos persistentes" description={safeText(profile.specialist_layers.persistent_entities.join(" • "), "Sin entidades persistentes")} icon="folder" tone="green" />
          <ModuleCard title="Agenda y recursos" description={safeText(profile.specialist_layers.agenda_and_resources.join(" • "), "Sin agenda")} icon="calendar" tone="blue" />
          <ModuleCard title="Documentos / compliance" description={safeText(profile.specialist_layers.documents_compliance.join(" • "), "Sin compliance")} icon="shield" tone="gold" />
          <ModuleCard title="Pricing y cotizaciones" description={safeText(profile.specialist_layers.pricing_and_quotes.join(" • "), "Sin pricing")} icon="money" tone="slate" />
          <ModuleCard title="Postventa y recurrencia" description={safeText(profile.specialist_layers.post_sale_and_recurrence.join(" • "), "Sin recurrencia")} icon="refresh" tone="green" />
          <ModuleCard title="Automatizaciones que mueven dinero" description={safeText(profile.specialist_layers.money_automations.join(" • "), "Sin automatizaciones duras")} icon="money" tone="gold" />
        </div>
      </Section>

      <Section title="Subplaybooks y pruebas e2e" subtitle="La capa que prueba que cada vertical ya opera como negocio y no solo como preset." icon="wand">
        <div className="grid gap-4 xl:grid-cols-2">
          {rows.playbookRows.length ? <DataTable columns={["Subvertical", "Foco"]} rows={rows.playbookRows} /> : <ModuleCard title="Sin subplaybooks" description="No hay subplaybooks visibles para esta vertical." icon="alert" tone="red" />}
          {rows.e2eRows.length ? <DataTable columns={["#", "Prueba e2e", "Estado"]} rows={rows.e2eRows} /> : <ModuleCard title="Sin pruebas e2e" description="No hay pruebas e2e definidas para esta vertical." icon="alert" tone="red" />}
        </div>
      </Section>
    </>
  );
}
