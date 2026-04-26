"use client";

import type { AiCommandBotOption, AiCommandOrganization, AiCommandPayload } from "./types";

type Props = {
  organizations: AiCommandOrganization[];
  bots: AiCommandBotOption[];
  payload: AiCommandPayload;
  busy: boolean;
  onChange: (patch: Partial<AiCommandPayload>) => void;
  onSubmit: () => void;
};

const GODMODE_ENABLED = process.env.NEXT_PUBLIC_AI_ENABLE_GODMODE === "true";
const INTENSITIES: AiCommandPayload["intensity"][] = GODMODE_ENABLED
  ? ["conservative", "balanced", "aggressive", "savage", "godmode"]
  : ["conservative", "balanced", "aggressive", "savage"];
const BOOLEAN_FIELDS: Array<keyof Pick<AiCommandPayload, "auto_generate_knowledge" | "auto_generate_templates" | "auto_generate_tools" | "auto_run_simulations" | "auto_autofix" | "auto_prepare_go_live" | "auto_apply">> = [
  "auto_generate_knowledge",
  "auto_generate_templates",
  "auto_generate_tools",
  "auto_run_simulations",
  "auto_autofix",
  "auto_prepare_go_live",
  "auto_apply",
];

const FIELD_LABELS: Record<string, string> = {
  auto_generate_knowledge: "Generar knowledge base",
  auto_generate_templates: "Generar templates WhatsApp",
  auto_generate_tools: "Planear tools/integraciones",
  auto_run_simulations: "Correr simulaciones",
  auto_autofix: "Autofix seguro",
  auto_prepare_go_live: "Preparar readiness",
  auto_apply: "Auto apply bloqueado por seguridad",
};

export function AiCommandPrompt({ organizations, bots, payload, busy, onChange, onSubmit }: Props) {
  const canSubmit = Boolean(payload.organization_id && payload.user_description.trim().length >= 20 && !busy);
  return (
    <section className="glass-card p-5">
      <p className="eyebrow">AI Production Autopilot</p>
      <h1 className="mt-2 text-2xl font-semibold text-[color:var(--text-primary)]">Construir agente con IA</h1>
      <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Describe el negocio, ciudad, servicios, objetivo, restricciones y qué debe lograr WhatsApp. WAOS crea el wizard, valida, simula y deja el apply bajo aprobación humana.</p>

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <label className="field-label">Organización
          <select className="input-field mt-2" value={payload.organization_id} onChange={(event) => onChange({ organization_id: event.target.value })}>
            <option value="">Selecciona organización</option>
            {organizations.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}
          </select>
        </label>
        <label className="field-label">Bot existente opcional
          <select className="input-field mt-2" value={payload.bot_id || ""} onChange={(event) => onChange({ bot_id: event.target.value || null })}>
            <option value="">Crear bot nuevo al aplicar</option>
            {bots.map((bot) => <option key={bot.id} value={bot.id}>{bot.name}</option>)}
          </select>
        </label>
      </div>

      <label className="field-label mt-4">Descripción del negocio
        <textarea className="input-field mt-2 min-h-40" value={payload.user_description} onChange={(event) => onChange({ user_description: event.target.value })} placeholder="Ej. Clínica dental en CDMX que agenda limpiezas y ortodoncia por WhatsApp, debe pedir nombre, servicio, horario y escalar urgencias a humano..." />
      </label>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <label className="field-label">Industria opcional<input className="input-field mt-2" value={payload.vertical_id || ""} onChange={(event) => onChange({ vertical_id: event.target.value || null })} placeholder="dental, beauty, real-estate..." /></label>
        <label className="field-label">Subvertical opcional<input className="input-field mt-2" value={payload.subvertical || ""} onChange={(event) => onChange({ subvertical: event.target.value || null })} placeholder="ortodoncia, uñas, rentas..." /></label>
        <label className="field-label">Objetivo principal<input className="input-field mt-2" value={payload.primary_objective || ""} onChange={(event) => onChange({ primary_objective: event.target.value || null })} placeholder="agendar, vender, calificar" /></label>
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {INTENSITIES.map((intensity) => <button key={intensity} type="button" className={payload.intensity === intensity ? "primary-btn" : "secondary-btn"} onClick={() => onChange({ intensity })}>{intensity}</button>)}
      </div>

      <div className="mt-5 grid gap-2 md:grid-cols-2">
        {BOOLEAN_FIELDS.map((field) => (
          <label key={field} className="flex items-center justify-between gap-3 rounded-2xl border border-white/10 p-3 text-sm text-[color:var(--text-secondary)]">
            <span><span className="mono-pill">{field}</span> {FIELD_LABELS[field]}</span>
            <input type="checkbox" checked={Boolean(payload[field])} disabled={field === "auto_apply"} onChange={(event) => onChange({ [field]: event.target.checked } as Partial<AiCommandPayload>)} />
          </label>
        ))}
      </div>

      <button type="button" className="primary-btn mt-5 w-full" disabled={!canSubmit} onClick={onSubmit}>{busy ? "Construyendo agente..." : "Construir agente con IA"}</button>
    </section>
  );
}
