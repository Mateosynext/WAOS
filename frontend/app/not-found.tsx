import Link from "next/link";

export default function NotFound() {
  return (
    <main className="min-h-screen bg-[var(--client-shell-bg)] px-4 py-8 text-[color:var(--text-primary)]">
      <div className="mx-auto max-w-3xl">
        <section className="panel p-6 lg:p-8">
          <div className="eyebrow">Página no encontrada</div>
          <h1 className="mt-2 text-4xl font-semibold tracking-[-0.05em] text-[color:var(--text-primary)]">Aquí no hay una pantalla útil.</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-[color:var(--text-secondary)] lg:text-[15px]">
            Puede que la ruta haya cambiado durante el rediseño del frontend. Vuelve al inicio o entra al inbox para retomar trabajo real.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link href="/" className="primary-btn">Ir al inicio</Link>
            <Link href="/inbox" className="secondary-btn">Ir al inbox</Link>
          </div>
        </section>
      </div>
    </main>
  );
}
