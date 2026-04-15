import Link from "next/link";

export default function LoginRecoveryPage() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(16,185,129,0.15),_transparent_24%),linear-gradient(180deg,#07111f_0%,#0b1220_100%)] px-4 py-8 text-slate-50">
      <div className="mx-auto max-w-3xl">
        <section className="panel p-6 lg:p-8">
          <div className="eyebrow">Recuperar acceso</div>
          <h1 className="mt-2 text-4xl font-semibold tracking-[-0.05em] text-white">No te quedes atorado en login.</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 lg:text-[15px]">
            Si no recuerdas tu contraseña, no sabes si debes usar SSO o te bloqueó MFA, usa esta guía corta antes de abrir soporte.
          </p>

          <div className="mt-8 space-y-4">
            <div className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-5">
              <div className="font-semibold text-white">1. Confirma el camino correcto</div>
              <p className="mt-2 text-sm leading-6 text-slate-300">Si tu empresa usa proveedor corporativo, vuelve a login y busca SSO con tu correo antes de probar contraseña local.</p>
            </div>
            <div className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-5">
              <div className="font-semibold text-white">2. Revisa MFA</div>
              <p className="mt-2 text-sm leading-6 text-slate-300">Si perdiste el autenticador, usa tus recovery codes. Si tampoco los tienes, pide a tu administrador resetear MFA para tu cuenta.</p>
            </div>
            <div className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-5">
              <div className="font-semibold text-white">3. Escala con contexto</div>
              <p className="mt-2 text-sm leading-6 text-slate-300">Cuando abras soporte, comparte tu correo, organización, si usas SSO y el error visible. Eso acelera la resolución.</p>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <Link href="/login" className="primary-btn">Volver a login</Link>
            <Link href="/support" className="secondary-btn">Ir a soporte</Link>
          </div>
        </section>
      </div>
    </main>
  );
}
