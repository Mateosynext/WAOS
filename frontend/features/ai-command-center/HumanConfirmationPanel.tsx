"use client";
import { useState } from "react";

async function readJsonSafely(response: Response) {
  const text = await response.text();
  if (!text) return {};
  try { return JSON.parse(text); } catch { return { detail: { message: text } }; }
}

export function HumanConfirmationPanel({ runId, items, onConfirmed }: { runId?: string | null; items?: Array<Record<string, any>>; onConfirmed?: () => void }) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});

  async function confirm(item: Record<string, any>, status = "confirmed") {
    if (!runId) return;
    const fieldKey = String(item.field_key || "");
    const confirmedValue = values[fieldKey] || String(item.confirmed_value || item.suggested_value || "").trim();
    if (status === "confirmed" && !confirmedValue) {
      setErrors((current) => ({ ...current, [fieldKey]: "Este campo requiere valor confirmado, rango o regla segura." }));
      return;
    }
    const res = await fetch(`/api/ai/workflows/${encodeURIComponent(runId)}/human-confirmations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ field_key: fieldKey, label: item.label, reason: item.reason, status, confirmed_value: confirmedValue || status }),
    });
    const payload = await readJsonSafely(res);
    if (!res.ok) {
      setErrors((current) => ({ ...current, [fieldKey]: String(payload?.detail?.message || payload?.detail || "No se pudo confirmar") }));
      return;
    }
    await fetch(`/api/ai/workflows/${encodeURIComponent(runId)}/go-live-readiness`, { method: "POST" });
    setErrors((current) => ({ ...current, [fieldKey]: "" }));
    onConfirmed?.();
  }

  return <section className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5"><div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Human Confirmation</div><h3 className="text-xl font-semibold">Solo campos críticos que la IA no puede inventar</h3><div className="mt-4 grid gap-2">{(items||[]).length?(items||[]).map((item,index)=>{ const key=String(item.field_key||index); const status=String(item.status||"pending"); const confirmed=status!=="pending"; return <div key={key} className="rounded-2xl border border-[color:var(--border-soft)] p-3"><div className="flex items-center justify-between gap-3"><div className="font-semibold">{String(item.label||item.field_key)}</div><span className="rounded-full border px-2 py-1 text-xs">{status}</span></div><p className="text-sm text-[color:var(--text-secondary)]">{String(item.reason||"Pendiente de confirmar")}</p><div className="mt-3 grid gap-2 md:grid-cols-[1fr_auto]"><input className="field-input" placeholder="Valor confirmado, rango o regla de escalamiento" value={values[key]??String(item.confirmed_value||"")} onChange={(event)=>setValues((current)=>({...current,[key]:event.target.value}))} disabled={confirmed}/><button className="secondary-btn" disabled={!runId||confirmed} onClick={()=>confirm(item,"confirmed")}>Confirmar</button></div>{errors[key]?<p className="mt-2 text-sm text-[color:var(--warning-text)]">{errors[key]}</p>:null}<div className="mt-2 flex flex-wrap gap-2 text-xs"><button type="button" className="underline" disabled={!runId||confirmed} onClick={()=>confirm(item,"range_confirmed")}>rango</button><button type="button" className="underline" disabled={!runId||confirmed} onClick={()=>confirm(item,"deferred_safe")}>depende de valoración</button><button type="button" className="underline" disabled={!runId||confirmed} onClick={()=>confirm(item,"blocked_response")}>bloquear respuesta</button><button type="button" className="underline" disabled={!runId||confirmed} onClick={()=>confirm(item,"escalate_to_human")}>escalar a humano</button></div></div>}):<p className="text-sm text-[color:var(--text-secondary)]">Aún no hay blockers humanos.</p>}</div></section>;
}
