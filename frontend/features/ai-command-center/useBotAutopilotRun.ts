"use client";
import { useCallback, useState } from "react";

export type AiCommandInput = {
  organization_id: string;
  bot_id?: string;
  user_description: string;
  vertical_id?: string;
  subvertical?: string;
  primary_objective?: string;
  language?: string;
  timezone?: string;
  intensity: "conservative" | "balanced" | "aggressive" | "savage" | "godmode";
  auto_generate_knowledge?: boolean;
  auto_generate_templates?: boolean;
  auto_generate_tools?: boolean;
  auto_run_simulations?: boolean;
  auto_autofix?: boolean;
  auto_prepare_go_live?: boolean;
  auto_apply?: boolean;
  max_cost_usd?: number;
};

async function readJsonSafely(response: Response) {
  const text = await response.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return { detail: { message: text } };
  }
}

function errorMessage(payload: any, fallback: string) {
  return payload?.detail?.message || payload?.detail?.code || payload?.detail || payload?.error?.message || fallback;
}

export function useBotAutopilotRun(initialRunId?: string | null) {
  const [runId, setRunId] = useState<string | null>(initialRunId || null);
  const [run, setRun] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const start = useCallback(async (input: AiCommandInput) => {
    setLoading(true);
    setError("");
    try {
      const sanitized = { ...input, auto_apply: false };
      const res = await fetch("/api/ai/bot-autopilot?async_mode=true", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(sanitized),
      });
      const payload = await readJsonSafely(res);
      if (!res.ok) throw new Error(errorMessage(payload, "No se pudo crear el workflow"));
      const data = payload?.data || payload;
      if (!data?.run_id) throw new Error("El backend no devolvio run_id");
      setRun(data);
      setRunId(String(data.run_id || ""));
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Error de Autopilot";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const refresh = useCallback(async (id = runId) => {
    if (!id) return null;
    const res = await fetch(`/api/ai/workflows/${encodeURIComponent(id)}`, { cache: "no-store" });
    const payload = await readJsonSafely(res);
    if (!res.ok) {
      const message = errorMessage(payload, "No se pudo cargar el workflow");
      setError(String(message));
      throw new Error(String(message));
    }
    const data = payload?.data || payload;
    setRun(data);
    return data;
  }, [runId]);

  return { runId, setRunId, run, loading, error, start, refresh };
}
