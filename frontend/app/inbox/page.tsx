import Link from "next/link";
import { ContextTip, DataTable, EmptyActionState, SecondaryNav, Section, Shell, StatCard, StatusPill, SuccessState } from "../components";
import { formatNumber, safeText } from "../lib/ui";
import { getConversations } from "../lib/waos";

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }
function byFilter(item: import("../lib/contracts").ConversationItem, filter: string) {
  const status = String(item.status || "").toLowerCase();
  const leadStage = String(item.lead_stage || "").toLowerCase();
  const leadScore = Number(item.lead_score || 0);
  if (filter === "human") return status === "human_takeover";
  if (filter === "pending") return !item.last_outbound_at;
  if (filter === "hot") return leadStage.includes("hot") || leadScore >= 70;
  return true;
}

export default async function InboxPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const filter = first(params.filter) || "all";
  const conversations = await getConversations();
  const human = conversations.filter((item) => String(item.status).toLowerCase() === "human_takeover").length;
  const pending = conversations.filter((item) => !item.last_outbound_at).length;
  const hot = conversations.filter((item) => String(item.lead_stage || "").toLowerCase().includes("hot") || Number(item.lead_score || 0) >= 70).length;
  const filtered = conversations.filter((item) => byFilter(item, filter));
  const headlineHref = filter === "human" ? "/inbox?filter=pending" : "/inbox?filter=human";
  const headlineLabel = filter === "human" ? "Ver pendientes" : "Atender humanos";

  return (
    <Shell title="Inbox operativo" subtitle="La bandeja prioriza primero lo humano, luego lo pendiente y después el resto. Así la operación diaria se separa del mantenimiento." action={<Link href={headlineHref} className="primary-btn">{headlineLabel}</Link>}>
      <SecondaryNav items={[
        { href: "/inbox?filter=all", label: `Todo (${formatNumber(conversations.length)})`, active: filter === "all" },
        { href: "/inbox?filter=human", label: `Humano (${formatNumber(human)})`, active: filter === "human" },
        { href: "/inbox?filter=pending", label: `Pendiente (${formatNumber(pending)})`, active: filter === "pending" },
        { href: "/inbox?filter=hot", label: `Caliente (${formatNumber(hot)})`, active: filter === "hot" },
      ]} />
      <ContextTip>Trabaja siempre en este orden: humano, pendiente y caliente. Lo demás puede esperar.</ContextTip>

      {!conversations.length ? (
        <EmptyActionState title="Todavía no hay conversaciones" description="Cuando llegue actividad, esta pantalla te dirá qué hacer primero en lugar de mostrar una tabla vacía sin contexto." primaryAction={<Link href="/onboarding?step=probar" className="primary-btn">Probar</Link>} secondaryAction={<Link href="/integrations" className="secondary-btn">Conectar</Link>} />
      ) : (
        <SuccessState title="La bandeja ya está priorizada" description="El filtro queda persistente por URL para que no pierdas foco al navegar o compartir la vista." actions={<Link href={headlineHref} className="primary-btn">{headlineLabel}</Link>} />
      )}

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Conversaciones" value={formatNumber(conversations.length)} hint="Total visible" icon="chat" tone="blue" />
        <StatCard label="Con apoyo humano" value={formatNumber(human)} hint="Necesitan revisión manual" icon="support" tone="gold" />
        <StatCard label="Por responder" value={formatNumber(pending)} hint="Sin salida reciente" icon="alert" tone="green" />
        <StatCard label="Casos calientes" value={formatNumber(hot)} hint="Mayor intención o urgencia" icon="target" tone="red" />
      </div>

      <Section title="Bandeja priorizada" subtitle="Una sola tabla para decidir a quién atender y abrir el detalle cuando haga falta." icon="chat">
        {filtered.length ? (
          <DataTable columns={["Contacto", "Estado", "Prioridad", "Bot", "Resumen", "Abrir"]} rows={filtered.map((item) => {
            const leadScore = Number(item.lead_score || 0);
            const priority = String(item.status || "").toLowerCase() === "human_takeover" ? "Humano" : !item.last_outbound_at ? "Pendiente" : leadScore >= 70 ? "Caliente" : "Normal";
            return [
              <div key={item.id}><div className="font-medium text-white">{safeText(item.contact_name)}</div><div className="text-xs text-slate-400">{safeText(item.contact_phone)}</div></div>,
              <StatusPill key={`${item.id}-status`} status={safeText(item.status)} />,
              <span key={`${item.id}-priority`} className="mono-pill">{priority}</span>,
              <div key={`${item.id}-bot`}><div className="text-white">{safeText(item.bot_name)}</div><div className="text-xs text-slate-400">{safeText(item.lead_stage)} · {safeText(item.lead_score)}</div></div>,
              safeText(item.summary),
              <Link key={`${item.id}-go`} href={`/inbox/${item.id}`} className="font-medium text-emerald-300 hover:text-emerald-200">Ver hilo</Link>,
            ];
          })} />
        ) : (
          <EmptyActionState title="No hay conversaciones para este filtro" description="La vista queda vacía de forma útil: cambia el filtro o vuelve a la bandeja completa para revisar el resto." primaryAction={<Link href="/inbox?filter=all" className="primary-btn">Ver todo</Link>} secondaryAction={<Link href="/operations" className="secondary-btn">Volver a operación</Link>} />
        )}
      </Section>
    </Shell>
  );
}
