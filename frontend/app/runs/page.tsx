import { Shell } from "@/app/components/layout/shell";
import { Section, StatCard } from "@/app/components/primitives/cards";
import { DataTable } from "@/app/components/primitives/data-display";
import { formatNumber, safeText } from "../lib/ui";
import { getObservability, getRuns } from "@/app/lib/data/analytics";

export default async function RunsPage() {
  const [runs, observability] = await Promise.all([getRuns(), getObservability()]);
  return (
    <Shell title="Runs" subtitle="Aquí revisas ejecuciones del sistema y puedes detectar rápido cuáles fueron bien y cuáles necesitan seguimiento.">
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Runs" value={formatNumber(runs.length)} hint="Ejecuciones registradas" icon="play" tone="blue" />
        <StatCard label="Fallos recientes" value={formatNumber((observability.recent_failures || []).length)} hint="Problemas detectados" icon="alert" tone="red" />
        <StatCard label="Logs recientes" value={formatNumber((observability.recent_logs || []).length)} hint="Eventos recientes" icon="logs" tone="gold" />
      </div>
      <Section title="Ejecuciones" subtitle="Listado simple para revisar estado, fecha y referencia." icon="play">
        <DataTable columns={["Run", "Estado", "Fecha", "Detalle"]} rows={runs.map((item) => [safeText(item.id), safeText(item.status), safeText(item.created_at), safeText(item.summary || item.detail)])} />
      </Section>
    </Shell>
  );
}
