import Link from "next/link";
import { reactivateConversationAction, takeoverConversationAction } from "../actions";
import InboxKeyboardShortcuts from "../components/InboxKeyboardShortcuts";
import { ContextTip, EmptyActionState, Section, Shell, StatCard, StatusPill } from "../components";
import { formatNumber, safeText } from "../lib/ui";
import { getConversations } from "../lib/waos";
import type { ConversationItem } from "../lib/contracts";

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }

function urgencyLabel(level?: string) {
  const normalized = String(level || "normal").toLowerCase();
  if (normalized === "critical") return "Crítica";
  if (normalized === "high") return "Alta";
  if (normalized === "medium") return "Media";
  return "Normal";
}

function byFilter(item: ConversationItem, filter: string) {
  const status = String(item.status || "").toLowerCase();
  const leadStage = String(item.lead_stage || "").toLowerCase();
  const leadScore = Number(item.lead_score || 0);
  if (filter === "human") return status === "human_takeover";
  if (filter === "pending") return !item.last_outbound_at;
  if (filter === "hot") return leadStage.includes("hot") || leadScore >= 70;
  if (filter === "owner") return String(item.attention_tier || "").toLowerCase() === "owner_now";
  return true;
}

function searchMatches(item: ConversationItem, query: string) {
  if (!query) return true;
  const haystack = [
    item.contact_name,
    item.contact_phone,
    item.bot_name,
    item.summary,
    item.latest_message_preview,
    item.relationship_label,
    item.recommended_mode,
    item.attention_tier,
  ].join(" ").toLowerCase();
  return haystack.includes(query.toLowerCase());
}

function sortConversations(items: ConversationItem[], sort: string) {
  const cloned = [...items];
  if (sort === "urgency") return cloned.sort((a, b) => Number(b.urgency_score || 0) - Number(a.urgency_score || 0));
  if (sort === "lead") return cloned.sort((a, b) => Number(b.lead_score || 0) - Number(a.lead_score || 0));
  if (sort === "owner") return cloned.sort((a, b) => String(a.owner_name || "").localeCompare(String(b.owner_name || "")));
  if (sort === "name") return cloned.sort((a, b) => String(a.contact_name || "").localeCompare(String(b.contact_name || "")));
  return cloned.sort((a, b) => String(b.updated_at || b.last_inbound_at || "").localeCompare(String(a.updated_at || a.last_inbound_at || "")));
}

function priorityLabel(item: ConversationItem) {
  if (String(item.status || "").toLowerCase() === "human_takeover") return "Humano";
  if (String(item.attention_tier || "").toLowerCase() === "owner_now") return "Dueño";
  if (String(item.urgency_level || "").toLowerCase() === "critical") return "Urgente";
  if (!item.last_outbound_at) return "Pendiente";
  if (Number(item.lead_score || 0) >= 70) return "Caliente";
  return "Normal";
}

function buildQuery(params: Record<string, string | undefined>) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) query.set(key, value);
  });
  const rendered = query.toString();
  return rendered ? `?${rendered}` : "";
}

