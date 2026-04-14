import { generateExecutiveReportAction } from "../actions";
import { DataTable, Section, Shell, StatCard } from "../components";
import { getBots, getConversationReviews, getDirectorMode, getExecutiveReports } from "../lib/waos";
import { getCurrentOrganizationId } from "../lib/session";
import { formatNumber, safeText } from "../lib/ui";

function defaultRange() {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 7);
  return { start: start.toISOString().slice(0, 10), end: end.toISOString().slice(0, 10) };
}

export default async function InsightsPage() {
  const [director, reports, reviews, bots, organizationId] = await Promise.all([getDirectorMode(), getExecutiveReports(), getConversationReviews(), getBots(), getCurrentOrganizationId()]);
  const summary = director.summary || {};
  const range = defaultRange();
  return (
    <Shell title="Resultados y salud del servicio" subtitle="Aquí ves el resumen ejecutivo, el pulso del servicio y ahora también un flujo real para generar y descargar reportes PDF.">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Conversaciones" value={formatNumber(Number(summary.total_conversations || 0))} hint="Volumen medido" icon="chat" tone="blue" />
        <StatCard label="Escaladas" value={formatNumber(Number(summary.human_handoffs || 0))} hint="Casos que requirieron apoyo humano" icon="support" tone="gold" />
        <StatCard label="Reportes" value={formatNumber(reports.length)} hint="Reportes ejecutivos generados" icon="layers" tone="green" />
        <StatCard label="Revisiones" value={formatNumber(reviews.length)} hint="Conversaciones evaluadas" icon="check" tone="slate" />
      </div>
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
