import Link from "next/link";
import BotScopeSwitcher from "../components/BotScopeSwitcher";
import { Badge, ContextTip, DataTable, EmptyActionState, Section, Shell, SecondaryNav, StatCard, SuccessState } from "../components";
import { getCurrentBotId } from "../lib/session";
import { formatNumber, safeText } from "../lib/ui";
import { getBots } from "../lib/waos";

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }

export default async function BotsPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const filter = first(params.filter) || "todos";
  const bots = await getBots();
  const selectedBotId = await getCurrentBotId();
  const active = bots.filter((item) => String(item.status).toLowerCase() === "active").length;
  const paused = bots.filter((item) => String(item.status).toLowerCase() === "paused" || Number(item.ai_paused || 0) === 1).length;
  const withRisk = bots.filter((item) => Number(item.validation_score || 100) < 80 || String(item.status || "").toLowerCase() !== "active").length;
  const filtered = bots.filter((item) => {
    const status = String(item.status || "").toLowerCase();
    const aiPaused = Number(item.ai_paused || 0) === 1;
    if (filter === "activos") return status === "active" && !aiPaused;
    if (filter === "pausados") return status === "paused" || aiPaused;
    if (filter === "riesgo") return Number(item.validation_score || 100) < 80 || status !== "active";
    return true;
  });
  const selectedBot = bots.find((item) => String(item.id) === String(selectedBotId || ""));

  return (
    <Shell title="Bots" subtitle="Inventario real de bots: salud, riesgo y salida a detalle sin mezclar veinte acciones en la misma pantalla." action={<Link href="/bot-studio" className="primary-btn">Crear</Link>}>
      <SecondaryNav items={[
        { href: "/bots?filter=todos", label: `Todos (${formatNumber(bots.length)})`, active: filter === "todos" },
        { href: "/bots?filter=activos", label: `Activos (${formatNumber(active)})`, active: filter === "activos" },
        { href: "/bots?filter=pausados", label: `Pausados (${formatNumber(paused)})`, active: filter === "pausados" },
        { href: "/bots?filter=riesgo", label: `Riesgo (${formatNumber(withRisk)})`, active: filter === "riesgo" },
      ]} />
      <ContextTip>Usa esta pantalla para elegir el bot de trabajo y luego baja al detalle solo cuando de verdad necesites intervenir.</ContextTip>
      <Section title="Bot de trabajo" subtitle="Selecciona un bot explícito para que releases y otras vistas no adivinen contexto." icon="target" aside={<BotScopeSwitcher bots={bots} selectedBotId={selectedBotId} redirectTo={`/bots?filter=${encodeURIComponent(filter)}`} />}>
        {selectedBot ? <SuccessState title={`Bot seleccionado: ${safeText(selectedBot.name)}`} description="Las pantallas que dependen de un bot ya pueden usar este contexto explícito sin asumir el primer bot disponible." actions={<Link href={`/bots/${selectedBot.id}`} className="primary-btn">Ver detalle</Link>} /> : <EmptyActionState title="Todavía no seleccionas un bot" description="Elige uno para trabajar con contexto claro en releases y otras pantallas relacionadas." primaryAction={<Link href="/bot-studio" className="primary-btn">Crear</Link>} />}
      </Section>
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Bots totales" value={formatNumber(bots.length)} hint="Inventario visible" icon="bot" tone="blue" />
        <StatCard label="Activos" value={formatNumber(active)} hint="Listos para operar" icon="check" tone="green" />
        <StatCard label="Pausados" value={formatNumber(paused)} hint="Requieren revisión" icon="clock" tone={paused ? "gold" : "green"} />
        <StatCard label="Con riesgo" value={formatNumber(withRisk)} hint="Score bajo o estado no activo" icon="alert" tone={withRisk ? "red" : "green"} />
      </div>
      <Section title="Inventario de bots" subtitle="Una sola tabla para encontrar bot, ver salud y entrar directo al flujo correcto." icon="bot">
        {filtered.length ? <DataTable columns={["Bot", "Estado", "Salud", "Último cambio", "Abrir"]} rows={filtered.map((item) => {
          const risk = Number(item.validation_score || 100) < 80 || String(item.status || "").toLowerCase() !== "active" || Number(item.ai_paused || 0) === 1;
          return [
            <div key={item.id}><div className="font-medium text-white">{safeText(item.name)}</div><div className="text-xs text-slate-400">{safeText(item.goal || item.objective || item.vertical)}</div></div>,
            <Badge key={`${item.id}-status`} tone={risk ? "amber" : "green"}>{safeText(item.status || (Number(item.ai_paused || 0) === 1 ? "paused" : "active"))}</Badge>,
            <div key={`${item.id}-health`} className="flex flex-wrap gap-2"><span className="mono-pill">Score {formatNumber(item.validation_score || 0)}</span>{Number(item.ai_paused || 0) === 1 ? <span className="mono-pill">IA pausada</span> : null}</div>,
            safeText(item.updated_at || item.last_release_at || item.created_at),
            <Link key={`${item.id}-go`} href={`/bots/${item.id}`} className="font-medium text-emerald-300 hover:text-emerald-200">Ver detalle</Link>,
          ];
        })} /> : <EmptyActionState title="No hay bots para este filtro" description="La tabla queda limpia y útil. Cambia el filtro o crea el primer bot antes de seguir con integraciones o releases." primaryAction={<Link href="/bot-studio" className="primary-btn">Crear</Link>} secondaryAction={<Link href="/bots?filter=todos" className="secondary-btn">Ver todos</Link>} />}
      </Section>
    </Shell>
  );
}
