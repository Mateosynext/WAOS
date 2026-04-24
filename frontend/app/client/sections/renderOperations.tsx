import Link from "next/link";

import { ClientEmptyBlock, ClientExecutiveSummary, ClientMetricCard } from "../../components/client/ClientPortalPrimitives";
import { getClientOperationsData } from "../../lib/data/client-operations";
import { formatNumber, safeText } from "../../lib/ui";
import type { ClientPortalData } from "@/app/lib/data/client-portal";
import { renderOperationalAlerts } from "./operations/renderOperationalAlerts";
import { renderOperationalAvailability } from "./operations/renderOperationalAvailability";
import { renderOperationalForms } from "./operations/renderOperationalForms";
import { renderOperationalRecentCommands } from "./operations/renderOperationalRecentCommands";

export async function renderOperations(data: ClientPortalData) {
  if (!data.context.organizationId || !data.context.botId) {
    return <ClientEmptyBlock title="No hay contexto operativo activo" description="Selecciona una organización y un bot para habilitar el control operativo por portal o WhatsApp." />;
  }

  const organizationId = data.context.organizationId;
  const botId = data.context.botId;
  const { summary, availability, metrics, alerts } = await getClientOperationsData(organizationId, botId);
  const recentCommands = summary.recent_commands;
  const authorizedNumbers = summary.authorized_numbers;
  const bot = summary.bot;
  const counts = summary.counts;

  return (
    <div className="space-y-6">
      <ClientExecutiveSummary
        title="Opera la agenda y el estado del bot sin salir del portal"
        description="Esta vista unifica control operativo, números autorizados y comandos en lenguaje natural. Los cambios masivos exigen confirmación y quedan auditados."
        insights={[
          `Estado actual: ${safeText(String(bot.operational_state || bot.current_state || bot.status || "sin estado"), "sin estado")}.`,
          `Números autorizados: ${formatNumber(Number(counts.authorized_numbers || 0))}.`,
          `Comandos recientes: ${formatNumber(Number(counts.recent_commands || 0))}.`,
        ]}
        cta={<Link href="/client/agenda" className="primary-btn">Revisar citas afectadas</Link>}
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <ClientMetricCard label="Estado bot" value={safeText(bot.operational_state || bot.current_state || "active", "active")} description={safeText(bot.temp_unavailability_message || "Sin mensaje temporal", "Sin mensaje temporal")} icon="bot" tone="blue" />
        <ClientMetricCard label="Comandos 7d" value={formatNumber(metrics.summary.total || counts.recent_commands || 0)} description="Actividad operativa reciente registrada para este bot." icon="tool" tone="gold" />
        <ClientMetricCard label="Autorizados" value={formatNumber(Number(counts.authorized_numbers || 0))} description="Números que sí pueden operar por WhatsApp." icon="shield" tone="green" />
        <ClientMetricCard label="Alto impacto" value={formatNumber(metrics.summary.high_risk || 0)} description="Comandos de alto impacto creados en la última semana." icon="alert" tone="slate" />
        <ClientMetricCard label="Alertas abiertas" value={formatNumber(metrics.summary.alerts_open || counts.alerts_open || 0)} description="Eventos operativos que requieren seguimiento." icon="alert" tone="gold" />
      </div>

      {renderOperationalForms({ organizationId, botId, authorizedNumbers })}

      <div className="grid gap-6 xl:grid-cols-2">
        {renderOperationalAlerts({ alerts })}
        {renderOperationalRecentCommands({ recentCommands })}
        {renderOperationalAvailability({ availability })}
      </div>
    </div>
  );
}
