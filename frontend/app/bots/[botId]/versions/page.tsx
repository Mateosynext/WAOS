import Link from "next/link";
import { Shell } from "@/app/components/layout/shell";
import { SecondaryNav } from "@/app/components/navigation";
import { Section, StatCard } from "@/app/components/primitives/cards";
import { DataTable } from "@/app/components/primitives/data-display";
import { formatNumber, safeText } from "../../../lib/ui";
import { getBot, getBotValidation, getBuilds } from "@/app/lib/data/bots";

export default async function BotVersionsPage({ params }: { params: Promise<{ botId: string }> }) {
  const { botId } = await params;
  const [bot, validation, builds] = await Promise.all([getBot(botId), getBotValidation(botId), getBuilds(botId)]);
  const against = validation.against_published || {};
  return (
    <Shell title={`Versiones · ${safeText(bot.name, 'Bot')}`} subtitle="Aqui revisas cambios, builds y diferencia contra lo publicado para decidir con calma que sale a produccion." action={<Link href={`/releases?bot_id=${encodeURIComponent(botId)}`} className="primary-btn">Ir a releases</Link>}>
      <SecondaryNav items={[
        { href: `/bots/${botId}`, label: "Resumen" },
        { href: `/bots/${botId}/studio`, label: "Studio" },
        { href: `/bots/${botId}/versions`, label: "Versiones", active: true },
        { href: `/releases?bot_id=${encodeURIComponent(botId)}`, label: "Releases" },
      ]} />
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Builds" value={formatNumber(builds.length)} hint="Construcciones registradas" icon="layers" tone="blue" />
        <StatCard label="Cambios" value={formatNumber(against.total_changes)} hint="Diferencia contra publicado" icon="refresh" tone="gold" />
        <StatCard label="Score" value={formatNumber(validation.validation?.score)} hint="Senal de calidad" icon="stats" tone="green" />
      </div>
      <Section title="Historial de builds" subtitle="Que se construyo y como termino." icon="layers">
        <DataTable columns={["Build", "Estado", "Fecha", "Detalle"]} rows={builds.map((item) => [safeText(item.id), safeText(item.status), safeText(item.created_at), safeText(item.summary || item.detail)])} />
      </Section>
      <Section title="Cambios detectados" subtitle="Util para entender que tan distinto quedo frente a lo que ya estaba publicado." icon="refresh">
        <DataTable columns={["Cambio", "Detalle"]} rows={(against.changes || []).map((item, index: number) => [safeText(item.kind || item.type, `Cambio ${index + 1}`), safeText(item.detail || JSON.stringify(item))])} />
      </Section>
    </Shell>
  );
}
