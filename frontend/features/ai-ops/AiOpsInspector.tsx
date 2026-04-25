"use client";
import { useEffect, useState } from "react";

type Workflow = { run?: Record<string, any>; steps?: Array<Record<string, any>>; events?: Array<Record<string, any>>; human_confirmations?: Array<Record<string, any>>; result?: Record<string, any> };

export function AiOpsInspector({ initialRunId }: { initialRunId?: string | null }) {
  const [runId, setRunId] = useState(initialRunId || "");
  const [data, setData] = useState<Workflow | null>(null);
  const [error, setError] = useState("");
  async function load(id = runId) {
    if (!id) return;
    setError("");
    const res = await fetch(`/api/ai/workflows/${encodeURIComponent(id)}`, { cache: "no-store" });
    const payload = await res.json();
    if (!res.ok) { setError(payload?.detail?.message || payload?.detail || "No se pudo cargar el run"); return; }
    setData(payload?.data || payload);
  }
  useEffect(() => { if (initialRunId) void load(initialRunId); }, [initialRunId]);
  const run = data?.run || {};
  const result = data?.result || run.result_json || {};
  return <section className="grid gap-5 rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5"><div><h2 className="text-xl font-semibold">AI Operations Inspector</h2><p className="mt-2 text-sm text-[color:var(--text-secondary)]">Inspecciona workflow runs, wizard steps, dry runs, autofix, simulation, readiness, runtime turns, policy evals, tools, outcomes, costs y provider failures.</p></div><div className="grid gap-2 md:grid-cols-[1fr_auto]"><input className="field-input" placeholder="run_id" value={runId} onChange={(event)=>setRunId(event.target.value)} /><button className="secondary-btn" onClick={()=>load()}>Abrir run</button></div>{error?<p className="rounded-2xl border p-3 text-sm text-[color:var(--warning-text)]">{error}</p>:null}{data?<div className="grid gap-4"><div className="grid gap-3 md:grid-cols-4"><div className="rounded-2xl border p-3"><div className="text-xs uppercase">status</div><strong>{String(run.status || result.status || "unknown")}</strong></div><div className="rounded-2xl border p-3"><div className="text-xs uppercase">progress</div><strong>{String(run.progress || result.progress || 0)}%</strong></div><div className="rounded-2xl border p-3"><div className="text-xs uppercase">cost</div><strong>${String(run.cost_estimate_usd || 0)}</strong></div><div className="rounded-2xl border p-3"><div className="text-xs uppercase">readiness</div><strong>{String(result.go_live_readiness?.status || "pending")}</strong></div></div><div className="grid gap-4 xl:grid-cols-2"><Panel title="Timeline" items={data.events || []} main="event_type" sub="message" /><Panel title="Steps" items={data.steps || []} main="step_key" sub="status" /><Panel title="Human confirmations" items={data.human_confirmations || []} main="field_key" sub="status" /><pre className="max-h-[420px] overflow-auto rounded-2xl border p-3 text-xs">{JSON.stringify(result, null, 2)}</pre></div></div>:<p className="text-sm text-[color:var(--text-secondary)]">Abre un run para ver timeline, inputs/outputs, modelos, latencia, costos y artifacts.</p>}</section>;
}

function Panel({ title, items, main, sub }: { title: string; items: Array<Record<string, any>>; main: string; sub: string }) {
  return <div className="rounded-2xl border p-3"><h3 className="font-semibold">{title}</h3><ol className="mt-3 grid gap-2">{items.length?items.map((item,index)=><li key={String(item.id||index)} className="rounded-xl border p-2 text-sm"><div className="font-medium">{String(item[main]||"")}</div><p className="text-[color:var(--text-secondary)]">{String(item[sub]||"")}</p></li>):<li className="text-sm text-[color:var(--text-secondary)]">Sin datos todavía.</li>}</ol></div>;
}
