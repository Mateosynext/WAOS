import { Shell } from "@/app/components/layout/shell";
import { Section, StatCard } from "@/app/components/primitives/cards";
import { DataTable } from "@/app/components/primitives/data-display";
import { formatNumber, safeText } from "../lib/ui";
import { getDailyAnalytics, getObservability } from "@/app/lib/data/analytics";

export default async function UsagePage() {
  const [daily, observability] = await Promise.all([getDailyAnalytics(), getObservability()]);
  const metrics = daily.metrics || {};
  return (
    <Shell title="Uso y rendimiento" subtitle="Una vista simple para entender consumo, actividad y señales tempranas de problemas o sobrecarga.">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Mensajes" value={formatNumber(Number(metrics.messages || 0))} hint="Actividad del día" icon="chat" tone="green" />
        <StatCard label="Conversaciones" value={formatNumber(Number(metrics.conversations || 0))} hint="Sesiones activas" icon="stats" tone="blue" />
        <StatCard label="Fallos recientes" value={formatNumber((observability.recent_failures || []).length)} hint="Puntos a vigilar" icon="alert" tone="red" />
        <StatCard label="Logs recientes" value={formatNumber((observability.recent_logs || []).length)} hint="Pulso del sistema" icon="logs" tone="gold" />
      </div>
      <Section title="Métricas del día" subtitle="Datos que ayudan a detectar si el uso creció, cayó o necesita análisis más profundo." icon="usage">
        <DataTable columns={["Métrica", "Valor"]} rows={Object.entries(metrics).map(([key, value]) => [key, safeText(value)])} />
      </Section>
    </Shell>
  );
}
