import { ModuleCard, Section, StatCard } from "@/app/components/primitives/cards";
import { DataTable } from "@/app/components/primitives/data-display";
import { Badge } from "@/app/components/primitives/shared";
import { formatNumber, safeText } from "@/app/lib/ui";
import { tierLabel, toneForTier, waveLabel, type VerticalsPageModel } from "@/features/vertical-selection/server/getVerticalsPageModel";

export function VerticalProfile({ model }: { model: VerticalsPageModel }) {
  const { profile } = model;
  if (!profile) return null;
  return (
    <>
      <Section title="Resumen ejecutivo" subtitle="Lectura rápida para dirección, producto, ventas y onboarding." icon="briefcase">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Vertical" value={profile.name} hint={safeText(profile.description)} icon="stack" tone="green" />
          <StatCard label="Tier" value={tierLabel(profile.portfolio_tier)} hint="Prioridad del portafolio" icon="layers" tone={toneForTier(profile.portfolio_tier)} />
          <StatCard label="Subverticales" value={formatNumber(profile.subverticals.length)} hint="Cobertura de la familia" icon="folder" tone="blue" />
          <StatCard label="Integraciones" value={formatNumber(profile.recommended_integrations.length)} hint="Base operativa sugerida" icon="plug" tone="gold" />
          <StatCard label="Ola de endurecimiento" value={waveLabel(profile.hardening_model.wave)} hint="Prioridad recomendada" icon="rocket" tone="slate" />
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-3">
          <ModuleCard title="Tesis maestra" description={safeText(profile.master_thesis, "Sin tesis definida.")} icon="target" tone="green" />
          <ModuleCard title="Buyer principal" description={safeText(profile.buyer.primary, "Sin buyer principal.")} icon="client" tone="blue" footer={<div className="text-xs text-slate-400">Secundarios: {safeText(profile.buyer.secondary.join(" • "), "Sin secundarios")}</div>} />
          <ModuleCard title="Problema estructural" description={safeText(profile.problem, "Sin problema definido.")} icon="alert" tone="gold" />
        </div>
      </Section>

      <Section title="One-pager comercial" subtitle="La versión vendible de la vertical: qué vende, qué promete y cómo se empaqueta." icon="rocket">
        <div className="grid gap-4 xl:grid-cols-2">
          <ModuleCard title={safeText(profile.one_pager.headline, profile.name)} description={safeText(profile.one_pager.thesis, "Sin tesis comercial.")} icon="wand" tone="green" footer={<div className="text-xs text-slate-400">Promesa: {safeText(profile.one_pager.promise, "Sin promesa")}</div>} />
          <ModuleCard title="Qué monetiza" description={safeText(profile.one_pager.monetizes.join(" • "), "Sin monetización definida.")} icon="money" tone="gold" footer={<div className="text-xs text-slate-400">Empaque: {safeText(profile.one_pager.packaging.join(" • "), "Sin empaque")}</div>} />
          <ModuleCard title="Problema comercial" description={safeText(profile.one_pager.problem, "Sin problema")} icon="support" tone="blue" />
          <ModuleCard title="Cuidado estratégico" description={safeText(profile.one_pager.strategic_care, "Sin notas estratégicas")} icon="shield" tone="slate" />
        </div>
      </Section>

      <Section title="Demo flow" subtitle="Historia mínima que debe poder mostrarse como producto listo." icon="play">
        <DataTable columns={["Paso", "Qué valida WAOS"]} rows={profile.demo_flow.map((step, index) => [`${index + 1}`, step])} />
      </Section>

      <Section title="Esquema de objetos nativos" subtitle="No son solo chats y contactos: es el modelo operativo del negocio." icon="folder">
        <div className="grid gap-4 xl:grid-cols-3">
          <ModuleCard title="Core" description={safeText(profile.native_objects.core.join(" • "), "Sin objetos core")} icon="stack" tone="green" />
          <ModuleCard title="Comerciales" description={safeText(profile.native_objects.commercial.join(" • "), "Sin objetos comerciales")} icon="money" tone="blue" />
          <ModuleCard title="Operativos" description={safeText(profile.native_objects.operations.join(" • "), "Sin objetos operativos")} icon="tool" tone="gold" />
        </div>
      </Section>

      <Section title="Vertical duro / contrato de dominio" subtitle="La capa que convierte una vertical bonita en sistema especialista reusable." icon="shield">
        <div className="grid gap-4 xl:grid-cols-2">
          <ModuleCard title="Entidad reina" description={safeText(profile.hardening_model.entity_queen, "Sin entidad reina")} icon="target" tone="green" footer={<div className="text-xs text-slate-400">Meta: {safeText(profile.hardening_model.goal, "Sin meta")}</div>} />
          <ModuleCard title="Módulos reusables" description={safeText(profile.hardening_model.reusable_modules.join(" • "), "Sin módulos")} icon="stack" tone="blue" footer={<Badge tone="green">{waveLabel(profile.hardening_model.wave)}</Badge>} />
          <ModuleCard title="Especialización mínima" description={safeText(profile.hardening_model.minimum_viable_hardening.join(" • "), "Sin mínimo viable")} icon="check" tone="gold" />
          <ModuleCard title="Checklist duro" description={safeText(profile.hardening_model.hard_checklist.join(" • "), "Sin checklist")} icon="shield" tone="slate" />
        </div>
      </Section>
    </>
  );
}
