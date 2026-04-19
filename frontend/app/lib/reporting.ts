const FRONTEND_ERRORS_ENDPOINT = "/api/v1/observability/frontend-errors";

export async function reportFrontendError(payload: Record<string, unknown>) {
  try {
    await fetch(FRONTEND_ERRORS_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      keepalive: true,
    });
  } catch {}
}
