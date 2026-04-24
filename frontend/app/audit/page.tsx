import { Shell } from "@/app/components/layout/shell";
import { Section, StatCard } from "@/app/components/primitives/cards";
import { DataTable } from "@/app/components/primitives/data-display";
import { formatNumber, safeText } from "../lib/ui";
import { getLogs } from "@/app/lib/data/analytics";
export default async function AuditPage() {
  const logs = await getLogs();
  return <Shell title="Auditoría por organización" subtitle="Bitácora visible para cambios y eventos sensibles."><div className="grid gap-4 md:grid-cols-2"><StatCard label="Eventos visibles" value={formatNumber(logs.length)} hint="Registros recuperados" icon="logs" tone="blue" /><StatCard label="Eventos sensibles" value={formatNumber(logs.filter((item)=>/login|mfa|secret|publish|approve|pause|reactivate/i.test(JSON.stringify(item))).length)} hint="Acciones importantes" icon="shield" tone="gold" /></div><Section title="Bitácora reciente" subtitle="Una sola tabla para seguir cambios humanos y eventos críticos." icon="logs"><DataTable columns={["Evento","Detalle","Cuándo"]} rows={logs.map((item,index:number)=>[safeText(item.kind||item.event||`evento-${index}`), safeText(item.message||item.summary||JSON.stringify(item.payload||item)), safeText(item.created_at||item.timestamp||item.updated_at)])} /></Section></Shell>;
}
