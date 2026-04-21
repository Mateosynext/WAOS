export function normalizeDisplayError(error: unknown, fallback = "No se pudo completar la acción."): string {
  const raw =
    typeof error === "string"
      ? error
      : error instanceof Error
        ? (typeof (error as { digest?: unknown }).digest === "string" && String((error as { digest?: unknown }).digest).trim())
          || error.message
        : "";

  const message = String(raw || "").trim();
  if (!message) return fallback;
  if (/NEXT_REDIRECT/i.test(message)) return fallback;
  return message;
}
