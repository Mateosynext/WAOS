"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { safeText } from "@/app/lib/ui";
import type { WizardAiIntensity, WizardAiPrefillResult } from "../services/wizardApi";
import { AI_DESCRIPTION_MAX_LENGTH, normalizeAiDescription } from "../services/wizardAutopilotContract";

type AiSetupAssistantProps = {
  disabled?: boolean;
  selectedVerticalLabel: string;
  selectedSubvertical: string;
  selectedPrimaryObjective: string;
  onGenerate: (input: { userDescription: string; intensity: WizardAiIntensity }) => Promise<WizardAiPrefillResult>;
  onAutopilot: (input: { userDescription: string; intensity: WizardAiIntensity }) => Promise<WizardAiPrefillResult>;
  onAccept: (result: WizardAiPrefillResult) => Promise<void>;
};

const MIN_AI_DESCRIPTION_LENGTH = 20;
const AUTOPILOT_RUNNING_MESSAGE = "Autopilot real corriendo en backend...";

function cardItems(items: unknown[]) {
  return items.map((item) => String(item || "").trim()).filter(Boolean).slice(0, 6);
}

function getAutopilotWizardId(result: WizardAiPrefillResult) {
  const dryRunWizard = result.dry_run_result?.wizard;
  const candidate = result.wizard_id || (typeof dryRunWizard === "object" && dryRunWizard ? String((dryRunWizard as Record<string, unknown>).id || "") : "") || (result.wizard ? String(result.wizard.id || "") : "");
  return String(candidate || "").trim();
}

