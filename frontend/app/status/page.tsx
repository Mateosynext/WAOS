import Link from "next/link";
import { DataTable, PermissionGate, Section, Shell, StatCard } from "../components";
import { canViewObservability, roleLabel } from "../lib/permissions";
import { getSession } from "../lib/session";
import { formatNumber } from "../lib/ui";
import { getIntegrations, getObservability, getQueue } from "../lib/waos";

export default async function StatusPage() {
  const session = await getSession();
  const role = session?.user.global_role;
  const [observability, queue, integrations] = await Promise.all([getObservability(), getQueue(), getIntegrations()]);
  const integrationAlerts = integrations.filter((item) => !["active", "configured", "connected"].includes(String(item.status || "").toLowerCase()));
  const queueCount = (queue.automation_jobs || []).reduce((acc: number, item) => acc + Number(item.count || 0), 0);
  return <Shell title="Estado interno" subtitle="Una lectura rápida para saber si la plataforma está sana." action={<Link href="/operations" className="primary-btn">Abrir operación</Link>}><div className="mb-4 text-sm text-slate-300">Tu rol visible ahora es {roleLabel(role)}.</div><PermissionGate allowed={canViewObservability(role)} fallback={<Section title="Acceso restringido" subtitle="Tu rol no deberia abrir observabilidad interna completa." icon="alert"><div className="text-sm text-slate-300">Pide apoyo a operacion, soporte o seguridad si necesitas esta vista.</div></Section>}><div className="grid gap-4 md:grid-cols-3"><StatCard label="Fallos recientes" value={formatNumber((observability.recent_failures || []).length)} hint="Errores visibles" icon="alert" tone="red" /><StatCard label="Integraciones con alerta" value={formatNumber(integrationAlerts.length)} hint="Conexiones a revisar" icon="plug" tone="gold" /><StatCard label="Jobs en cola" value={formatNumber(queueCount)} hint="Trabajo pendiente" icon="layers" tone="blue" /></div><Section title="Mapa rápido" subtitle="Qué mirar primero." icon="route"><DataTable columns={["Tema", "Valor"]} rows={[["Errores recientes", formatNumber((observability.recent_failures || []).length)], ["Integraciones con alerta", formatNumber(integrationAlerts.length)], ["Jobs en cola", formatNumber(queueCount)]]} /></Section></PermissionGate></Shell>;
}
