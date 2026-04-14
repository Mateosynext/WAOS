import { DataTable, Section, Shell, StatCard } from "../components";
import { formatNumber, safeText } from "../lib/ui";
import { getLogs, getObservability } from "../lib/waos";

export default async function LogsPage() {
  const [logs, observability] = await Promise.all([getLogs(), getObservability()]);
  const failures = observability.recent_failures || [];
  return (
    <Shell title="Registros" subtitle="Un lugar claro para ver errores, eventos técnicos y fallas recientes sin meterte al servidor.">
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Logs" value={formatNumber(logs.length)} hint="Entradas visibles" icon="logs" tone="blue" />
        <StatCard label="Fallos recientes" value={formatNumber(failures.length)} hint="Problemas detectados" icon="alert" tone="red" />
        <StatCard label="Salud general" value={safeText(observability.totals?.status, 'sin dato')} hint="Pulso actual del sistema" icon="shield" tone="gold" />
      </div>
      <Section title="Eventos recientes" subtitle="Úsalos para entender qué pasó y dónde revisar primero." icon="logs">
        <DataTable columns={["Fecha", "Tipo", "Nivel", "Detalle"]} rows={logs.map((item) => [safeText(item.created_at), safeText(item.event || item.kind), safeText(item.details.level || item.payload.level), safeText(item.message || item.summary)])} />
      </Section>
    </Shell>
  );
}
