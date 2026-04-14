import Link from "next/link";
import { DataTable, ModuleCard, Section, Shell, StatCard } from "../components";
import { formatNumber, safeText } from "../lib/ui";
import { getI18nAnalytics, getI18nConfig, getPlaybooks, getWhatsappFlows } from "../lib/waos";

export default async function FlowsPage() {
  const [playbooks, whatsappFlows, i18nConfig, i18nAnalytics] = await Promise.all([getPlaybooks(), getWhatsappFlows(), getI18nConfig(), getI18nAnalytics()]);
  return (
    <Shell title="Respuestas y flujos" subtitle="Todo lo que define cómo conversa el bot: guías, flujos, variantes y cobertura por idioma." action={<Link href="/bot-studio" className="secondary-btn">Volver a crear bot</Link>}>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Playbooks" value={formatNumber(playbooks.length)} hint="Guías de respuesta" icon="flow" tone="green" />
        <StatCard label="Flows de WhatsApp" value={formatNumber(whatsappFlows.length)} hint="Formularios o pasos guiados" icon="channel" tone="blue" />
        <StatCard label="Idiomas" value={formatNumber(Object.keys(i18nConfig || {}).length)} hint="Cobertura configurada" icon="channel" tone="gold" />
        <StatCard label="Cobertura i18n" value={safeText(i18nAnalytics.summary?.coverage ? `${i18nAnalytics.summary.coverage}%` : null, '-')} hint="Traducción o variantes listas" icon="stats" tone="slate" />
      </div>
      <Section title="Playbooks" subtitle="La base de respuestas y comportamiento para distintos escenarios." icon="flow">
        <DataTable columns={["Playbook", "Objetivo", "Estado"]} rows={playbooks.map((item) => [safeText(item.name), safeText(item.objective), safeText(item.status)])} />
      </Section>
      <Section title="Flows de WhatsApp" subtitle="Pasos guiados que ayudan a pedir datos o cerrar acciones con menos fricción." icon="channel">
        <DataTable columns={["Flow", "Tipo", "Estado"]} rows={whatsappFlows.map((item) => [safeText(item.name), safeText(item.flow_type), safeText(item.status)])} />
      </Section>
    </Shell>
  );
}
