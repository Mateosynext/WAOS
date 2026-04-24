import Link from "next/link";
import BotScopeSwitcher from "../components/BotScopeSwitcher";
import { ContextTip, EmptyActionState, PermissionGate } from "@/app/components/feedback";
import { Shell } from "@/app/components/layout/shell";
import { SecondaryNav } from "@/app/components/navigation";
import { ModuleCard, Section, StatCard } from "@/app/components/primitives/cards";
import { DataTable, StageRail } from "@/app/components/primitives/data-display";
import { Badge } from "@/app/components/primitives/shared";
import ConfirmSubmitButton from "../components/ConfirmSubmitButton";
import { approveReleaseAction, publishReleaseAction, requestReleaseAction } from "@/app/actions/releases";
import { canApproveRelease, canPublishRelease, roleLabel } from "../lib/permissions";
import { getCurrentBotId, getSession } from "../lib/session";
import { formatNumber, safeText } from "../lib/ui";
import { getV14PublishSchedules, getV15PublishRuns } from "@/app/lib/data/analytics";
import { getBots, getReleaseReadiness, getReleases, getTraceability } from "@/app/lib/data/bots";

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }
function releaseStatus(item: { status?: string | null }) { const raw = String(item.status || "draft").toLowerCase(); return raw === "requested" ? "review" : raw; }

