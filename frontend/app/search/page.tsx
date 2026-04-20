import Link from "next/link";
import { ContextTip, DataTable, EmptyActionState, Section, Shell } from "../components";
import { safeText } from "../lib/ui";
import { getBots, getConversations, getIntegrations } from "../lib/waos";

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }
function includesQuery(values: Array<unknown>, query: string) { return !query || values.map((value) => String(value || "").toLowerCase()).join(" ").includes(query); }
export default async function SearchPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const rawQuery = (first(params.q) || "").trim();
  const q = rawQuery.toLowerCase();
  const [bots, conversations, integrations] = await Promise.all([getBots(), getConversations(), getIntegrations()]);
  const items = !q ? [] : [
    ...bots.filter((item) => includesQuery([item.name, item.goal, item.objective, item.vertical, item.primary_channel, item.status], q)).slice(0, 10).map((item) => ["Bot", safeText(item.name), <Link key={item.id} href={`/bots/${item.id}`} className="font-medium text-emerald-300 hover:text-emerald-200">Abrir</Link>]),
    ...conversations.filter((item) => includesQuery([item.contact_name, item.contact_phone, item.bot_name, item.summary, item.latest_message_preview, item.relationship_label, item.relationship_key, item.recommended_mode, item.status], q)).slice(0, 10).map((item) => ["Conversación", safeText(item.contact_name || item.contact_phone || item.bot_name), <Link key={item.id} href={`/inbox/${item.id}`} className="font-medium text-emerald-300 hover:text-emerald-200">Abrir</Link>]),
    ...integrations.filter((item) => includesQuery([item.name, item.provider, item.integration_type, item.status, item.health_status, item.credential_status], q)).slice(0, 10).map((item) => ["Integración", safeText(item.name || item.provider), safeText(item.status)]),
  ];
  return <Shell title="Búsqueda global" subtitle="Busca bots, conversaciones e integraciones desde una sola pantalla."><Section title="Buscar" subtitle="Usa una palabra simple: nombre del bot, contacto, canal o proveedor." icon="target"><form className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]"><input defaultValue={rawQuery} name="q" className="field-input" placeholder="Ej. ventas, whatsapp, maría" /><button className="primary-btn" type="submit">Buscar</button></form></Section>{!q ? <EmptyActionState title="Todavía no has buscado nada" description="Empieza por el nombre de un bot, un contacto o un canal." primaryAction={<Link href="/bots" className="primary-btn">Ver bots</Link>} secondaryAction={<Link href="/inbox" className="secondary-btn">Abrir inbox</Link>} /> : <><ContextTip>Si salen demasiados resultados, cambia la búsqueda por un nombre más específico.</ContextTip><Section title="Resultados" subtitle="Vista rápida para llegar a la pantalla correcta." icon="target"><DataTable columns={["Tipo", "Elemento", "Acción"]} rows={items} /></Section></>}</Shell>;
}
