import Link from "next/link";
import { ContextTip, DataTable, EmptyActionState, Section, Shell } from "../components";
import { safeText } from "../lib/ui";
import { getBots, getConversations, getIntegrations } from "../lib/waos";

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }
export default async function SearchPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {}; const q = (first(params.q) || "").toLowerCase().trim(); const [bots, conversations, integrations] = await Promise.all([getBots(), getConversations(), getIntegrations()]);
  const items = !q ? [] : [
    ...bots.filter((x)=>JSON.stringify(x).toLowerCase().includes(q)).slice(0,10).map((x)=>["Bot", safeText(x.name), <Link key={x.id} href={`/bots/${x.id}`} className="font-medium text-emerald-300 hover:text-emerald-200">Abrir</Link>]),
    ...conversations.filter((x)=>JSON.stringify(x).toLowerCase().includes(q)).slice(0,10).map((x)=>["Conversación", safeText(x.contact_name), <Link key={x.id} href={`/inbox/${x.id}`} className="font-medium text-emerald-300 hover:text-emerald-200">Abrir</Link>]),
    ...integrations.filter((x)=>JSON.stringify(x).toLowerCase().includes(q)).slice(0,10).map((x)=>["Integración", safeText(x.name), safeText(x.status)]),
  ];
  return <Shell title="Búsqueda global" subtitle="Busca bots, conversaciones e integraciones desde una sola pantalla."><Section title="Buscar" subtitle="Usa una palabra simple: nombre del bot, contacto, canal o proveedor." icon="target"><form className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]"><input defaultValue={q} name="q" className="field-input" placeholder="Ej. ventas, whatsapp, maría" /><button className="primary-btn" type="submit">Buscar</button></form></Section>{!q ? <EmptyActionState title="Todavía no has buscado nada" description="Empieza por el nombre de un bot, un contacto o un canal." primaryAction={<Link href="/bots" className="primary-btn">Ver bots</Link>} secondaryAction={<Link href="/inbox" className="secondary-btn">Abrir inbox</Link>} /> : <><ContextTip>Si salen demasiados resultados, cambia la búsqueda por un nombre más específico.</ContextTip><Section title="Resultados" subtitle="Vista rápida para llegar a la pantalla correcta." icon="target"><DataTable columns={["Tipo", "Elemento", "Acción"]} rows={items} /></Section></>}</Shell>;
}
