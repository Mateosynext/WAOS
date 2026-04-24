import Link from "next/link";
import InboxKeyboardShortcuts from "@/app/components/InboxKeyboardShortcuts";
import { ContextTip, EmptyActionState } from "@/app/components/feedback";
import { Shell } from "@/app/components/layout/shell";
import { Section } from "@/app/components/primitives/cards";
import type { InboxPageModel } from "@/features/inbox/server/getInboxPageModel";
import { InboxMetrics } from "./InboxMetrics";
import { InboxFilters } from "./InboxFilters";
import { ConversationList } from "./ConversationList";
import { ConversationDetail } from "./ConversationDetail";

export function InboxShell({ model }: { model: InboxPageModel }) {
  const { conversations, filtered, selected, listUrls, selectedIndex } = model;
  return (
    <Shell
      title="Inbox"
      subtitle="Inbox ya no compite con setup ni con publish: aquí operas conversaciones reales con lista, preview y prioridad antes de entrar al hilo completo."
      action={<Link href={selected ? `/inbox/${selected.id}` : "/inbox"} className="primary-btn">{selected ? "Abrir detalle completo" : "Ver detalle"}</Link>}
    >
      <ContextTip title="Qué hace Inbox y qué no">Inbox opera. Si falta conectar o probar, vuelve a Integraciones. Si falta crear o reconfigurar, vuelve a Bot Studio. Aquí solo decides, respondes y escalas conversaciones reales.</ContextTip>

      {!conversations.length ? (
        <EmptyActionState title="Todavía no hay conversaciones" description="Antes de operar aquí, conecta o prueba los canales desde Integraciones o valida el asistente operativo desde Bot Studio." primaryAction={<Link href="/integrations?section=configuracion" className="primary-btn">Conectar canal</Link>} secondaryAction={<Link href="/bot-studio" className="secondary-btn">Abrir Bot Studio</Link>} />
      ) : null}

      <InboxMetrics model={model} />

      <Section title="Bandeja priorizada" subtitle="Toda la fila es clickeable y el panel derecho te deja decidir antes de entrar al hilo." icon="chat">
        <InboxFilters model={model} />
        <InboxKeyboardShortcuts urls={listUrls} currentIndex={selectedIndex} openHref={selected ? `/inbox/${selected.id}` : null} />
        {filtered.length ? (
          <div className="mt-4 grid gap-4 xl:grid-cols-[0.96fr_1.04fr]">
            <ConversationList model={model} />
            <ConversationDetail model={model} />
          </div>
        ) : (
          <EmptyActionState title="No encontramos conversaciones con esos filtros" description="Prueba con menos filtros o cambia el foco principal para no vaciar la bandeja demasiado pronto." />
        )}
      </Section>
    </Shell>
  );
}