function buildValidateHref(result: WizardAiPrefillResult) {
  const wizardId = getAutopilotWizardId(result);
  return `/bot-studio/create/validate${wizardId ? `?wizard_id=${encodeURIComponent(wizardId)}` : ""}`;
}
export function AiSetupAssistant({ disabled, selectedVerticalLabel, selectedSubvertical, selectedPrimaryObjective, onGenerate, onAutopilot, onAccept }: AiSetupAssistantProps) {
  const [description, setDescription] = useState("");
  const [result, setResult] = useState<WizardAiPrefillResult | null>(null);
  const [loading, setLoading] = useState<WizardAiIntensity | "">("");
  const [error, setError] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [applying, setApplying] = useState<"edit" | "autopilot" | "">("");
  const router = useRouter();

  const contextLabel = useMemo(() => [selectedVerticalLabel, selectedSubvertical, selectedPrimaryObjective].filter(Boolean).join(" · "), [selectedVerticalLabel, selectedSubvertical, selectedPrimaryObjective]);
  const normalizedDescription = normalizeAiDescription(description);
  const descriptionLength = normalizedDescription.trim().length;
  const descriptionIsTooShort = descriptionLength < MIN_AI_DESCRIPTION_LENGTH;
  const autopilotProgressMessage = applying === "autopilot" ? AUTOPILOT_RUNNING_MESSAGE : "Listo";

  const validateDescription = () => {
    if (descriptionIsTooShort) {
      setError(`Describe el negocio con al menos ${MIN_AI_DESCRIPTION_LENGTH} caracteres. Ahora hay ${descriptionLength}.`);
      return false;
    }
    return true;
  };

  const generate = async (intensity: WizardAiIntensity) => {
    if (disabled) {
      setError("Selecciona una organización e industria antes de generar con IA.");
      return;
    }
    if (loading || applying) return;
    setError("");
    if (!validateDescription()) return;
    setLoading(intensity);
    setAccepted(false);
    try {
      const next = await onGenerate({ userDescription: normalizedDescription, intensity });
      setResult(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo generar el setup con IA.");
    } finally {
      setLoading("");
    }
  };

  const accept = async () => {
    if (disabled) {
      setError("Selecciona una organización e industria antes de aplicar el wizard.");
      return;
    }
    if (loading || applying) return;
    setError("");
    if (!validateDescription()) return;
    setApplying("autopilot");
    setAccepted(false);
    try {
      const wired = await onAutopilot({ userDescription: normalizedDescription, intensity: "savage" });
      setResult(wired);
      setAccepted(true);
      router.push(buildValidateHref(wired));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo correr AI Autopilot end-to-end.");
    } finally {
      setApplying("");
    }
  };

  const edit = async () => {
    if (!result) return;
    if (disabled) {
      setError("Selecciona una organización e industria antes de editar detalles generados.");
      return;
    }
    if (loading || applying) return;
    setApplying("edit");
    setError("");
    try {
      await onAccept(result);
      setAccepted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron aplicar los detalles generados.");
    } finally {
      setApplying("");
    }
  };

  return (
    <section data-testid="ai-setup-assistant" className="rounded-[28px] border border-[color:var(--accent-border)] bg-[color:var(--accent-soft)] p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">AI Autopilot</div>
          <h3 className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-[color:var(--text-primary)]">Generar setup con IA dura</h3>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">
            Después de elegir industria/subvertical, describe el negocio y la IA arma nombre, tono, oferta, CTAs, FAQs, policies, handoff, integraciones, playbooks y launch notes. Al aceptar, corre backend end-to-end: batch save de todos los pasos, dry run, autofix iterativo y validación lista para apply humano.
          </p>
          <p className="mt-2 text-xs font-semibold uppercase tracking-[0.14em] text-[color:var(--text-tertiary)]">{safeText(contextLabel, "Selecciona industria, subvertical y objetivo para más precisión")}</p>
        </div>
        <div className="rounded-full border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] px-3 py-1 text-xs font-semibold text-[color:var(--text-secondary)]">
          {result ? `${Math.round((result.confidence || 0) * 100)}% confianza · ${result.source || "ia"}` : "Draft blindado"}
        </div>
      </div>

      <label className="mt-5 grid gap-2 rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
        <span className="text-sm font-semibold text-[color:var(--text-primary)]">Cuéntame tu negocio</span>
        <span className="text-xs leading-5 text-[color:var(--text-secondary)]">Ejemplo: “Es una clínica dental en Monterrey; vendemos ortodoncia, limpiezas e implantes. Queremos que WhatsApp agende valoraciones y filtre urgencias.”</span>
        <textarea
          className="field-input min-h-[120px]"
          value={description}
          onChange={(event) => setDescription(normalizeAiDescription(event.currentTarget.value))}
          maxLength={AI_DESCRIPTION_MAX_LENGTH}
          placeholder="Describe servicios, ciudad, objetivo, horarios, canal y restricciones importantes..."
        />
        <span className="text-right text-[11px] text-[color:var(--text-tertiary)]">{description.length}/{AI_DESCRIPTION_MAX_LENGTH}</span>
      </label>

      <p className={`mt-3 text-xs ${descriptionIsTooShort ? "text-[color:var(--warning-text)]" : "text-[color:var(--text-tertiary)]"}`}>
        {descriptionIsTooShort ? `Faltan ${MIN_AI_DESCRIPTION_LENGTH - descriptionLength} caracteres para poder generar con IA.` : "Descripcion lista para IA."}
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" className="primary-btn" disabled={Boolean(disabled || loading || applying)} onClick={accept}>
          {applying === "autopilot" ? autopilotProgressMessage : "Preparar y validar con Autopilot"}
        </button>
        <button type="button" className="secondary-btn" disabled={Boolean(disabled || loading || applying)} onClick={() => generate("aggressive")}>
          {loading === "aggressive" ? "Regenerando..." : "Regenerar más agresivo"}
        </button>
        <button type="button" className="secondary-btn" disabled={Boolean(disabled || loading || applying)} onClick={() => generate("savage")}>
          {loading === "savage" ? "Regenerando..." : "Modo 10x duro"}
        </button>
        <button type="button" className="secondary-btn" disabled={Boolean(disabled || loading || applying)} onClick={() => generate("conservative")}>
          {loading === "conservative" ? "Regenerando..." : "Regenerar más conservador"}
        </button>
      </div>
      {applying === "autopilot" ? (
        <div className="mt-3 rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] px-4 py-3 text-sm text-[color:var(--text-secondary)]" role="status" aria-live="polite">
          <div className="flex items-center gap-3">
            <span className="inline-block h-2.5 w-2.5 animate-pulse rounded-full bg-current" aria-hidden="true" />
            <span className="font-semibold text-[color:var(--text-primary)]">{autopilotProgressMessage}</span>
          </div>
          <p className="mt-2 text-xs leading-5">El backend está corriendo el flujo real. Para progreso paso a paso usa el AI Command Center, que consume SSE/polling reales.</p>
        </div>
      ) : null}
      {disabled ? <p className="mt-3 text-sm text-[color:var(--warning-text)]">Selecciona organización e industria antes de pedirle a la IA que arme el setup.</p> : null}
      {error ? <p className="mt-3 text-sm text-[color:var(--warning-text)]">{error}</p> : null}

      {result ? (
        <div className="mt-5 grid gap-4">
          <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
            <div className="text-sm font-semibold text-[color:var(--text-primary)]">{safeText(result.summary, "Setup generado por IA")}</div>
            <div className="mt-3 flex flex-wrap gap-2">
              <button type="button" className="primary-btn" disabled={Boolean(disabled || applying)} onClick={accept}>{applying === "autopilot" ? autopilotProgressMessage : "Preparar y validar con Autopilot"}</button>
              <button type="button" className="secondary-btn" disabled={Boolean(disabled || loading || applying)} onClick={edit}>{applying === "edit" ? "Aplicando..." : "Editar detalles importantes"}</button>
              {accepted ? <span className="rounded-full border border-[color:var(--success-border)] bg-[color:var(--success-soft)] px-3 py-2 text-xs font-semibold text-[color:var(--success-text)]">Setup guardado, validado y autofixeado</span> : null}
            </div>
          </div>

          {result.pipeline?.length ? (
            <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
              <div className="text-sm font-semibold text-[color:var(--text-primary)]">Pipeline end-to-end</div>
              <div className="mt-3 grid gap-2 md:grid-cols-3">
                {result.pipeline.map((step) => (
                  <div key={step.key || step.label} className="rounded-2xl border border-[color:var(--border-soft)] px-3 py-2 text-xs text-[color:var(--text-secondary)]">
                    <span className="font-semibold text-[color:var(--text-primary)]">{safeText(step.label, "Paso")}</span> · {safeText(step.status, "pending")}
                  </div>
                ))}
              </div>
              {result.next_action ? <p className="mt-3 text-xs leading-5 text-[color:var(--text-secondary)]"><strong>{safeText(result.next_action.label, "Siguiente acción")}:</strong> {safeText(result.next_action.detail, "Revisa los campos críticos antes de aplicar.")}</p> : null}
            </div>
          ) : null}
          <div className="grid gap-3 lg:grid-cols-3">
            {(result.generated_cards || []).map((card) => {
              const items = cardItems(card.items || []);
              return (
                <div key={card.key || card.title} className="rounded-[22px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
                  <div className="text-sm font-semibold text-[color:var(--text-primary)]">{safeText(card.title, "Bloque generado")}</div>
                  <ul className="mt-2 grid gap-1 text-xs leading-5 text-[color:var(--text-secondary)]">
                    {items.length ? items.map((item) => <li key={item}>• {item}</li>) : <li>• Sin items visibles</li>}
                  </ul>
                </div>
              );
            })}
          </div>
          <div className="grid gap-3 lg:grid-cols-2">
            <div className="rounded-[22px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4">
              <div className="text-sm font-semibold text-[color:var(--text-primary)]">Supuestos</div>
              <ul className="mt-2 grid gap-1 text-xs leading-5 text-[color:var(--text-secondary)]">
                {(result.assumptions || []).slice(0, 6).map((item) => <li key={item}>• {item}</li>)}
              </ul>
            </div>
            <div className="rounded-[22px] border border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] p-4">
              <div className="text-sm font-semibold text-[color:var(--text-primary)]">Solo confirma lo crítico</div>
              <ul className="mt-2 grid gap-1 text-xs leading-5 text-[color:var(--text-secondary)]">
                {(result.requires_user_confirmation || []).slice(0, 8).map((item) => <li key={item}>• {item}</li>)}
              </ul>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
