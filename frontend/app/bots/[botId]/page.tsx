import Link from "next/link";
import { pauseBotAction, resumeBotAction } from "@/app/actions/bots";
import { switchBotAction } from "@/app/actions/selection";
import { ContextTip, PermissionGate, SuccessState } from "@/app/components/feedback";
import { Shell } from "@/app/components/layout/shell";
import { SecondaryNav } from "@/app/components/navigation";
import { Section, StatCard } from "@/app/components/primitives/cards";
import { DataTable, KeyValueList, TimelineList } from "@/app/components/primitives/data-display";
import { Badge } from "@/app/components/primitives/shared";
import ConfirmSubmitButton from "../../components/ConfirmSubmitButton";
import { canManageBots, roleLabel } from "../../lib/permissions";
import { getSession } from "../../lib/session";
import { formatNumber, safeText, yesNo } from "../../lib/ui";
import { getBot, getBotValidation } from "@/app/lib/data/bots";
import { getIntegrations } from "@/app/lib/data/integrations";

export default async function BotPage({ params }: { params: Promise<{ botId: string }> }) {
  const { botId } = await params;
  const session = await getSession();
  const role = session?.user.global_role;
  const [bot, validation, integrations] = await Promise.all([getBot(botId), getBotValidation(botId), getIntegrations()]);
  const report = validation.validation || {};
  const connected = integrations.filter((item) => String(item.bot_id || item.related_bot_id || "") === String(botId));
  const nextSteps = [
    !report.ok ? { title: "Corrige validacion", detail: safeText((report.errors || []).join(" · "), "Revisa la configuracion base antes de publicar."), tone: "gold" as const } : { title: "Validacion base lista", detail: "El borrador ya tiene una base razonable para pasar a release.", tone: "green" as const },
    Number(bot.ai_paused) === 1 ? { title: "Bot pausado", detail: "Reactivalo cuando termines de revisar cambios y pruebas.", tone: "red" as const } : { title: "Bot operativo", detail: "No se ve una pausa manual activa en este momento.", tone: "green" as const },
    connected.length ? { title: "Integraciones relacionadas", detail: `${formatNumber(connected.length)} conexiones aparecen asociadas a este bot o a su organizacion inmediata.`, tone: "blue" as const } : { title: "Sin integraciones visibles", detail: "Antes de publicar, conecta al menos un canal o proveedor necesario.", tone: "gold" as const },
  ].filter(Boolean) as Array<{ title: string; detail: string; tone?: "slate" | "green" | "gold" | "red" | "blue" }>;

  return <Shell title={safeText(bot.name, "Bot")} subtitle="Resumen unico del bot: salud, integraciones, validacion y acciones delicadas protegidas por rol visible." action={<Link href={`/bots/${botId}/studio`} className="primary-btn">Editar</Link>}>
    <SecondaryNav items={[
      { href: `/bots/${botId}`, label: "Resumen", active: true },
      { href: `/bots/${botId}/studio`, label: "Studio" },
      { href: `/bots/${botId}/versions`, label: "Versiones" },
      { href: `/vacantes`, label: "Vacantes" },
      { href: `/releases?bot_id=${encodeURIComponent(botId)}`, label: "Releases" },
    ]} />
    <ContextTip>Tu rol visible ahora es {roleLabel(role)}. Este bot ya puede fijarse como contexto para releases y otras pantallas que antes adivinaban el primer bot disponible.</ContextTip>
    <SuccessState title="Bot listo para trabajar con contexto claro" description="Si este es el bot principal del momento, puedes fijarlo una sola vez y seguir a releases, pruebas o publicación sin ambigüedad." actions={<form action={switchBotAction}><input type="hidden" name="bot_id" value={botId} /><input type="hidden" name="redirect_to" value={`/bots/${botId}`} /><button className="primary-btn" type="submit">Usar como contexto</button></form>} />
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <StatCard label="Estado" value={safeText(bot.status, "sin estado")} hint="Estado operativo" icon="bot" tone="green" />
      <StatCard label="Validacion" value={report.ok ? "Lista" : "Revisar"} hint="Lectura rapida antes de publicar" icon="check" tone={report.ok ? "green" : "gold"} />
      <StatCard label="Score" value={formatNumber(report.score)} hint="Senal de preparacion" icon="stats" tone="blue" />
      <StatCard label="IA pausada" value={yesNo(bot.ai_paused)} hint="Si la IA esta detenida" icon="clock" tone={Number(bot.ai_paused) === 1 ? "red" : "slate"} />
    </div>
    <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
      <Section title="Resumen del bot" subtitle="Lo mas importante del bot en una sola lectura." icon="bot" aside={<Badge tone={String(bot.status).toLowerCase() === "active" ? "green" : "amber"}>{safeText(bot.status)}</Badge>}>
        <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
          <KeyValueList items={[{ label: "Nombre", value: safeText(bot.name) }, { label: "Objetivo", value: safeText(bot.goal || bot.objective) }, { label: "Tono", value: safeText(bot.tone) }, { label: "Canal principal", value: safeText(bot.primary_channel) }, { label: "Vertical", value: safeText(bot.vertical) }]} />
          <KeyValueList items={[{ label: "IA pausada", value: yesNo(bot.ai_paused) }, { label: "Respuestas con imagen", value: yesNo(bot.auto_send_images) }, { label: "Puede mencionar stock", value: yesNo(bot.can_mention_stock) }, { label: "Ultima actualizacion", value: safeText(bot.updated_at) }, { label: "ID", value: safeText(bot.id) }]} />
        </div>
      </Section>
      <Section title="Que sigue" subtitle="Una ruta corta para dejar el bot listo sin perderte entre pantallas." icon="route">
        <TimelineList items={nextSteps} />
      </Section>
    </div>
    <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
      <Section title="Resultado de validacion" subtitle="Usalo antes de publicar para detectar riesgos o tareas pendientes." icon="alert">
        <DataTable columns={["Tipo", "Detalle"]} rows={[["Errores", safeText((report.errors || []).join(" · "), "Sin errores")], ["Advertencias", safeText((report.warnings || []).join(" · "), "Sin advertencias")]]} />
      </Section>
      <Section title="Integraciones y referencias" subtitle="Una tabla corta para entender con que sistemas convive este bot." icon="plug">
        {connected.length ? <DataTable columns={["Integracion", "Proveedor", "Estado"]} rows={connected.map((item) => [safeText(item.name), safeText(item.provider || item.integration_type), safeText(item.status || item.health_status)])} /> : <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] px-4 py-4 text-sm text-slate-300">No se ven integraciones asociadas directamente a este bot.</div>}
      </Section>
    </div>
    <Section title="Acciones delicadas" subtitle="Pausar, reactivar o publicar quedan visibles solo cuando el rol deberia poder tocarlas." icon="shield">
      <div className="flex flex-wrap gap-2">
        <PermissionGate allowed={canManageBots(role)} fallback={<div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] px-4 py-4 text-sm text-slate-300">Tu rol puede revisar este bot pero no pausar, reactivar o publicar desde aqui.</div>}>
          <form action={pauseBotAction}><input type="hidden" name="bot_id" value={botId} /><input type="hidden" name="redirect_to" value={`/bots/${botId}`} /><ConfirmSubmitButton message="Seguro que quieres pausar este bot?">Pausar</ConfirmSubmitButton></form>
          <form action={resumeBotAction}><input type="hidden" name="bot_id" value={botId} /><input type="hidden" name="redirect_to" value={`/bots/${botId}`} /><ConfirmSubmitButton message="Seguro que quieres reactivar este bot?">Reactivar</ConfirmSubmitButton></form>
          <Link href={`/releases?stage=draft&bot_id=${encodeURIComponent(botId)}`} className="primary-btn">Ir al release flow</Link>
        </PermissionGate>
      </div>
    </Section>
  </Shell>;
}
