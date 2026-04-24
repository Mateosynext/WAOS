import Link from "next/link";
import { ContextTip, EmptyActionState } from "@/app/components/feedback";
import { Shell } from "@/app/components/layout/shell";
import { ModuleCard, Section, StatCard } from "@/app/components/primitives/cards";
import { DataTable, StageRail } from "@/app/components/primitives/data-display";
import { Badge } from "@/app/components/primitives/shared";
import BotScopeSwitcher from "../components/BotScopeSwitcher";
import { getCurrentBotId } from "../lib/session";
import { formatDateTime, formatNumber, safeText } from "../lib/ui";
import { getV14PublishSchedules, getV15PublishRuns } from "@/app/lib/data/analytics";
import { getBots, getReleaseReadiness, getReleases, getTraceability } from "@/app/lib/data/bots";

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }

function releaseStage(value: unknown) {
  const raw = String(value || "draft").toLowerCase();
  if (raw.includes("publish")) return "published";
  if (raw.includes("approve")) return "approved";
  if (raw.includes("review")) return "review";
  return "draft";
}

export default async function LaunchCenterPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const bots = await getBots();
  const botId = first(params.bot_id) || (await getCurrentBotId()) || "";

  if (!botId) {
    return (
      <Shell
        title="Launch center"
        subtitle="Readiness, schedules, runs y trazabilidad viven aquí cuando necesitas coordinar una salida real sin saltar por varias pantallas."
      >
        <EmptyActionState
          title="Primero selecciona un bot"
          description="Launch center necesita contexto de bot para mostrar readiness, release flow, schedules y runs relacionados."
          primaryAction={<BotScopeSwitcher bots={bots} selectedBotId={botId} redirectTo="/launch-center" />}
          secondaryAction={<Link href="/bots" className="secondary-btn">Ver bots</Link>}
        />
      </Shell>
    );
  }

  const [readiness, releases, schedules, runs, traceability] = await Promise.all([
    getReleaseReadiness(botId),
    getReleases(botId),
    getV14PublishSchedules(),
    getV15PublishRuns(),
    getTraceability(botId),
  ]);

  const readinessSummary = (readiness.summary || {}) as Record<string, unknown>;
  const blockers = readiness.blockers || [];
  const warnings = readiness.warnings || [];
  const filteredSchedules = schedules.filter((item) => String(item.bot_id || "") === botId);
  const filteredRuns = runs.filter((item) => String(item.bot_id || item.related_bot_id || "") === botId);
  const staged = {
    draft: releases.filter((item) => releaseStage(item.status) === "draft").length,
    review: releases.filter((item) => releaseStage(item.status) === "review").length,
    approved: releases.filter((item) => releaseStage(item.status) === "approved").length,
    published: releases.filter((item) => releaseStage(item.status) === "published").length,
  };

  return (
    <Shell
      title="Launch center"
      subtitle="Coordina readiness, salidas programadas y runs recientes desde una sola historia operativa. Esta vista reduce la distancia entre pedir release, calendarizar y confirmar que sí salió bien."
      action={<Link href={`/releases?bot_id=${encodeURIComponent(botId)}`} className="primary-btn">Abrir releases</Link>}
    >
      <ContextTip title="Qué resuelve esta vista">
        Releases sigue siendo el workflow formal. Launch center te da la lectura transversal: qué bloquea la salida, qué está programado y qué corrió hace poco para este bot.
      </ContextTip>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Semáforo" value={safeText(readinessSummary.status, "sin dato")} hint={`${formatNumber(Number(readinessSummary.score || 0))} puntos · ${formatNumber(Number(readinessSummary.blocking_count || 0))} bloqueos`} icon="alert" tone={String(readinessSummary.status || "").toLowerCase() === "green" ? "green" : String(readinessSummary.status || "").toLowerCase() === "amber" ? "gold" : "red"} />
        <StatCard label="Releases" value={formatNumber(releases.length)} hint="Solicitudes visibles para este bot" icon="layers" tone="blue" />
        <StatCard label="Schedules" value={formatNumber(filteredSchedules.length)} hint="Publicaciones calendarizadas" icon="clock" tone="gold" />
        <StatCard label="Runs recientes" value={formatNumber(filteredRuns.length)} hint="Ejecuciones ligadas al bot" icon="refresh" tone="slate" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Section title="Readiness para salir" subtitle="Checklist corto para saber si el bot está listo para salir o si aún faltan piezas críticas." icon="rocket">
          <StageRail
            activeStep={blockers.length ? "review" : warnings.length ? "approved" : "published"}
            steps={[
              { id: "draft", label: `Borrador (${formatNumber(staged.draft)})`, detail: "Cambios listos para evaluación." },
              { id: "review", label: `Revisión (${formatNumber(staged.review)})`, detail: blockers.length ? `${formatNumber(blockers.length)} bloqueo(s) siguen abiertos.` : "Sin bloqueos críticos visibles." },
              { id: "approved", label: `Aprobado (${formatNumber(staged.approved)})`, detail: warnings.length ? `${formatNumber(warnings.length)} advertencia(s) todavía conviene revisar.` : "Semáforo sin advertencias visibles." },
              { id: "published", label: `Publicado (${formatNumber(staged.published)})`, detail: "Monitoreo posterior a salida y trazabilidad." },
            ]}
          />
        </Section>

        <Section title="Qué hacer ahora" subtitle="Acciones sugeridas según la señal de readiness y el estado de publicaciones." icon="target">
          <div className="grid gap-4 sm:grid-cols-2">
            <ModuleCard title="Corregir bloqueos" description={blockers.length ? blockers.slice(0, 2).map((item) => safeText(item)).join(" · ") : "No se ven bloqueos críticos en la respuesta actual."} icon="alert" tone={blockers.length ? "red" : "green"} footer={<Link href={`/releases?bot_id=${encodeURIComponent(botId)}`} className="secondary-btn">Abrir releases</Link>} />
            <ModuleCard title="Validar programación" description={filteredSchedules.length ? `Hay ${formatNumber(filteredSchedules.length)} schedule(s) ligados a este bot.` : "No hay publicaciones calendarizadas para este bot todavía."} icon="clock" tone={filteredSchedules.length ? "gold" : "slate"} footer={<Link href="/scheduler" className="secondary-btn">Abrir scheduler</Link>} />
            <ModuleCard title="Ver bot" description="Si necesitas editar comportamiento, assets o variables antes de salir, vuelve al detalle del bot." icon="bot" tone="blue" footer={<Link href={`/bots/${botId}`} className="secondary-btn">Ir al bot</Link>} />
            <ModuleCard title="Trazabilidad" description={`Builds: ${formatNumber((traceability.builds || []).length)} · Runs: ${formatNumber((traceability.runs || []).length)}.`} icon="logs" tone="slate" footer={<Link href={`/audit`} className="secondary-btn">Ver audit</Link>} />
          </div>
        </Section>
      </div>

      <Section title="Checklist y alertas" subtitle="La vista operativa de blockers, warnings y checks sin abrir varias secciones manualmente." icon="check">
        {(readiness.checklist_items || []).length ? (
          <DataTable
            columns={["Check", "Resultado", "Detalle", "Acción"]}
            rows={(readiness.checklist_items || []).slice(0, 12).map((item) => [
              safeText(item.label || item.key),
              <Badge key={`${item.key}-badge`} tone={item.ok ? "green" : item.required ? "red" : "gold"}>{item.ok ? "OK" : item.required ? "Bloquea" : "Advertencia"}</Badge>,
              safeText(item.detail, "Sin detalle"),
              item.href ? <Link key={`${item.key}-href`} href={String(item.href)} className="secondary-btn">Abrir</Link> : <span className="mono-pill">Sin acción directa</span>,
            ])}
          />
        ) : (
          <EmptyActionState title="No llegó checklist desde backend" description="Launch center ya está listo para mostrar el checklist, pero este bot no expuso checks en la respuesta actual." />
        )}
      </Section>

      <div className="grid gap-6 xl:grid-cols-2">
        <Section title="Schedules programados" subtitle="Publicaciones calendarizadas para este bot." icon="clock">
          {filteredSchedules.length ? (
            <DataTable
              columns={["Schedule", "Cuando", "Estado"]}
              rows={filteredSchedules.slice(0, 12).map((item) => [safeText(item.id), formatDateTime(safeText(item.scheduled_for || item.next_run_at, "")), safeText(item.status)])}
            />
          ) : (
            <EmptyActionState title="Sin schedules para este bot" description="Todavía no hay publicaciones programadas asociadas al bot activo." />
          )}
        </Section>

        <Section title="Runs recientes" subtitle="Las últimas ejecuciones para validar si la salida efectivamente corrió y cómo terminó." icon="refresh">
          {filteredRuns.length ? (
            <DataTable
              columns={["Run", "Resultado", "Fecha"]}
              rows={filteredRuns.slice(0, 12).map((item) => [safeText(item.id || item.schedule_id), <Badge key={`${item.id}-result`} tone={String(item.status || item.result || "").toLowerCase().includes("success") ? "green" : String(item.status || item.result || "").toLowerCase().includes("fail") ? "red" : "slate"}>{safeText(item.status || item.result)}</Badge>, formatDateTime(safeText(item.created_at || item.updated_at, ""))])}
            />
          ) : (
            <EmptyActionState title="Sin runs recientes" description="No aparecieron ejecuciones relacionadas con este bot en la respuesta actual." />
          )}
        </Section>
      </div>
    </Shell>
  );
}
