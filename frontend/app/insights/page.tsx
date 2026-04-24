import { generateExecutiveReportAction } from "@/app/actions/reports";
import { StatusPill } from "@/app/components/feedback";
import { Shell } from "@/app/components/layout/shell";
import { Section, StatCard } from "@/app/components/primitives/cards";
import { DataTable } from "@/app/components/primitives/data-display";
import { Badge } from "@/app/components/primitives/shared";
import { getDirectorMode, getExecutiveReports, getWhatsappDeliveryTruth } from "@/app/lib/data/analytics";
import { getBots } from "@/app/lib/data/bots";
import { getConversationReviews } from "@/app/lib/data/inbox";
import { getCurrentOrganizationId } from "../lib/session";
import { formatDateTime, formatNumber, safeText } from "../lib/ui";

function defaultRange() {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 7);
  return { start: start.toISOString().slice(0, 10), end: end.toISOString().slice(0, 10) };
}

function formatPercent(value: unknown) {
  const number = Number(value || 0);
  if (Number.isNaN(number)) return "0%";
  return `${number.toFixed(2)}%`;
}

function formatSeconds(value: unknown) {
  const number = Number(value);
  if (!Number.isFinite(number) || number < 0) return "-";
  if (number < 60) return `${number.toFixed(0)} s`;
  const minutes = number / 60;
  if (minutes < 60) return `${minutes.toFixed(1)} min`;
  const hours = minutes / 60;
  return `${hours.toFixed(1)} h`;
}

function asArray(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object") : [];
}

