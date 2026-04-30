import Link from "next/link";
import { ContextTip, EmptyActionState, OperationalDegradedBanner, hasOperationalFailures } from "@/app/components/feedback";
import { Shell } from "@/app/components/layout/shell";
import { SecondaryNav } from "@/app/components/navigation";
import { Section, StatCard } from "@/app/components/primitives/cards";
import { DataTable } from "@/app/components/primitives/data-display";
import { formatNumber, safeText } from "../lib/ui";
import { getQueueState } from "@/app/lib/data/analytics";
import { getDeadLettersState, getRuntimeCallbacksState, getSchedulerState } from "@/app/lib/data/integrations";

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }
export default async function SchedulerPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const view = first(params.view) || "queue";
  const [schedulerState, queueState, deadLettersState, callbacksState] = await Promise.all([getSchedulerState(), getQueueState(), getDeadLettersState(), getRuntimeCallbacksState()]);
  const criticalStates = [schedulerState, queueState, deadLettersState, callbacksState];
  if (hasOperationalFailures(criticalStates)) {
    return (
      <Shell title="Scheduler y colas" subtitle="Operación técnica con bloqueo explícito cuando el backend no responde." action={<><Link href="/status" className="secondary-btn">Estado</Link><Link href="/operations" className="primary-btn">Operacion</Link></>}>
        <OperationalDegradedBanner states={criticalStates} block title="Scheduler bloqueado por backend degradado" description="No se muestran colas, dead letters ni callbacks desde fallbacks. Esta pantalla queda bloqueada para evitar que una cola rota parezca vacía." />
      </Shell>
    );
  }
  const scheduler = schedulerState.data;
  const queue = queueState.data;
  const deadLetters = deadLettersState.data;
  const callbacks = callbacksState.data;
  const queueTotal = (queue.automation_jobs || []).reduce((acc: number, item) => acc + Number(item.count || 0), 0);
  const integrationQueueTotal = (queue.integration_sync || []).reduce((acc: number, item) => acc + Number(item.count || 0), 0);
  const deadTotal = Number((deadLetters.jobs || []).length) + Number((deadLetters.outbox || []).length);
  const callbackRows = callbacks.map((item) => [safeText(item.kind, "callback"), safeText(item.health_status || item.status || "-"), safeText(item.updated_at || item.last_run_at || "-")]);
  return (
    <Shell title="Scheduler y colas" subtitle="La operacion tecnica ya no vive escondida. Aqui se separan trabajos programados, acumulacion, callbacks, dead letters y syncs de integraciones para mantenimiento real." action={<><Link href="/status" className="secondary-btn">Estado</Link><Link href="/operations" className="primary-btn">Operacion</Link></>}>
      <SecondaryNav items={[{ href: "/scheduler?view=queue", label: "Cola", active: view === "queue" },{ href: "/scheduler?view=dead", label: "Dead letters", active: view === "dead" },{ href: "/scheduler?view=callbacks", label: "Callbacks", active: view === "callbacks" }]} />
      <ContextTip>Esta vista separa trabajo diario de mantenimiento. Si algo se acumula o se queda atorado, primero mira cola, luego dead letters, despues callbacks y por ultimo syncs de integraciones.</ContextTip>
      <div className="grid gap-4 md:grid-cols-5">
        <StatCard label="Vencen ahora" value={formatNumber(scheduler.due_now)} hint="Jobs para este momento" icon="clock" tone="gold" />
        <StatCard label="Cola total" value={formatNumber(queueTotal)} hint="Trabajo pendiente" icon="layers" tone="blue" />
        <StatCard label="Syncs integración" value={formatNumber(scheduler.integration_due_now)} hint="Corridas listas para ejecutar" icon="plug" tone="green" />
        <StatCard label="Retries integración" value={formatNumber(scheduler.integration_retries)} hint="Conectores degradados" icon="refresh" tone="red" />
        <StatCard label="Dead letters" value={formatNumber(deadTotal)} hint="Requieren reintento o limpieza" icon="support" tone="slate" />
      </div>
      {view === "queue" ? <Section title="Conteo por tipo" subtitle="La cola sirve cuando puedes ver rapido en que clase de trabajo se esta acumulando presion." icon="layers">{scheduler.counts.length || integrationQueueTotal ? <DataTable columns={["Tipo", "Cantidad"]} rows={[...scheduler.counts.map((item) => [safeText(item.kind), formatNumber(item.count)]), ...queue.integration_sync.map((item) => [`integration:${safeText(item.kind)}`, formatNumber(item.count)])]} /> : <EmptyActionState title="No hay conteos visibles" description="Cuando el scheduler publique mas detalle por tipo, aparecera aqui en formato estable." />}</Section> : null}
      {view === "queue" && scheduler.next_integration ? <Section title="Siguiente sync de integración" subtitle="Ayuda a ver cuándo vuelve a correr el proveedor sin entrar a logs." icon="plug"><DataTable columns={["Proveedor", "Próximo intento", "Estado"]} rows={[[safeText(String(scheduler.next_integration.provider || scheduler.next_integration.id || "-")), safeText(String(scheduler.next_integration.next_sync_at || "-")), safeText(String(scheduler.next_integration.status || "-"))]]} /></Section> : null}
      {view === "dead" ? <Section title="Dead letters y reintentos" subtitle="Esta vista ayuda a separar lo que fallo del request path normal para que el frontend no pague el costo." icon="alert">{deadTotal ? <DataTable columns={["Canal", "Detalle", "Estado"]} rows={[...deadLetters.jobs.map((item) => [safeText(item.kind), safeText(item.detail), safeText(item.status)]), ...deadLetters.outbox.map((item) => [safeText(item.kind), safeText(item.detail), safeText(item.status)])]} /> : <EmptyActionState title="No hay dead letters visibles" description="Buena senal: por ahora no se ven mensajes o trabajos atrapados en esta capa." primaryAction={<Link href="/status" className="primary-btn">Ver estado</Link>} />}</Section> : null}
      {view === "callbacks" ? <Section title="Callbacks y salud de ejecucion" subtitle="Webhooks, callbacks y procesos derivados necesitan una lectura compacta para soporte y mantenimiento." icon="refresh">{callbackRows.length ? <DataTable columns={["Callback", "Estado", "Ultimo movimiento"]} rows={callbackRows} /> : <EmptyActionState title="No hay callbacks visibles" description="Cuando existan callbacks o procesos encadenados, los veras aqui con estado y fecha." primaryAction={<Link href="/integrations" className="primary-btn">Ver integraciones</Link>} />}</Section> : null}
    </Shell>
  );
}
