import { Shell } from "@/app/components/layout/shell";
import { Section, StatCard } from "@/app/components/primitives/cards";
import { DataTable } from "@/app/components/primitives/data-display";
import { formatNumber, safeText } from "../lib/ui";
import { getOmnichannelOverview } from "@/app/lib/data/analytics";
import { getFeedback, getPortalRequests, getVoiceNotes } from "@/app/lib/data/inbox";

export default async function OmnichannelPage() {
  const [overview, feedback, voiceNotes, portalRequests] = await Promise.all([getOmnichannelOverview(), getFeedback(), getVoiceNotes(), getPortalRequests()]);
  const summary = overview.summary || {};
  return (
    <Shell title="Canales y experiencia" subtitle="Una vista transversal para entender qué pasa entre canales, portal, notas de voz y retroalimentación del cliente.">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Hilos" value={formatNumber((overview.threads || []).length)} hint="Conversaciones entre canales" icon="channel" tone="blue" />
        <StatCard label="Feedback" value={formatNumber(feedback.length)} hint="Opinión del cliente" icon="check" tone="green" />
        <StatCard label="Notas de voz" value={formatNumber(voiceNotes.length)} hint="Audio pendiente" icon="play" tone="gold" />
        <StatCard label="Solicitudes" value={formatNumber(portalRequests.length)} hint="Entradas del portal" icon="folder" tone="slate" />
      </div>
      <Section title="Hilos omnicanal" subtitle="Cómo se está moviendo la conversación entre canales." icon="channel">
        <DataTable columns={["Canal", "Cliente", "Estado", "Resumen"]} rows={(overview.threads || []).map((item) => [safeText(item.channel), safeText(item.contact_name), safeText(item.status), safeText(item.summary)])} />
      </Section>
    </Shell>
  );
}
