import { ModuleCard, Section, StatCard } from "@/app/components/primitives/cards";
import { DataTable } from "@/app/components/primitives/data-display";
import { formatNumber, safeText } from "@/app/lib/ui";
import type { VerticalsPageModel } from "@/features/vertical-selection/server/getVerticalsPageModel";

export function TransactionalMotorPanel({ model }: { model: VerticalsPageModel }) {
  const { profile, rows } = model;
  if (!profile) return null;
  return (
    <>
      <Section title="Runtime ejecutable" subtitle="La vertical ya no solo define objetos: ahora expone lógica de ejecución para estados, pricing, capacidad, recurrencia, documentos, matching y automatizaciones." icon="tool">
        <div className="grid gap-4 xl:grid-cols-3">
          <ModuleCard title="Pipeline machine" description={safeText(((profile.vertical_runtime.pipeline_machine.states as string[]) || []).join(" • "), "Sin estados ejecutables")} icon="flow" tone="green" footer={<div className="text-xs text-slate-400">At risk: {safeText(profile.vertical_runtime.pipeline_machine.at_risk_state)}</div>} />
          <ModuleCard title="Pricing engine" description={safeText(((profile.vertical_runtime.pricing_engine.quote_types as string[]) || []).join(" • "), "Sin quote runtime")} icon="money" tone="gold" footer={<div className="text-xs text-slate-400">Base: {safeText(profile.vertical_runtime.pricing_engine.pricing_basis)}</div>} />
          <ModuleCard title="Resource capacity" description={safeText(((profile.vertical_runtime.resource_capacity.resource_types as string[]) || []).join(" • "), "Sin capacidad")} icon="calendar" tone="blue" footer={<div className="text-xs text-slate-400">Cola: {safeText(profile.vertical_runtime.resource_capacity.priority_queue)}</div>} />
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-2">
          {rows.runtimeTransitionRows.length ? <DataTable columns={["From", "To", "Trigger", "Efecto"]} rows={rows.runtimeTransitionRows} /> : <ModuleCard title="Sin transiciones" description="No hay state machine visible para esta vertical." icon="alert" tone="red" />}
          {rows.pricingRuleRows.length ? <DataTable columns={["#", "Regla", "Efecto"]} rows={rows.pricingRuleRows} /> : <ModuleCard title="Sin pricing rules" description="No hay reglas de pricing visibles para esta vertical." icon="alert" tone="red" />}
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-3">
          {rows.recurrenceRows.length ? <DataTable columns={["Política", "Días", "Ancla"]} rows={rows.recurrenceRows} /> : <ModuleCard title="Sin recurrencia" description="No hay políticas de recurrencia visibles." icon="alert" tone="red" />}
          {rows.kpiFormulaRows.length ? <DataTable columns={["KPI", "Fórmula"]} rows={rows.kpiFormulaRows} /> : <ModuleCard title="Sin fórmulas" description="No hay fórmulas de KPI visibles." icon="alert" tone="red" />}
          {rows.automationPolicyRows.length ? <DataTable columns={["Trigger", "Acciones", "Goal"]} rows={rows.automationPolicyRows} /> : <ModuleCard title="Sin money automations" description="No hay políticas runtime de automatización visibles." icon="alert" tone="red" />}
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-2">
          <ModuleCard title="Document flow" description={safeText(((profile.vertical_runtime.document_flow.required_documents as string[]) || []).join(" • "), "Sin documentos runtime")} icon="folder" tone="slate" />
          <ModuleCard title="Matching engine" description={safeText(((profile.vertical_runtime.matching_engine.rules as string[]) || []).join(" • "), "Sin matching runtime")} icon="spark" tone="green" />
        </div>
      </Section>

      <Section title="Motor v12 full transaccional" subtitle="Núcleo común que convierte el runtime vertical en sistema de registro, ejecución, cobro, cumplimiento y continuidad por vertical." icon="stack">
        <div className="grid gap-4 xl:grid-cols-4">
          <StatCard label="Versión" value={safeText(profile.transactional_motor_v12.version, "v12")} hint="Contrato transaccional" icon="rocket" tone="green" />
          <StatCard label="Aggregate root" value={safeText(profile.transactional_motor_v12.aggregate_root, "Sin root")} hint={safeText(profile.transactional_motor_v12.main_business_entity, "Sin entidad")} icon="stack" tone="blue" />
          <StatCard label="Unidad transaccional" value={safeText(profile.transactional_motor_v12.transaction_unit, "Sin unidad")} hint="Unidad mínima de operación" icon="tool" tone="gold" />
          <StatCard label="Comandos" value={formatNumber(profile.transactional_motor_v12.command_catalog.length)} hint="Catálogo ejecutable" icon="flow" tone="slate" />
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-3">
          <ModuleCard title="Primitivas" description={safeText((((profile.transactional_motor_v12.transaction_primitives.commands as string[]) || []).slice(0, 8)).join(" • "), "Sin comandos")} icon="flow" tone="green" footer={<div className="text-xs text-slate-400">Eventos: {safeText((((profile.transactional_motor_v12.transaction_primitives.events as string[]) || []).slice(0, 6)).join(" • "), "Sin eventos")}</div>} />
          <ModuleCard title="Finanzas" description={safeText((((profile.transactional_motor_v12.finance.money_objects as string[]) || [])).join(" • "), "Sin objetos de dinero")} icon="money" tone="gold" footer={<div className="text-xs text-slate-400">Cobro: {safeText((((profile.transactional_motor_v12.finance.collection_modes as string[]) || [])).join(" • "), "Sin cobro")}</div>} />
          <ModuleCard title="Operación" description={safeText((((profile.transactional_motor_v12.operations.resource_locking as string[]) || [])).join(" • "), "Sin locking")} icon="calendar" tone="blue" footer={<div className="text-xs text-slate-400">Board: {safeText((((profile.transactional_motor_v12.operations.dispatch_or_schedule_board as string[]) || [])).join(" • "), "Sin board")}</div>} />
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-2">
          <ModuleCard title="Compliance y auditoría" description={safeText((((profile.transactional_motor_v12.audit_compliance.consent_gates as string[]) || [])).join(" • "), "Sin gates")} icon="shield" tone="slate" footer={<div className="text-xs text-slate-400">Evidencia: {safeText((((profile.transactional_motor_v12.audit_compliance.required_evidence as string[]) || [])).join(" • "), "Sin evidencia")}</div>} />
          <ModuleCard title="Orquestación" description={safeText((((profile.transactional_motor_v12.orchestration.sagas as string[]) || [])).join(" • "), "Sin sagas")} icon="wand" tone="green" footer={<div className="text-xs text-slate-400">Guards: {safeText((((profile.transactional_motor_v12.orchestration.money_guards as string[]) || [])).join(" • "), "Sin guards")}</div>} />
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-2">
          {rows.v12CommandRows.length ? <DataTable columns={["#", "Command", "Writes", "Guard"]} rows={rows.v12CommandRows} /> : <ModuleCard title="Sin command catalog" description="No hay comandos visibles para esta vertical." icon="alert" tone="red" />}
          {rows.v12EventRows.length ? <DataTable columns={["#", "Event", "Updates", "Next action"]} rows={rows.v12EventRows} /> : <ModuleCard title="Sin event catalog" description="No hay eventos visibles para esta vertical." icon="alert" tone="red" />}
        </div>
        <div className="mt-4">
          {rows.v12ViewRows.length ? <DataTable columns={["Vista", "Qué controla"]} rows={rows.v12ViewRows} /> : <ModuleCard title="Sin transaction views" description="No hay vistas transaccionales visibles para esta vertical." icon="alert" tone="red" />}
        </div>
      </Section>
    </>
  );
}
