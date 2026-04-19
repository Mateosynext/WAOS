import Link from "next/link";

export default function LoginRecoveryPage() {
  return (
    <main className="min-h-screen bg-[var(--client-shell-bg)] px-4 py-8 text-[color:var(--text-primary)]">
      <div className="mx-auto max-w-3xl">
        <section className="panel p-6 lg:p-8">
          <div className="eyebrow">Recuperar acceso</div>
          <h1 className="mt-2 text-4xl font-semibold tracking-[-0.05em] text-[color:var(--text-primary)]">No te quedes atorado en login.</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-[color:var(--text-secondary)] lg:text-[15px]">
            Si no recuerdas tu contraseña, no sabes si debes usar SSO o te bloqueó MFA, usa esta guía corta antes de abrir soporte.
          </p>

          <div className="mt-8 space-y-4">
            <div className="rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-5">
              <div className="font-semibold text-[color:var(--text-primary)]">1. Confirma el camino correcto</div>
              <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Si tu empresa usa proveedor corporativo, vuelve a login y busca SSO con tu correo antes de probar contraseña local.</p>
            </div>
            <div className="rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-5">
              <div className="font-semibold text-[color:var(--text-primary)]">2. Revisa MFA</div>
              <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Si perdiste el autenticador, usa tus recovery codes. Si tampoco los tienes, pide a tu administrador resetear MFA para tu cuenta.</p>
            </div>
            <div className="rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-5">
              <div className="font-semibold text-[color:var(--text-primary)]">3. Escala con contexto</div>
              <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Cuando abras soporte, comparte tu correo, organización, si usas SSO y el error visible. Eso acelera la resolución.</p>
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
