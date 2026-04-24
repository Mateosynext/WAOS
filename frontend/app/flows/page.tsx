import Link from "next/link";
import { Shell } from "@/app/components/layout/shell";
import { ModuleCard, Section, StatCard } from "@/app/components/primitives/cards";
import { DataTable } from "@/app/components/primitives/data-display";
import { formatNumber, safeText } from "../lib/ui";
import { getI18nAnalytics, getI18nConfig } from "@/app/lib/data/analytics";
import { getPlaybooks } from "@/app/lib/data/commerce";
import { getWhatsappFlows } from "@/app/lib/data/inbox";

export default async function FlowsPage() {
  const [playbooks, whatsappFlows, i18nConfig, i18nAnalytics] = await Promise.all([getPlaybooks(), getWhatsappFlows(), getI18nConfig(), getI18nAnalytics()]);
  const analyticsSummary = i18nAnalytics && typeof i18nAnalytics === "object" && i18nAnalytics.summary && typeof i18nAnalytics.summary === "object" ? i18nAnalytics.summary : null;
  const coverageValue = analyticsSummary?.coverage != null ? `${analyticsSummary.coverage}%` : null;
  return (
    <Shell title="Respuestas y flujos" subtitle="Todo lo que define cómo conversa el bot: guías, flujos, variantes y cobertura por idioma." action={<Link href="/bot-studio" className="secondary-btn">Volver a crear bot</Link>}>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Playbooks" value={formatNumber(playbooks.length)} hint="Guías de respuesta" icon="flow" tone="green" />
        <StatCard label="Flows de WhatsApp" value={formatNumber(whatsappFlows.length)} hint="Formularios o pasos guiados" icon="channel" tone="blue" />
        <StatCard label="Idiomas" value={formatNumber(Object.keys(i18nConfig || {}).length)} hint="Cobertura configurada" icon="channel" tone="gold" />
        <StatCard label="Cobertura i18n" value={safeText(coverageValue, "-")} hint="Traducción o variantes listas" icon="stats" tone="slate" />
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