export default async function ReleasesPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const stage = first(params.stage) || "all";
  const session = await getSession();
  const role = session?.user.global_role;
  const bots = await getBots();
  const botId = first(params.bot_id) || (await getCurrentBotId()) || "";
  const [releases, traceability, schedules, runs, readiness] = await Promise.all([getReleases(botId || undefined), getTraceability(botId || undefined), getV14PublishSchedules(), getV15PublishRuns(), getReleaseReadiness(botId || undefined)]);
  const filtered = releases.filter((item) => stage === "all" ? true : releaseStatus(item) === stage);
  const readinessSummary = (readiness.summary || {}) as Record<string, unknown>;
  const filteredSchedules = schedules.filter((item) => !botId || String(item.bot_id || "") === botId);
  const filteredRuns = runs.filter((item) => !botId || String(item.bot_id || "") === botId || String(item.related_bot_id || "") === botId);
  const counts = { draft: releases.filter((item) => releaseStatus(item) === "draft").length, review: releases.filter((item) => releaseStatus(item) === "review").length, approved: releases.filter((item) => releaseStatus(item) === "approved").length, published: releases.filter((item) => releaseStatus(item) === "published").length };

  return (
    <Shell title="Releases" subtitle="Releases ya no compite con setup ni con integraciones: aquí solo se solicita, aprueba y publica con trazabilidad del cambio." action={botId ? <Link href={`/bots/${botId}/versions`} className="primary-btn">Ver versiones</Link> : <Link href="/bot-studio?mode=create" className="primary-btn">Crear asistente operativo</Link>}>
      <SecondaryNav items={[{ href: `/releases?stage=all${botId ? `&bot_id=${encodeURIComponent(botId)}` : ""}`, label: `Todo (${formatNumber(releases.length)})`, active: stage === "all" },{ href: `/releases?stage=draft${botId ? `&bot_id=${encodeURIComponent(botId)}` : ""}`, label: `Borrador (${formatNumber(counts.draft)})`, active: stage === "draft" },{ href: `/releases?stage=review${botId ? `&bot_id=${encodeURIComponent(botId)}` : ""}`, label: `Revision (${formatNumber(counts.review)})`, active: stage === "review" },{ href: `/releases?stage=approved${botId ? `&bot_id=${encodeURIComponent(botId)}` : ""}`, label: `Aprobado (${formatNumber(counts.approved)})`, active: stage === "approved" },{ href: `/releases?stage=published${botId ? `&bot_id=${encodeURIComponent(botId)}` : ""}`, label: `Publicado (${formatNumber(counts.published)})`, active: stage === "published" }]} />
      <ContextTip>Tu rol visible ahora es {roleLabel(role)}. Bot Studio prepara el cambio; Integraciones conecta y prueba; aquí solo publicas con request, aprobación y evidencia.</ContextTip>
      {!botId ? <EmptyActionState title="Primero selecciona un asistente operativo" description="Releases, trazabilidad y diferencias contra publicado necesitan un contexto explícito del asistente operativo." primaryAction={<BotScopeSwitcher bots={bots} selectedBotId={botId} redirectTo="/releases?stage=all" />} secondaryAction={<Link href="/bots" className="secondary-btn">Ver asistentes operativos</Link>} /> : <>
      <div className="grid gap-4 md:grid-cols-5">
        <StatCard label="Solicitudes" value={formatNumber(releases.length)} hint="Releases registradas" icon="layers" tone="blue" />
        <StatCard label="Aprobadas" value={formatNumber(counts.approved)} hint="Listas para salir" icon="check" tone="green" />
        <StatCard label="Programadas" value={formatNumber(filteredSchedules.length)} hint="Publicaciones calendarizadas" icon="clock" tone="gold" />
        <StatCard label="Builds visibles" value={formatNumber((traceability.builds || []).length)} hint="Construcciones relacionadas" icon="tool" tone="slate" />
        <StatCard label="Semáforo" value={safeText(String(readinessSummary.status || "sin dato"))} hint={`${formatNumber(Number(readinessSummary.score || 0))} puntos · ${formatNumber(Number(readinessSummary.blocking_count || 0))} bloqueos`} icon="alert" tone={String(readinessSummary.status || "").toLowerCase() === "green" ? "green" : String(readinessSummary.status || "").toLowerCase() === "amber" ? "gold" : "red"} />
      </div>
      <Section title="Semáforo de producción" subtitle="Este semáforo sí bloquea publish si el asistente operativo todavía no cumple lo crítico para salir." icon="alert">
        <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-4">
          {(readiness.checklist_items || []).map((item) => {
            const label = safeText(String(item.label || item.key || "check"));
            const detail = safeText(String(item.detail || ""));
            const ok = Boolean(item.ok);
            const href = String(item.href || "");
            const required = Boolean(item.required);
            return (
              <ModuleCard
                key={label}
                title={label}
                description={detail}
                icon={ok ? "check" : "alert"}
                tone={ok ? "green" : required ? "red" : "gold"}
                footer={href ? <Link href={href} className="secondary-btn">Abrir</Link> : undefined}
              />
            );
          })}
        </div>
      </Section>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Section title="Solicitar release" subtitle="Antes faltaba la pantalla operativa. Ahora puedes pedir release con título y notas desde producto." icon="route">
          <form action={requestReleaseAction} className="space-y-3">
            <input type="hidden" name="bot_id" value={botId} />
            <input type="hidden" name="redirect_to" value={`/releases?stage=all&bot_id=${encodeURIComponent(botId)}`} />
            <label className="field-label">Título<input className="field-input" type="text" name="title" defaultValue="Release candidate" required /></label>
            <label className="field-label">Notas<textarea className="field-input min-h-28" name="notes" defaultValue="Checklist operativo, diff y validación antes de publicar." /></label>
{Boolean(readinessSummary.can_request_release) ? <button className="primary-btn" type="submit">Solicitar release</button> : <span className="mono-pill">Falta cerrar bloqueos antes de solicitar release</span>}
          </form>
        </Section>
        <Section title="Flujo recomendado" subtitle="Un release sano sigue la misma historia todas las veces." icon="route"><StageRail activeStep={stage === "all" ? "draft" : stage} steps={[{ id: "draft", label: "Borrador", detail: "Cambios listos para revisión." },{ id: "review", label: "Revisión", detail: "Se valida impacto, riesgo y cambios." },{ id: "approved", label: "Aprobado", detail: "El cambio ya puede salir." },{ id: "published", label: "Publicado", detail: "Se observa el estado y se deja trazabilidad." }]} /></Section>
      </div>
      <Section title="Tabla de release" subtitle="Cada release mantiene acciones de aprobación y publicación dentro del mismo workflow." icon="layers">
        {filtered.length ? <DataTable columns={["Release", "Estado", "Checklist", "Acciones"]} rows={filtered.map((item) => { const status = releaseStatus(item); const checklist = item.checklist || {}; return [<div key={item.id}><div className="font-medium text-white">{safeText(item.id)}</div><div className="text-xs text-slate-400">{safeText(item.created_at || item.updated_at || "sin fecha")}</div></div>, <Badge key={`${item.id}-status`} tone={status === "approved" ? "green" : status === "published" ? "sky" : status === "review" ? "gold" : "slate"}>{safeText(item.status)}</Badge>, `${checklist.validation_ok ? "validación" : "revisar"} · ${checklist.channel_ready ? "canal" : "sin canal"} · ${checklist.payments_ready ? "pagos" : "sin pagos"}`, <div key={`${item.id}-actions`} className="flex flex-wrap gap-2"><PermissionGate allowed={canApproveRelease(role)} fallback={<span className="mono-pill">Sin permiso de aprobación</span>}><form action={approveReleaseAction}><input type="hidden" name="release_id" value={item.id} /><input type="hidden" name="redirect_to" value={`/releases?stage=${encodeURIComponent(stage)}&bot_id=${encodeURIComponent(botId)}`} /><ConfirmSubmitButton message="¿Seguro que quieres aprobar este release?">Aprobar</ConfirmSubmitButton></form></PermissionGate><PermissionGate allowed={canPublishRelease(role)} fallback={<span className="mono-pill">Sin permiso de publicación</span>}>{Boolean(readinessSummary.can_publish_release) ? <form action={publishReleaseAction}><input type="hidden" name="release_id" value={item.id} /><input type="hidden" name="redirect_to" value={`/releases?stage=${encodeURIComponent(stage)}&bot_id=${encodeURIComponent(botId)}`} /><ConfirmSubmitButton className="primary-btn" message="¿Seguro que quieres publicar este release a producción?">Publicar</ConfirmSubmitButton></form> : <span className="mono-pill">Publish bloqueado por semáforo</span>}</PermissionGate></div>]; })} /> : <EmptyActionState title="No hay releases para este filtro" description="La vista queda limpia y útil. Cambia el filtro o crea una solicitud." primaryAction={<Link href={`/releases?stage=all&bot_id=${encodeURIComponent(botId)}`} className="primary-btn">Ver todo</Link>} secondaryAction={<Link href={`/bots/${botId}`} className="secondary-btn">Ver bot</Link>} />}
      </Section>
      <div className="grid gap-6 xl:grid-cols-2">
        <Section title="Publicaciones programadas" subtitle="Los endpoints de schedules y runs ya tienen una vista operativa básica dentro de producto." icon="clock">
          <DataTable columns={["Schedule", "Cuando", "Estado"]} rows={filteredSchedules.map((item) => [safeText(String(item.id || "")), safeText(String(item.scheduled_for || item.next_run_at || "")), safeText(String(item.status || ""))])} />
        </Section>
        <Section title="Runs recientes" subtitle="Trazabilidad corta de ejecuciones de publicación." icon="refresh">
          <DataTable columns={["Run", "Resultado", "Fecha"]} rows={filteredRuns.slice(0, 20).map((item) => [safeText(String(item.id || item.schedule_id || "")), safeText(String(item.status || item.result || "")), safeText(String(item.created_at || item.updated_at || ""))])} />
        </Section>
      </div>
      </>}
    </Shell>
  );
}
