import { Badge, DataTable, Section, Shell, StatCard } from "../components";
import { formatNumber, safeText } from "../lib/ui";
import { getDeadLetters, getIntegrationSyncRuns, getRuntimeCallbacks } from "../lib/waos";

export default async function OperationsPage() {
  const [deadLetters, callbacks, syncRuns] = await Promise.all([getDeadLetters(), getRuntimeCallbacks(), getIntegrationSyncRuns()]);
  return (
    <Shell title="Operación" subtitle="Aquí revisas procesos que se quedaron atorados, callbacks y sincronizaciones importantes para que el sistema siga estable.">
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Callbacks" value={formatNumber(callbacks.length)} hint="Eventos externos registrados" icon="refresh" tone="blue" />
        <StatCard label="Dead letters" value={formatNumber(deadLetters.jobs.length + deadLetters.outbox.length)} hint="Procesos detenidos" icon="alert" tone="red" />
        <StatCard label="Sync runs" value={formatNumber(syncRuns.length)} hint="Actualizaciones ejecutadas" icon="plug" tone="gold" />
      </div>
      <Section title="Dead letters" subtitle="Lo que falló y necesita reintento o revisión." icon="alert">
        <DataTable columns={["Tipo", "Estado", "Detalle"]} rows={[...deadLetters.jobs, ...deadLetters.outbox].map((item) => [safeText(item.type), <Badge key={safeText(item.id)} tone="red">{safeText(item.status)}</Badge>, safeText(item.error || item.detail)])} />
      </Section>
    </Shell>
  );
}
