"use client";
import { useEffect } from "react";
import { reportFrontendError } from "./lib/reporting";
export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => { reportFrontendError({ source: "global-error-boundary", message: error?.message || "unknown global error", digest: error?.digest || null, stack: error?.stack || null, path: typeof window !== "undefined" ? window.location.pathname : null }); }, [error]);
  return <html lang="es"><body className="min-h-screen bg-slate-950 px-4 py-10 text-slate-50"><div className="mx-auto max-w-3xl rounded-3xl border border-rose-400/[0.20] bg-rose-400/[0.08] p-6"><div className="eyebrow">Error global</div><h1 className="mt-2 text-3xl font-semibold text-white">WAOS encontró un error general.</h1><p className="mt-3 text-sm leading-6 text-slate-200">Se registró el fallo con un identificador de contexto para soporte y observabilidad.</p><div className="mt-5 flex flex-wrap gap-2"><button className="primary-btn" onClick={() => reset()}>Recargar aplicación</button><a href="/login" className="secondary-btn">Volver al acceso</a></div></div></body></html>;
}
