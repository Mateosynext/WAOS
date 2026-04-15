import Link from "next/link";
import LoginForm from "../components/LoginForm";

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }

const errorMap: Record<string, string> = {
  sso_failed: "El inicio de sesión corporativo no se pudo completar. Intenta de nuevo o usa contraseña si tu cuenta la tiene.",
  invalid_state: "La verificación de seguridad del inicio con SSO expiró. Reintenta desde esta pantalla.",
  access_denied: "Tu proveedor corporativo negó el acceso o canceló la autorización.",
};

export default async function LoginPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const rawError = first(params.error);
  const initialMessage = rawError ? (errorMap[rawError] || decodeURIComponent(rawError)) : null;

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(16,185,129,0.15),_transparent_24%),linear-gradient(180deg,#07111f_0%,#0b1220_100%)] px-4 py-8 text-slate-50">
      <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <section className="panel p-6 lg:p-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-400/[0.20] bg-emerald-400/[0.10] px-3 py-1 text-[11px] font-medium uppercase tracking-[0.18em] text-emerald-100">
            WAOS · acceso claro
          </div>
          <h1 className="mt-5 text-4xl font-semibold tracking-[-0.05em] text-white lg:text-5xl">Entra sin adivinar.</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 lg:text-[15px]">
            Primero identificamos si tu organización usa SSO. Después completas contraseña y MFA en pasos claros, sin mezclar flujos enterprise con acciones básicas.
          </p>

          <div className="mt-8 grid gap-4 md:grid-cols-2">
            <div className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-5">
              <div className="eyebrow">1. Identifica tu acceso</div>
              <div className="mt-2 text-xl font-semibold text-white">Correo o SSO</div>
              <p className="mt-2 text-sm leading-6 text-slate-300">Escribe tu correo y descubre si tu empresa entra con proveedor corporativo.</p>
            </div>
            <div className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-5">
              <div className="eyebrow">2. Protege la entrada</div>
              <div className="mt-2 text-xl font-semibold text-white">Contraseña y MFA</div>
              <p className="mt-2 text-sm leading-6 text-slate-300">Si tu cuenta lo requiere, terminas aquí mismo con MFA sin salir de pantalla.</p>
            </div>
          </div>

          <div className="mt-6 grid gap-3 md:grid-cols-3">
            <Link href="/client/resumen" className="secondary-btn">Ver portal cliente</Link>
            <Link href="/organizations" className="secondary-btn">Cambiar organización</Link>
            <Link href="/login/recovery" className="secondary-btn">Recuperar acceso</Link>
          </div>
        </section>

        <section className="panel p-6 lg:p-8">
          <div className="eyebrow">Acceso</div>
          <h2 className="mt-2 text-2xl font-semibold text-white">Inicia sesión</h2>
          <p className="mt-3 text-sm leading-6 text-slate-300">
            Usa tu cuenta para entrar al panel correcto. Si tu organización exige SSO o MFA, aquí mismo completas ese flujo sin perder contexto.
          </p>
          <LoginForm initialMessage={initialMessage} />
        </section>
      </div>
    </main>
  );
}
