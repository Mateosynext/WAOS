import { Badge } from "../primitives/shared";
import { ModuleCard, Section } from "../primitives/cards";
import { TimelineList } from "../primitives/data-display";

export function WhatsAppPreview({ title, scenario, userPrompt, blocks, footer, themeTone = "green", stageLabel, objective, proofLabel, highlights = [], quickReplies = [] }: { title: string; scenario: string; userPrompt: string; blocks: Array<Record<string, unknown> & { type?: string; label?: string; text?: string }>; footer: string; themeTone?: "green" | "blue" | "gold" | "red" | "slate"; stageLabel?: string; objective?: string; proofLabel?: string; highlights?: string[]; quickReplies?: string[] }) {
  const bubbleTone = themeTone === "blue" ? "bg-sky-400/[0.16] border-sky-400/[0.25]" : themeTone === "gold" ? "bg-amber-400/[0.14] border-amber-400/[0.25]" : themeTone === "red" ? "bg-rose-400/[0.14] border-rose-400/[0.25]" : "bg-emerald-400/[0.14] border-emerald-400/[0.25]";
  return (
    <Section title={title} subtitle={scenario} icon="chat" aside={proofLabel ? <Badge tone={themeTone === "gold" ? "gold" : themeTone === "blue" ? "sky" : themeTone === "red" ? "red" : "green"}>{proofLabel}</Badge> : null}>
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-4">
          {objective ? <ModuleCard title="Objetivo de esta vista" description={objective} icon="target" tone="blue" /> : null}
          {highlights.length ? <TimelineList items={highlights.map((item, index) => ({ title: `Punto ${index + 1}`, detail: item, tone: index === 0 ? "green" : "slate" }))} /> : null}
          {quickReplies.length ? <ModuleCard title="Respuestas rápidas sugeridas" description="Botones claros para acelerar la conversación y ayudar a cerrar sin ruido." icon="spark" tone="gold" footer={quickReplies.map((reply) => <span key={reply} className="mono-pill">{reply}</span>)} /> : null}
        </div>
        <div className="rounded-[32px] border border-white/[0.10] bg-slate-950/70 p-4 shadow-[0_18px_60px_rgba(2,6,23,0.45)]">
          <div className="rounded-[28px] border border-white/[0.10] bg-[#0f172a] p-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div>
                <div className="text-sm font-semibold text-[color:var(--text-primary)]">{stageLabel || "Vista previa"}</div>
                <div className="text-xs text-slate-400">Flujo de conversación</div>
              </div>
              <Badge tone="green">En vivo</Badge>
            </div>
            <div className="space-y-3 py-4">
              <div className="ml-auto max-w-[85%] rounded-3xl rounded-br-lg border border-white/[0.10] bg-white/[0.04] px-4 py-3 text-sm text-slate-100">{userPrompt}</div>
              {blocks.map((block, index) => {
                if (block.type === "image") return <div key={index} className={`max-w-[88%] rounded-3xl border ${bubbleTone} overflow-hidden`}><div className="h-40 bg-[linear-gradient(135deg,rgba(255,255,255,0.08),rgba(255,255,255,0.02))]" /><div className="px-4 py-3 text-sm text-slate-100">{block.label || "Imagen"}</div></div>;
                if (block.type === "text") return <div key={index} className={`max-w-[88%] rounded-3xl rounded-bl-lg border px-4 py-3 text-sm text-slate-100 ${bubbleTone}`}>{block.text}</div>;
                return <div key={index} className="max-w-[88%] rounded-3xl border border-white/[0.10] bg-white/[0.03] px-4 py-3 text-sm text-slate-100">{Object.entries(block).filter(([key]) => key !== "type").slice(0, 5).map(([key, value]) => <div key={key} className="flex justify-between gap-3 py-1"><span className="text-slate-400">{key}</span><span>{typeof value === "object" ? JSON.stringify(value) : String(value)}</span></div>)}</div>;
              })}
            </div>
            <div className="border-t border-white/[0.08] pt-3 text-xs text-slate-400">{footer}</div>
          </div>
        </div>
      </div>
    </Section>
  );
}
