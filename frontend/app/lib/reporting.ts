import { getClientApiBase } from "./env";
export async function reportFrontendError(payload: Record<string, unknown>) {
  const base = getClientApiBase();
  if (!base) return;
  try {
    await fetch(`${base}/api/v1/observability/frontend-errors`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      keepalive: true,
    });
  } catch {}
}
