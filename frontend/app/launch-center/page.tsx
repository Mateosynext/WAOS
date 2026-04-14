import Link from "next/link";
import { DataTable, ModuleCard, Section, Shell, StatCard } from "../components";
import { formatNumber, safeText, yesNo } from "../lib/ui";
import { getHealth, getObservability, getQueue, getSecurityPolicy, getSystemStatus } from "../lib/waos";

export default async function LaunchCenterPage() {
  const [health, status, observability, queue, policy] = await Promise.all([getHealth(), getSystemStatus(), getObservability(), getQueue(), getSecurityPolicy()]);
  return (
    <Shell title="Centro de lanzamiento" subtitle="Revisa si todo está listo para salir o si conviene corregir algo antes de publicar cambios o conectar más clientes." action={<Link href="/releases" className="secondary-btn">Ver releases</Link>}>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Salud" value={safeText(health.status, 'sin dato')} hint="Respuesta principal del backend" icon="shield" tone="green" />
        <StatCard label="Sistema" value={safeText(status.status, 'sin dato')} hint="Estado general" icon="dashboard" tone="blue" />
        <StatCard label="Jobs en cola" value={formatNumber((queue.automation_jobs || []).length)} hint="Trabajo pendiente antes de salir" icon="clock" tone="gold" />
        <StatCard label="Fallos recientes" value={formatNumber((observability.recent_failures || []).length)} hint="Señales de riesgo" icon="alert" tone="red" />
      </div>
      <Section title="Chequeo previo a publicar" subtitle="Una lista ejecutiva de puntos que normalmente conviene revisar antes de dejar algo en vivo." icon="rocket">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <ModuleCard title="API responde" description={`Estado actual: ${safeText(health.status, 'sin dato')}.`} icon="check" tone="green" />
          <ModuleCard title="Sistema estable" description={`Estado general: ${safeText(status.status, 'sin dato')}.`} icon="shield" tone="blue" />
          <ModuleCard title="Seguridad mínima" description={`MFA: ${yesNo(policy.require_mfa)} · Firma webhook: ${yesNo(policy.webhook_signature_required)}.`} icon="shield" tone="gold" />
          <ModuleCard title="Operación despejada" description={`${formatNumber((queue.automation_jobs || []).length)} tipos de jobs en cola y ${formatNumber((observability.recent_failures || []).length)} fallos recientes.`} icon="clock" tone="slate" />
        </div>
      </Section>
      <Section title="Señales recientes" subtitle="Úsalas para decidir si hoy conviene publicar o esperar a estabilizar." icon="logs">
        <DataTable columns={["Tipo", "Detalle"]} rows={(observability.recent_failures || []).map((item) => [safeText(item.kind || item.type), safeText(item.message || item.detail)])} />
      </Section>
    </Shell>
  );
}
