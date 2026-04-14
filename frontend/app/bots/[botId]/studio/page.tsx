import Link from "next/link";
import { KeyValueList, SecondaryNav, Section, Shell } from "../../../components";
import { safeText, yesNo } from "../../../lib/ui";
import { getBot } from "../../../lib/waos";

export default async function BotStudioPage({ params }: { params: Promise<{ botId: string }> }) {
  const { botId } = await params;
  const bot = await getBot(botId);
  return (
    <Shell title={`Edicion · ${safeText(bot.name, 'Bot')}`} subtitle="Una vista de edicion mas tranquila: que esta definido, que falta y hacia donde ir para ajustar contenido o comportamiento." action={<Link href={`/bots/${botId}`} className="secondary-btn">Volver al resumen</Link>}>
      <SecondaryNav items={[
        { href: `/bots/${botId}`, label: "Resumen" },
        { href: `/bots/${botId}/studio`, label: "Studio", active: true },
        { href: `/bots/${botId}/versions`, label: "Versiones" },
        { href: `/releases?bot_id=${encodeURIComponent(botId)}`, label: "Releases" },
      ]} />
      <Section title="Configuracion base" subtitle="Lo que conviene revisar primero al editar este bot." icon="wand">
        <div className="grid gap-4 xl:grid-cols-2">
          <KeyValueList items={[
            { label: 'Nombre', value: safeText(bot.name) },
            { label: 'Objetivo', value: safeText(bot.goal || bot.objective) },
            { label: 'Tono', value: safeText(bot.tone) },
            { label: 'Modo', value: safeText(bot.bot_mode) },
          ]} />
          <KeyValueList items={[
            { label: 'Auto imagenes', value: yesNo(bot.auto_send_images) },
            { label: 'Menciona stock', value: yesNo(bot.can_mention_stock) },
            { label: 'Canal principal', value: safeText(bot.primary_channel) },
            { label: 'Ultima actualizacion', value: safeText(bot.updated_at) },
          ]} />
        </div>
      </Section>
    </Shell>
  );
}
