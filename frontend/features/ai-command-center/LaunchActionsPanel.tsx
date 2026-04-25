"use client";
import { useState } from "react";

async function readJsonSafely(response: Response) {
  const text = await response.text();
  if (!text) return {};
  try { return JSON.parse(text); } catch { return { detail: { message: text } }; }
}

export function LaunchActionsPanel({runId,readiness,onChanged}:{runId?:string|null; readiness?:Record<string,any>; onChanged?:()=>void}){
  const [error,setError]=useState("");
  const blocked=readiness?.status==="blocked";
  async function post(action:string, body?:Record<string,unknown>){
    if(!runId)return;
    setError("");
    const res=await fetch(`/api/ai/workflows/${encodeURIComponent(runId)}/${action}`,{method:"POST",headers:{"Content-Type":"application/json"},body:body?JSON.stringify(body):undefined});
    const payload=await readJsonSafely(res);
    if(!res.ok){ setError(String(payload?.detail?.message||payload?.detail?.code||payload?.detail||"Accion bloqueada")); return; }
    onChanged?.();
  }
  return <section className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5"><div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">Launch Actions</div><div className="mt-4 flex flex-wrap gap-2"><button className="secondary-btn" disabled={!runId} onClick={()=>post("simulate")}>Rerun simulation</button><button className="secondary-btn" disabled={!runId} onClick={()=>post("go-live-readiness")}>Recheck readiness</button><button className="secondary-btn" disabled={!runId||blocked} onClick={()=>post("prepare-apply")}>Prepare apply</button><button className="primary-btn" disabled={!runId||blocked} onClick={()=>post("apply",{confirm:true})}>Apply safely</button><button className="secondary-btn" disabled={!runId||blocked} onClick={()=>post("prepare-canary")}>Prepare canary</button><a className="secondary-btn" href={runId?`/ai-ops?run_id=${runId}`:"/ai-ops"}>Open AI Ops Inspector</a></div>{blocked?<p className="mt-3 text-sm text-[color:var(--warning-text)]">Apply bloqueado porque readiness está blocked. Confirma campos críticos y recalcula readiness.</p>:null}{error?<p className="mt-3 text-sm text-[color:var(--warning-text)]">{error}</p>:null}</section>
}
