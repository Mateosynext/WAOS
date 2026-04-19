"use client";

import { useEffect } from "react";
import { reportFrontendError } from "./lib/reporting";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    reportFrontendError({
      source: "route-error-boundary",
      message: error?.message || "unknown error",
      digest: error?.digest || null,
      stack: error?.stack || null,
      path: typeof window !== "undefined" ? window.location.pathname : null,
    });
  }, [error]);

  return (
    <main className="min-h-screen bg-[var(--client-shell-bg)] px-4 py-10 text-[color:var(--text-primary)]">
      <div className="mx-auto max-w-3xl rounded-3xl border border-[color:var(--danger-border)] bg-[color:var(--danger-soft)] p-6 shadow-[var(--shadow-soft)]">
        <div className="eyebrow">Error de pantalla</div>
        <h1 className="mt-2 text-3xl font-semibold text-[color:var(--text-primary)]">No pudimos cargar esta vista.</h1>
        <p className="mt-3 text-sm leading-6 text-[color:var(--text-secondary)]">
          El error ya quedó reportado con el contexto disponible. Puedes reintentar sin perder toda la sesión.
        </p>
        <div className="mt-5 flex flex-wrap gap-2">
          <button className="primary-btn" onClick={() => reset()}>Reintentar</button>
          <a href="/status" className="secondary-btn">Ir a estado interno</a>
        </div>
      </div>
    </main>
  );
}
