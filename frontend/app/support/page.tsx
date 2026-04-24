import Link from "next/link";
import { ContextTip, EmptyActionState } from "@/app/components/feedback";
import { Shell } from "@/app/components/layout/shell";
import { ModuleCard, Section, StatCard } from "@/app/components/primitives/cards";
import { DataTable } from "@/app/components/primitives/data-display";
import { Badge } from "@/app/components/primitives/shared";
import { formatDateTime, formatNumber, safeText } from "../lib/ui";
import { getBots } from "@/app/lib/data/bots";
import { getConversations, getFeedback } from "@/app/lib/data/inbox";
import { getIntegrations } from "@/app/lib/data/integrations";

export default async function SupportPage() {
  const [conversations, bots, integrations, feedback] = await Promise.all([
    getConversations(),
    getBots(),
    getIntegrations(),
    getFeedback(),
  ]);

  const humanTakeovers = conversations.filter((item) => String(item.status || "").toLowerCase() === "human_takeover");
  const urgent = conversations.filter((item) => ["urgent", "high"].includes(String(item.urgency_level || item.attention_tier || "").toLowerCase()));
  const hotCommercial = conversations.filter((item) => ["hot", "qualified", "sales"].includes(String(item.lead_stage || item.recommended_mode || "").toLowerCase()));
  const pausedBots = bots.filter((item) => String(item.status || "").toLowerCase() === "paused" || Number(item.ai_paused || 0) === 1);
  const degradedIntegrations = integrations.filter((item) => !["active", "configured", "connected", "healthy"].includes(String(item.health_status || item.status || "").toLowerCase()));
  const visibleFeedback = feedback.filter((item) => Boolean(item.detail || item.comment || item.message));

  return (
    <Shell
      title="Soporte operativo"
      subtitle="La vista de soporte ya no vive enterrada dentro de operaciones. Aquí se priorizan takeovers, urgencias, fricción real y señales que piden intervención humana."
      action={<Link href="/inbox?filter=human" className="primary-btn">Abrir inbox humano</Link>}
    >
      <ContextTip title="Cómo leer esta pantalla">
        Primero revisa takeovers humanos y urgencias. Después valida si el ruido viene de bots pausados o integraciones degradadas. Así soporte no persigue síntomas equivocados.
      </ContextTip>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Takeovers humanos" value={formatNumber(humanTakeovers.length)} hint="Conversaciones que ya salieron del flujo automático" icon="support" tone={humanTakeovers.length ? "gold" : "green"} />
        <StatCard label="Urgencias visibles" value={formatNumber(urgent.length)} hint="Casos que piden revisión prioritaria" icon="alert" tone={urgent.length ? "red" : "blue"} />
        <StatCard label="Señal comercial alta" value={formatNumber(hotCommercial.length)} hint="Conversaciones que no conviene dejar enfriar" icon="briefcase" tone="blue" />
        <StatCard label="Feedback visible" value={formatNumber(visibleFeedback.length)} hint="Reportes o fricción recibida por el sistema" icon="chat" tone={visibleFeedback.length ? "gold" : "slate"} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Section title="Atención inmediata" subtitle="Casos que conviene abrir ahora mismo porque ya requieren intervención humana o priorización explícita." icon="support">
          {humanTakeovers.length || urgent.length ? (
            <DataTable
              columns={["Conversación", "Motivo", "Señal", "Último movimiento"]}
              rows={[...humanTakeovers.slice(0, 8), ...urgent.slice(0, 8)].slice(0, 12).map((item) => [
                safeText(item.contact_name || item.contact_phone || item.id),
                safeText(item.summary || item.latest_message_preview || item.relationship_label, "Sin resumen"),
                <div key={`${item.id}-signals`} className="flex flex-wrap gap-2">
                  {String(item.status || "").toLowerCase() === "human_takeover" ? <Badge tone="gold">Takeover</Badge> : null}
                  {["urgent", "high"].includes(String(item.urgency_level || item.attention_tier || "").toLowerCase()) ? <Badge tone="red">Urgente</Badge> : null}
                  {["hot", "qualified", "sales"].includes(String(item.lead_stage || item.recommended_mode || "").toLowerCase()) ? <Badge tone="sky">Comercial</Badge> : null}
                </div>,
                formatDateTime(safeText(item.updated_at || item.last_inbound_at || item.created_at, "")),
              ])}
            />
          ) : (
            <EmptyActionState title="Sin takeovers ni urgencias visibles" description="El backend no devolvió conversaciones con takeover humano ni prioridad alta para este tenant." primaryAction={<Link href="/inbox" className="primary-btn">Abrir inbox</Link>} />
          )}
        </Section>

        <Section title="Estado del sistema alrededor de soporte" subtitle="Señales del entorno que suelen explicar casos abiertos o experiencia degradada." icon="gear">
          <div className="grid gap-4 sm:grid-cols-2">
            <ModuleCard title="Bots pausados" description={pausedBots.length ? `${formatNumber(pausedBots.length)} bot(s) aparecen pausados o con AI detenida.` : "No se ven bots pausados en esta organización."} icon="bot" tone={pausedBots.length ? "gold" : "green"} footer={<Link href="/bots" className="secondary-btn">Ver bots</Link>} />
            <ModuleCard title="Integraciones degradadas" description={degradedIntegrations.length ? `${formatNumber(degradedIntegrations.length)} integración(es) con estado degradado o sin conexión estable.` : "No se ven integraciones degradadas ahora mismo."} icon="plug" tone={degradedIntegrations.length ? "red" : "green"} footer={<Link href="/integrations" className="secondary-btn">Ver integraciones</Link>} />
            <ModuleCard title="Portal cliente" description="Si el caso requiere validar la experiencia externa, entra al portal sin perder el contexto interno." icon="client" tone="blue" footer={<Link href="/client/resumen" className="secondary-btn">Abrir portal</Link>} />
            <ModuleCard title="Auditoría" description="Si necesitas revisar quién hizo un cambio o desde qué módulo vino, abre audit." icon="logs" tone="slate" footer={<Link href="/audit" className="secondary-btn">Ver audit</Link>} />
          </div>
        </Section>
      </div>

      <Section title="Feedback y fricción visibles" subtitle="Soporte no solo responde conversaciones; también necesita ver reportes y señales repetidas de fricción." icon="chat">
        {visibleFeedback.length ? (
          <DataTable
            columns={["Tipo", "Detalle", "Fecha"]}
            rows={visibleFeedback.slice(0, 12).map((item) => [
              safeText(item.kind, "Feedback"),
              safeText(item.detail || item.comment || item.message, "Sin detalle"),
              formatDateTime(safeText(item.created_at, "")),
            ])}
          />
        ) : (
          <EmptyActionState title="No hay feedback visible" description="En esta respuesta no aparecieron reportes o feedback pendiente de atención." />
        )}
      </Section>
    </Shell>
  );
}