export default async function InsightsPage() {
  const [director, reports, reviews, bots, organizationId, deliveryTruth] = await Promise.all([
    getDirectorMode(),
    getExecutiveReports(),
    getConversationReviews(),
    getBots(),
    getCurrentOrganizationId(),
    getWhatsappDeliveryTruth(undefined, { windowHours: 24 * 7, limit: 20 }),
  ]);
  const summary = director.summary || {};
  const range = defaultRange();
  const truthSummary = (deliveryTruth.summary || {}) as Record<string, unknown>;
  const truthBreakdowns = (deliveryTruth.breakdowns || {}) as Record<string, unknown>;
  const truthAlerts = asArray(deliveryTruth.alerts);
  const truthRecent = asArray(deliveryTruth.recent_messages);
  const reconciliation = (deliveryTruth.reconciliation || {}) as Record<string, unknown>;
  return (
    <Shell title="Resultados y salud del servicio" subtitle="Aquí ves el resumen ejecutivo, el pulso del servicio y ahora también la verdad real de delivery sobre WhatsApp, de aceptación a delivered/read/failed.">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Conversaciones" value={formatNumber(Number(summary.total_conversations || 0))} hint="Volumen medido" icon="chat" tone="blue" />
        <StatCard label="Escaladas" value={formatNumber(Number(summary.human_handoffs || 0))} hint="Casos que requirieron apoyo humano" icon="support" tone="gold" />
        <StatCard label="Reportes" value={formatNumber(reports.length)} hint="Reportes ejecutivos generados" icon="layers" tone="green" />
        <StatCard label="Revisiones" value={formatNumber(reviews.length)} hint="Conversaciones evaluadas" icon="check" tone="slate" />
      </div>
      <Section title="Delivery truth de WhatsApp" subtitle="Esta capa separa aceptación del provider de la verdad del canal: sent, delivered, read y failed, con tasas reales, tiempos y alertas operativas." icon="channel" aside={<div className="flex flex-wrap items-center gap-2"><Badge tone="sky">Ventana 7d</Badge>{Boolean(reconciliation.performed) ? <Badge tone="gold">Reconciliado</Badge> : <Badge tone="slate">Live projection</Badge>}</div>}>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <StatCard label="Aceptados" value={formatNumber(Number(truthSummary.accepted_count || 0))} hint="API aceptó el envío" icon="play" tone="slate" />
          <StatCard label="Delivery rate" value={formatPercent(truthSummary.delivery_rate)} hint={`${formatNumber(Number(truthSummary.delivered_count || 0))} delivered/read`} icon="check" tone="green" />
          <StatCard label="Read rate" value={formatPercent(truthSummary.read_rate)} hint={`${formatNumber(Number(truthSummary.read_count || 0))} leídos sobre delivered`} icon="insights" tone="blue" />
          <StatCard label="Fail rate" value={formatPercent(truthSummary.fail_rate)} hint={`${formatNumber(Number(truthSummary.failed_count || 0))} fallidos`} icon="alert" tone="red" />
          <StatCard label="Pendientes" value={formatNumber(Number(truthSummary.pending_truth_count || 0))} hint="Aún sin verdad final del canal" icon="clock" tone="gold" />
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="T2 Delivered" value={formatSeconds(truthSummary.avg_time_to_delivered_seconds)} hint="Desde aceptación hasta delivered" icon="refresh" tone="green" />
          <StatCard label="T2 Read" value={formatSeconds(truthSummary.avg_time_to_read_seconds)} hint="Desde aceptación hasta read" icon="insights" tone="blue" />
          <StatCard label="Sent reales" value={formatNumber(Number(truthSummary.sent_count || 0))} hint="Ya vistos por webhook de canal o inferidos por lifecycle" icon="channel" tone="slate" />
          <StatCard label="Read/Accepted" value={formatPercent(truthSummary.read_rate_over_accepted)} hint="Lectura sobre base aceptada" icon="target" tone="gold" />
        </div>
      </Section>
      <Section title="Alertado por comportamiento real del canal" subtitle="Se disparan alertas cuando el fail rate o el delivery rate muestran degradación real por número, plantilla o vertical." icon="alert">
        <DataTable
          columns={["Severidad", "Dimensión", "Métrica", "Observado", "Detalle"]}
          rows={truthAlerts.map((item) => [
            <StatusPill key={`${safeText(item.title)}-severity`} status={safeText(item.severity, "warning")} />,
            safeText(item.dimension),
            safeText(item.metric),
            `${formatPercent(item.observed_value)} / umbral ${formatPercent(item.threshold)}`,
            safeText(item.body),
          ])}
        />
      </Section>
      <Section title="Breakdown por plantilla" subtitle="Aquí ves cuáles plantillas cargan el fail rate real y qué tan rápido llegan y se leen." icon="layers">
        <DataTable
          columns={["Plantilla", "Aceptados", "Delivery", "Read", "Fail", "T2 Delivered", "T2 Read"]}
          rows={asArray(truthBreakdowns.by_template).map((item) => [
            safeText(item.label),
            formatNumber(Number(item.accepted_count || 0)),
            formatPercent(item.delivery_rate),
            formatPercent(item.read_rate),
            formatPercent(item.fail_rate),
            formatSeconds(item.avg_time_to_delivered_seconds),
            formatSeconds(item.avg_time_to_read_seconds),
          ])}
        />
      </Section>
      <div className="grid gap-4 xl:grid-cols-2">
        <Section title="Breakdown por número" subtitle="Útil para detectar números con degradación o problemas de reputación/canal." icon="client">
          <DataTable
            columns={["Número", "Aceptados", "Delivery", "Read", "Fail", "Pendientes"]}
            rows={asArray(truthBreakdowns.by_number).map((item) => [
              safeText(item.label),
              formatNumber(Number(item.accepted_count || 0)),
              formatPercent(item.delivery_rate),
              formatPercent(item.read_rate),
              formatPercent(item.fail_rate),
              formatNumber(Number(item.pending_truth_count || 0)),
            ])}
          />
        </Section>
        <Section title="Breakdown por vertical" subtitle="Sirve para ver si la degradación está concentrada en un tipo de negocio o playbook." icon="briefcase">
          <DataTable
            columns={["Vertical", "Aceptados", "Delivery", "Read", "Fail", "Pendientes"]}
            rows={asArray(truthBreakdowns.by_vertical).map((item) => [
              safeText(item.label),
              formatNumber(Number(item.accepted_count || 0)),
              formatPercent(item.delivery_rate),
              formatPercent(item.read_rate),
              formatPercent(item.fail_rate),
              formatNumber(Number(item.pending_truth_count || 0)),
            ])}
          />
        </Section>
      </div>
      <Section title="Mensajes recientes con truth status" subtitle="Cada fila ya queda reconciliada por provider_message_id para poder explicar la vida real del mensaje después de salir a WhatsApp." icon="logs">
        <DataTable
          columns={["Provider message", "Estado", "Plantilla", "Número", "Aceptado", "Delivered", "Read", "Error"]}
          rows={truthRecent.map((item) => [
            safeText(item.provider_message_id),
            <StatusPill key={safeText(item.provider_message_id)} status={safeText(item.current_status)} />,
            safeText(item.template_name, "Sin plantilla"),
            safeText(item.phone_number_id),
            formatDateTime(safeText(item.accepted_at, "")),
            item.delivered_at ? `${formatDateTime(safeText(item.delivered_at, ""))} · ${formatSeconds(item.time_to_delivered_seconds)}` : "-",
            item.read_at ? `${formatDateTime(safeText(item.read_at, ""))} · ${formatSeconds(item.time_to_read_seconds)}` : "-",
            item.last_error_message ? `${safeText(item.last_error_message)}${item.last_error_code ? ` (${safeText(item.last_error_code)})` : ""}` : "-",
          ])}
        />
      </Section>
      <Section title="Generar reporte ejecutivo" subtitle="Dispara la generación desde producto y descarga el PDF cuando ya exista." icon="folder">
        <form action={generateExecutiveReportAction} className="grid gap-3 md:grid-cols-4">
          <input type="hidden" name="organization_id" value={organizationId || ""} />
          <input type="hidden" name="redirect_to" value="/insights" />
          <label className="field-label">Inicio<input className="field-input" type="date" name="period_start" defaultValue={range.start} required /></label>
          <label className="field-label">Fin<input className="field-input" type="date" name="period_end" defaultValue={range.end} required /></label>
          <label className="field-label">Bot<select className="field-input" name="bot_id" defaultValue=""><option value="">Todos</option>{bots.map((bot) => <option key={String(bot.id)} value={String(bot.id)}>{safeText(bot.name)}</option>)}</select></label>
          <div className="flex items-end"><button className="primary-btn w-full" type="submit">Generar PDF</button></div>
        </form>
      </Section>
      <Section title="Reportes listos" subtitle="Cada fila deja una descarga real del PDF generado por backend." icon="layers">
        <DataTable columns={["Reporte", "Periodo", "PDF"]} rows={reports.map((item) => [safeText(String(item.id || "")), `${safeText(String(item.period_start || ""))} → ${safeText(String(item.period_end || ""))}`, <a key={String(item.id)} href={`/api/reports/executive/${encodeURIComponent(String(item.id || ""))}/pdf`} className="secondary-btn">Descargar PDF</a>])} />
      </Section>
      <Section title="Narrativa ejecutiva" subtitle="Un resumen legible para tomar decisiones sin meterte a detalle técnico." icon="briefcase">
        <DataTable columns={["Punto", "Detalle"]} rows={(director.narrative || []).map((item, index: number) => [safeText(item.title, `Punto ${index + 1}`), safeText(item.body || item.detail)])} />
      </Section>
      <Section title="Revisiones recientes" subtitle="Muestras de conversaciones revisadas para encontrar mejoras o riesgos." icon="chat">
        <DataTable columns={["Conversación", "Resultado", "Comentario"]} rows={reviews.map((item) => [safeText(item.conversation_id), safeText(item.result), safeText(item.comment)])} />
      </Section>
    </Shell>
  );
}
