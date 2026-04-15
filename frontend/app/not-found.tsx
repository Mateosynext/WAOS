import Link from "next/link";

export default function NotFound() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(16,185,129,0.12),_transparent_24%),linear-gradient(180deg,#07111f_0%,#0b1220_100%)] px-4 py-8 text-slate-50">
      <div className="mx-auto max-w-3xl">
        <section className="panel p-6 lg:p-8">
          <div className="eyebrow">Página no encontrada</div>
          <h1 className="mt-2 text-4xl font-semibold tracking-[-0.05em] text-white">Aquí no hay una pantalla útil.</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 lg:text-[15px]">
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
