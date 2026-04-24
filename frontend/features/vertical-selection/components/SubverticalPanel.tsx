import { SegmentedLinks } from "@/app/components/navigation";
import { ModuleCard, Section, StatCard } from "@/app/components/primitives/cards";
import { formatNumber, safeText } from "@/app/lib/ui";
import type { VerticalsPageModel } from "@/features/vertical-selection/server/getVerticalsPageModel";

export function SubverticalPanel({ model }: { model: VerticalsPageModel }) {
  const { profile, subverticalSegmented } = model;
  const activeSubvertical = profile?.selected_subvertical || null;
  if (!profile?.is_strongest_vertical) return null;
  return (
    <Section title="Subvertical 10x" subtitle="Empaque táctico para bajar la vertical a una subvertical vendible, operable y medible." icon="spark">
      {subverticalSegmented.length ? <SegmentedLinks items={subverticalSegmented} /> : null}
      <div className="mt-4 grid gap-4 xl:grid-cols-4">
        <StatCard label="Score subvertical" value={safeText(activeSubvertical?.strength_score, "-")} hint={safeText(activeSubvertical?.growth_motion, "Sin motion")} icon="rocket" tone="green" />
        <StatCard label="Buyer" value={safeText(activeSubvertical?.buyer, profile.buyer.primary)} hint="Quién compra primero" icon="client" tone="blue" />
        <StatCard label="Servicios pack" value={formatNumber(activeSubvertical?.service_bundle.length || 0)} hint="Bundle seed aplicable" icon="folder" tone="gold" />
        <StatCard label="KPIs pack" value={formatNumber(activeSubvertical?.kpi_pack.length || 0)} hint="Métricas subverticales" icon="stats" tone="slate" />
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <ModuleCard title="Promesa subvertical" description={safeText(activeSubvertical?.promise, "Sin promesa subvertical")} icon="wand" tone="green" footer={<div className="text-xs text-slate-400">Monetiza: {safeText(activeSubvertical?.monetizes.join(" • "), "Sin monetización")}</div>} />
        <ModuleCard title="Growth loops 10x" description={safeText(profile.ten_x_growth_loops.join(" • "), "Sin loops")} icon="refresh" tone="blue" footer={<div className="text-xs text-slate-400">Comandos: {safeText(activeSubvertical?.recommended_commands.join(" • "), safeText((profile.ten_x_operational_pack.recommended_commands as string[] || []).join(" • ")))}</div>} />
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <ModuleCard title="Bundle de servicios" description={safeText(activeSubvertical?.service_bundle.join(" • "), "Sin bundle")} icon="stack" tone="green" />
        <ModuleCard title="Preguntas de calificación" description={safeText(activeSubvertical?.qualification_questions.join(" • "), "Sin preguntas")} icon="support" tone="gold" />
        <ModuleCard title="Objeciones" description={safeText(activeSubvertical?.objections.join(" • "), "Sin objeciones")} icon="alert" tone="slate" />
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <ModuleCard title="Automatizaciones prioritarias" description={safeText(activeSubvertical?.automation_priorities.join(" • "), "Sin automatizaciones")} icon="bot" tone="blue" />
        <ModuleCard title="KPIs del pack" description={safeText(activeSubvertical?.kpi_pack.join(" • "), "Sin KPIs")} icon="stats" tone="green" />
        <ModuleCard title="Assets de lanzamiento" description={safeText(activeSubvertical?.launch_assets.join(" • "), "Sin assets")} icon="check" tone="gold" />
      </div>
    </Section>
  );
}
