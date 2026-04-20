import Link from "next/link";
import { Badge, ContextTip, DataTable, PermissionGate, Section, Shell, StatCard } from "../components";
import { canUseSupportMode, canViewObservability, roleLabel } from "../lib/permissions";
import { requireSession } from "../lib/session";
import { formatNumber, safeText } from "../lib/ui";
import { getBots, getConversations, getDeadLetters, getIntegrationSyncRuns, getIntegrations, getObservability, getQueue, getRuntimeCallbacks } from "../lib/waos";

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }

export default async function OperationsPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const view = first(params.view) || "overview";
  const session = await requireSession();
  const role = session?.user.global_role;

  const [deadLetters, callbacks, syncRuns, bots, conversations, integrations, observability, queue] = await Promise.all([
    getDeadLetters(),
    getRuntimeCallbacks(),
    getIntegrationSyncRuns(),
    getBots(),
    getConversations(),
    getIntegrations(),
    getObservability(),
    getQueue(),
  ]);

  const pausedBots = bots.filter((item) => String(item.status || "").toLowerCase() === "paused" || Number(item.ai_paused || 0) === 1);
  const humanCases = conversations.filter((item) => String(item.status || "").toLowerCase() === "human_takeover");
  const degradedIntegrations = integrations.filter((item) => String(item.health_status || item.status || "").toLowerCase() === "degraded");
  const integrationAlerts = integrations.filter((item) => !["active", "configured", "connected"].includes(String(item.status || "").toLowerCase()));
  const queueCount = (queue.automation_jobs || []).reduce((acc: number, item) => acc + Number(item.count || 0), 0);
  const deadLetterCount = deadLetters.jobs.length + deadLetters.outbox.length;

  return (
    <Shell title="Operaciones" subtitle="Estado, soporte y operación técnica viven ahora en una sola capa. Cambias de vista sin sentir que saltaste a otro producto." action={<Link href="/inbox?filter=human" className="primary-btn">Abrir inbox humano</Link>}>
      <ContextTip>Tu rol visible ahora es {roleLabel(role)}. Esta pantalla consolida overview, estado interno y soporte para que el equipo no tenga que adivinar en qué módulo buscar cada cosa.</ContextTip>

      <div className="flex flex-wrap gap-2 rounded-3xl border border-white/[0.08] bg-white/[0.03] p-2">
        {[
          ["overview", "Resumen"],
          ["observability", "Estado interno"],
          ["support", "Soporte"],
          ["runtime", "Runtime"],
        ].map(([id, label]) => <Link key={id} href={`/operations?view=${id}`} className={view === id ? "primary-btn" : "secondary-btn"}>{label}</Link>)}
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Bots pausados" value={formatNumber(pausedBots.length)} hint="Impacto directo en conversaciones" icon="bot" tone={pausedBots.length ? "gold" : "green"} />
        <StatCard label="Casos humanos" value={formatNumber(humanCases.length)} hint="Takeovers visibles" icon="support" tone="gold" />
        <StatCard label="Alertas integraciones" value={formatNumber(integrationAlerts.length)} hint="Conexiones a revisar" icon="plug" tone={integrationAlerts.length ? "red" : "blue"} />
        <StatCard label="Jobs en cola" value={formatNumber(queueCount)} hint="Trabajo pendiente" icon="layers" tone="slate" />
      </div>

      {view === "overview" ? (
        <Section title="Resumen operacional" subtitle="La foto corta para decidir dónde entrar primero." icon="stats">
          <DataTable columns={["Tema", "Valor"]} rows={[
            ["Dead letters", formatNumber(deadLetterCount)],
            ["Callbacks", formatNumber(callbacks.length)],
            ["Sync runs", formatNumber(syncRuns.length)],
            ["Integraciones degradadas", formatNumber(degradedIntegrations.length)],
          ]} />
        </Section>
      ) : null}

      {view === "observability" ? (
        <PermissionGate allowed={canViewObservability(role)} fallback={<Section title="Acceso restringido" subtitle="Tu rol no debería abrir observabilidad interna completa." icon="alert"><div className="text-sm text-slate-300">Pide apoyo a operación o seguridad si necesitas esta vista.</div></Section>}>
          <Section title="Estado interno" subtitle="Lectura rápida de errores, cola e integraciones." icon="alert">
            <DataTable columns={["Tema", "Valor"]} rows={[
              ["Fallos recientes", formatNumber((observability.recent_failures || []).length)],
              ["Integraciones con alerta", formatNumber(integrationAlerts.length)],
              ["Jobs en cola", formatNumber(queueCount)],
            ]} />
          </Section>
        </PermissionGate>
      ) : null}

      {view === "support" ? (
        <PermissionGate allowed={canUseSupportMode(role)} fallback={<Section title="Acceso restringido" subtitle="Tu rol no debería usar el modo soporte." icon="support"><div className="text-sm text-slate-300">El modo soporte se mantiene reducido por seguridad operativa.</div></Section>}>
          <Section title="Soporte" subtitle="Una lista corta y segura de lo que soporte debe revisar ahora." icon="support">
            <DataTable columns={["Tipo", "Detalle"]} rows={[
              ...pausedBots.slice(0, 6).map((item) => ["Bot pausado", `${safeText(item.name)} · ${safeText(item.status)}`]),
              ...humanCases.slice(0, 6).map((item) => ["Takeover humano", `${safeText(item.contact_name)} · ${safeText(item.summary)}`]),
              ...degradedIntegrations.slice(0, 6).map((item) => ["Integración degradada", `${safeText(item.name)} · ${safeText(item.health_status || item.status)}`]),
            ]} />
          </Section>
        </PermissionGate>
      ) : null}

      {view === "runtime" ? (
        <Section title="Runtime" subtitle="Callbacks, dead letters y sync runs sin separarlos en pantallas distintas." icon="refresh">
          <DataTable columns={["Tipo", "Estado", "Detalle"]} rows={[
            ...[...deadLetters.jobs, ...deadLetters.outbox].slice(0, 8).map((item) => [safeText(item.type), <Badge key={safeText(item.id)} tone="red">{safeText(item.status)}</Badge>, safeText(item.error || item.detail)]),
            ...callbacks.slice(0, 6).map((item) => ["Callback", safeText(item.status), safeText(item.target || item.kind || item.type)]),
            ...syncRuns.slice(0, 6).map((item) => ["Sync run", safeText(item.status), safeText(item.provider || item.integration_id || item.id)]),
          ]} />
        </Section>
      ) : null}
    </Shell>
  );
}
