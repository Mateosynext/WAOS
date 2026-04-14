import Link from "next/link";
import { ContextTip, DataTable, PermissionGate, Section, Shell, StatCard } from "../components";
import { canUseSupportMode, roleLabel } from "../lib/permissions";
import { getSession } from "../lib/session";
import { formatNumber, safeText } from "../lib/ui";
import { getBots, getConversations, getIntegrations } from "../lib/waos";

export default async function SupportPage() {
  const session = await getSession();
  const role = session?.user.global_role;
  const [bots, conversations, integrations] = await Promise.all([getBots(), getConversations(), getIntegrations()]);
  const pausedBots = bots.filter((item) => String(item.status || "").toLowerCase() === "paused" || Number(item.ai_paused || 0) === 1);
  const humanCases = conversations.filter((item) => String(item.status || "").toLowerCase() === "human_takeover");
  const degradedIntegrations = integrations.filter((item) => String(item.health_status || item.status || "").toLowerCase() === "degraded");
  return (
    <Shell title="Modo soporte" subtitle="Una vista segura para inspeccionar la operacion sin abrir todo el panel administrativo." action={<><Link href="/status" className="secondary-btn">Estado</Link><Link href="/inbox?filter=human" className="primary-btn">Inbox humano</Link></>}>
      <ContextTip>Tu rol visible ahora es {roleLabel(role)}. Soporte existe para inspeccion segura: menos acciones, mas claridad y menos riesgo de tocar configuracion estructural.</ContextTip>
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Bots pausados" value={formatNumber(pausedBots.length)} hint="Bots detenidos" icon="bot" tone="gold" />
        <StatCard label="Casos humanos" value={formatNumber(humanCases.length)} hint="Conversaciones con intervencion" icon="support" tone="gold" />
        <StatCard label="Integraciones degradadas" value={formatNumber(degradedIntegrations.length)} hint="Conexiones a revisar" icon="plug" tone="red" />
      </div>
      <PermissionGate allowed={canUseSupportMode(role)} fallback={<Section title="Acceso restringido" subtitle="Tu rol no deberia usar el modo soporte. Pide apoyo a un perfil operativo si necesitas inspeccion." icon="support"><div className="text-sm text-slate-300">El modo soporte se mantiene reducido por seguridad operativa.</div></Section>}>
        <Section title="Casos visibles ahora" subtitle="Soporte trabaja sobre una lista corta y segura, no sobre todo el producto." icon="support"><DataTable columns={["Tipo", "Detalle"]} rows={[...pausedBots.slice(0, 5).map((item) => ["Bot pausado", `${safeText(item.name)} · ${safeText(item.status)}`]), ...humanCases.slice(0, 5).map((item) => ["Takeover humano", `${safeText(item.contact_name)} · ${safeText(item.summary)}`]), ...degradedIntegrations.slice(0, 5).map((item) => ["Integracion degradada", `${safeText(item.name)} · ${safeText(item.health_status || item.status)}`])]} /></Section>
      </PermissionGate>
    </Shell>
  );
}
