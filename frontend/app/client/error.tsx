"use client";

import Link from "next/link";

export default function ClientPortalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main id="main-content" className="min-h-screen bg-[var(--client-shell-bg)] text-[color:var(--text-primary)]">
      <div className="mx-auto max-w-[960px] px-4 py-10 sm:px-6 lg:px-8">
        <div className="rounded-[32px] border border-[color:var(--danger-border)] bg-[color:var(--surface-elevated)] p-6 shadow-[var(--shadow-xl)] sm:p-8">
          <div className="inline-flex items-center rounded-full border border-[color:var(--danger-border)] bg-[color:var(--danger-soft)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--danger-text)]">
            Portal cliente
          </div>
          <h1 className="mt-5 text-3xl font-semibold tracking-[-0.05em]">No pudimos abrir esta vista</h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-[color:var(--text-secondary)]">
            Protegimos la experiencia para no dejar una pantalla rota. Puedes recargar la sección o volver al resumen mientras se revisa la causa.
          </p>
          <div className="mt-6 rounded-[22px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 text-sm text-[color:var(--text-secondary)]">
            {error.message || "Ocurrió un error inesperado en el portal cliente."}
          </div>
          <div className="mt-6 flex flex-wrap gap-3">
            <button type="button" onClick={() => reset()} className="primary-btn">Reintentar</button>
            <Link href="/client/resumen" className="secondary-btn">Ir al resumen</Link>
          </div>
        </div>
      </div>
    </main>
  );
}