export default async function InboxPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const filter = first(params.filter) || "all";
  const sort = first(params.sort) || "recent";
  const q = first(params.q) || "";
  const relation = first(params.relation) || "all";
  const mode = first(params.mode) || "all";
  const urgency = first(params.urgency) || "all";
  const selectedId = first(params.selected) || "";
  const conversations = await getConversations();

  const filtered = sortConversations(
    conversations
      .filter((item) => byFilter(item, filter))
      .filter((item) => searchMatches(item, q))
      .filter((item) => relation === "all" ? true : String(item.relationship_key || item.relationship_label || "").toLowerCase().includes(relation.toLowerCase()))
      .filter((item) => mode === "all" ? true : String(item.recommended_mode || "").toLowerCase() === mode.toLowerCase())
      .filter((item) => urgency === "all" ? true : String(item.urgency_level || "normal").toLowerCase() === urgency.toLowerCase()),
    sort,
  );

  const selected = filtered.find((item) => item.id === selectedId) || filtered[0] || null;
  const selectedIndex = Math.max(filtered.findIndex((item) => item.id === selected?.id), 0);
  const listUrls = filtered.map((item) => `/inbox${buildQuery({ filter, sort, q, relation, mode, urgency, selected: item.id })}`);

  const human = conversations.filter((item) => String(item.status).toLowerCase() === "human_takeover").length;
  const pending = conversations.filter((item) => !item.last_outbound_at).length;
  const hot = conversations.filter((item) => String(item.lead_stage || "").toLowerCase().includes("hot") || Number(item.lead_score || 0) >= 70).length;
  const ownerNow = conversations.filter((item) => String(item.attention_tier || "").toLowerCase() === "owner_now").length;

  return (
    <Shell
      title="Inbox operativo"
      subtitle="La bandeja se trabaja como lista + preview. Primero filtras por intención, urgencia, relación y modo recomendado; después decides si hace falta entrar al hilo completo."
      action={<Link href={selected ? `/inbox/${selected.id}` : "/inbox"} className="primary-btn">{selected ? "Abrir detalle completo" : "Ver detalle"}</Link>}
    >
      <ContextTip title="Cómo leer la bandeja">Aquí ya se separan tres cosas que antes se mezclaban: urgencia real, calor comercial y necesidad de intervención humana.</ContextTip>

      {!conversations.length ? (
        <EmptyActionState title="Todavía no hay conversaciones" description="Cuando llegue actividad real, aquí verás prioridad, relación y modo recomendado antes de abrir el detalle." primaryAction={<Link href="/onboarding?step=probar" className="primary-btn">Probar flujo</Link>} secondaryAction={<Link href="/integrations" className="secondary-btn">Conectar canal</Link>} />
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Conversaciones" value={formatNumber(conversations.length)} hint="Total visible" icon="chat" tone="blue" />
        <StatCard label="Takeover humano" value={formatNumber(human)} hint="Casos ya tomados manualmente" icon="support" tone="gold" />
        <StatCard label="Pendientes" value={formatNumber(pending)} hint="Sin salida reciente" icon="alert" tone="green" />
        <StatCard label="Dueño ahora" value={formatNumber(ownerNow)} hint="Relación o urgencia que escalan" icon="target" tone={ownerNow ? "red" : "slate"} />
      </div>

      <Section title="Leyenda operativa" subtitle="Así se interpreta la capa relacional y la prioridad." icon="stack">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="surface-row text-sm text-slate-300"><span className="mono-pill">Urgencia</span><div className="mt-2">Qué tan rápido hay que responder.</div></div>
          <div className="surface-row text-sm text-slate-300"><span className="mono-pill">Lead</span><div className="mt-2">Qué tan cerca está de comprar o cerrar.</div></div>
          <div className="surface-row text-sm text-slate-300"><span className="mono-pill">Relación</span><div className="mt-2">Si es cliente, conocido, proveedor, familia o mixto.</div></div>
          <div className="surface-row text-sm text-slate-300"><span className="mono-pill">Modo</span><div className="mt-2">Si conviene tratarlo como ventas, soporte, operación o asistente.</div></div>
        </div>
      </Section>

      <Section title="Bandeja priorizada" subtitle="Toda la fila es clickeable y el panel derecho te deja decidir antes de entrar al hilo." icon="chat">
        <form className="mb-4 grid gap-3 rounded-3xl border border-white/[0.08] bg-white/[0.03] p-4 xl:sticky xl:top-4 xl:z-10 xl:grid-cols-[minmax(0,1.4fr)_repeat(4,180px)_auto]">
          <label className="field-label">
            Buscar
            <input className="field-input" type="search" name="q" defaultValue={q} placeholder="Nombre, teléfono, bot, resumen…" />
          </label>
          <label className="field-label">Foco
            <select className="field-input" name="filter" defaultValue={filter}>
              <option value="all">Todo</option>
              <option value="human">Humano</option>
              <option value="pending">Pendiente</option>
              <option value="hot">Caliente</option>
              <option value="owner">Dueño</option>
            </select>
          </label>
          <label className="field-label">Relación
            <select className="field-input" name="relation" defaultValue={relation}>
              <option value="all">Todas</option>
              <option value="client">Cliente</option>
              <option value="known">Conocido</option>
              <option value="family">Familia</option>
              <option value="provider">Proveedor</option>
            </select>
          </label>
          <label className="field-label">Modo
            <select className="field-input" name="mode" defaultValue={mode}>
              <option value="all">Todos</option>
              <option value="sales">Ventas</option>
              <option value="support">Soporte</option>
              <option value="operations">Operación</option>
              <option value="personal_assistant">Asistente</option>
              <option value="universal">Universal</option>
            </select>
          </label>
          <label className="field-label">Urgencia
            <select className="field-input" name="urgency" defaultValue={urgency}>
              <option value="all">Todas</option>
              <option value="critical">Crítica</option>
              <option value="high">Alta</option>
              <option value="medium">Media</option>
              <option value="normal">Normal</option>
            </select>
          </label>
          <label className="field-label">Orden
            <select className="field-input" name="sort" defaultValue={sort}>
              <option value="recent">Actividad reciente</option>
              <option value="urgency">Urgencia</option>
              <option value="lead">Lead score</option>
              <option value="owner">Owner</option>
              <option value="name">Nombre</option>
            </select>
          </label>
          <div className="flex items-end"><button className="primary-btn w-full" type="submit">Aplicar</button></div>
        </form>

        <div className="mb-4 flex flex-wrap gap-2 text-xs text-slate-300">
          <span className="mono-pill">Foco: {filter}</span>
          <span className="mono-pill">Relación: {relation}</span>
          <span className="mono-pill">Modo: {mode}</span>
          <span className="mono-pill">Urgencia: {urgency}</span>
          <span className="mono-pill">Orden: {sort}</span>
        </div>

        <InboxKeyboardShortcuts urls={listUrls} currentIndex={selectedIndex} openHref={selected ? `/inbox/${selected.id}` : null} />

        {filtered.length ? (
          <div className="mt-4 grid gap-4 xl:grid-cols-[0.96fr_1.04fr]">
            <div className="space-y-3 xl:max-h-[900px] xl:overflow-y-auto xl:pr-2">
              {filtered.map((item) => {
                const active = selected?.id === item.id;
                return (
                  <Link
                    key={item.id}
                    href={`/inbox${buildQuery({ filter, sort, q, relation, mode, urgency, selected: item.id })}`}
                    className={`block rounded-3xl border p-4 transition ${active ? "border-emerald-400/[0.24] bg-emerald-400/[0.10]" : "border-white/[0.08] bg-white/[0.03] hover:border-white/[0.16] hover:bg-white/[0.05]"}`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="truncate text-base font-semibold text-white">{safeText(item.contact_name, "Sin nombre")}</div>
                        <div className="mt-1 text-xs text-slate-400">{safeText(item.contact_phone)}</div>
                      </div>
                      <span className="mono-pill">{priorityLabel(item)}</span>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <StatusPill status={safeText(item.status)} />
                      <span className="mono-pill">{safeText(item.relationship_label || item.relationship_key || "nuevo")}</span>
                      <span className="mono-pill">{urgencyLabel(item.urgency_level)}</span>
                      <span className="mono-pill">Lead {formatNumber(item.lead_score || 0)}</span>
                    </div>
                    <p className="mt-3 line-clamp-2 text-sm leading-6 text-slate-300">{safeText(item.latest_message_preview || item.summary, "Sin resumen visible")}</p>
                    <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
                      <span>{safeText(item.bot_name, "Sin bot")}</span>
                      <span>{safeText(item.recommended_mode || item.relationship_status || "universal")}</span>
                    </div>
                  </Link>
                );
              })}
            </div>

            <div className="space-y-4 xl:sticky xl:top-28">
              {selected ? (
                <>
                  <div className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-5">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="text-xs uppercase tracking-[0.16em] text-slate-500">Preview</div>
                        <div className="mt-1 text-2xl font-semibold text-white">{safeText(selected.contact_name, "Sin nombre")}</div>
                        <div className="mt-2 text-sm text-slate-400">{safeText(selected.contact_phone)} · {safeText(selected.bot_name, "Sin bot")}</div>
                      </div>
                      <Link href={`/inbox/${selected.id}`} className="primary-btn">Abrir detalle</Link>
                    </div>
                    <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                      <div className="surface-row"><div className="text-xs uppercase tracking-[0.16em] text-slate-500">Relación</div><div className="mt-1 font-medium text-white">{safeText(selected.relationship_label || selected.relationship_key || "nuevo")}</div></div>
                      <div className="surface-row"><div className="text-xs uppercase tracking-[0.16em] text-slate-500">Urgencia</div><div className="mt-1 font-medium text-white">{urgencyLabel(selected.urgency_level)}</div></div>
                      <div className="surface-row"><div className="text-xs uppercase tracking-[0.16em] text-slate-500">Modo recomendado</div><div className="mt-1 font-medium text-white">{safeText(selected.recommended_mode || "universal")}</div></div>
                      <div className="surface-row"><div className="text-xs uppercase tracking-[0.16em] text-slate-500">Intervención</div><div className="mt-1 font-medium text-white">{safeText(selected.attention_tier || "normal")}</div></div>
                    </div>
                    <p className="mt-4 text-sm leading-7 text-slate-300">{safeText(selected.summary || selected.latest_message_preview, "Sin resumen visible")}</p>
                  </div>

                  <div className="grid gap-3 md:grid-cols-3">
                    <form action={takeoverConversationAction}>
                      <input type="hidden" name="conversation_id" value={selected.id} />
                      <input type="hidden" name="redirect_to" value={`/inbox${buildQuery({ filter, sort, q, relation, mode, urgency, selected: selected.id })}`} />
                      <button className="secondary-btn w-full" type="submit">Tomar caso</button>
                    </form>
                    <form action={reactivateConversationAction}>
                      <input type="hidden" name="conversation_id" value={selected.id} />
                      <input type="hidden" name="redirect_to" value={`/inbox${buildQuery({ filter, sort, q, relation, mode, urgency, selected: selected.id })}`} />
                      <button className="secondary-btn w-full" type="submit">Devolver a IA</button>
                    </form>
                    <Link href={`/inbox/${selected.id}`} className="secondary-btn w-full">Responder</Link>
                  </div>
                </>
              ) : null}
            </div>
          </div>
        ) : (
          <EmptyActionState title="No encontramos conversaciones con esos filtros" description="Prueba con menos filtros o cambia el foco principal para no vaciar la bandeja demasiado pronto." />
        )}
      </Section>
    </Shell>
  );
}
