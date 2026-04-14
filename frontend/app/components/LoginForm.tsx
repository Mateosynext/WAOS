"use client";
import { useActionState, useMemo, useState } from "react";
import { loginAction } from "../actions";
import { trackFrontendEvent } from "../lib/analytics";
import { validateLogin } from "../lib/forms";
import { FieldError, UiMessage } from "./UiMessage";

type SsoProvider = { id?: string; button_label?: string; organization_name?: string; provider?: string };
const initialState = { ok: false };

export default function LoginForm() {
  const [state, formAction, pending] = useActionState(loginAction, initialState);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [ssoProviders, setSsoProviders] = useState<SsoProvider[]>([]);
  const [ssoLoading, setSsoLoading] = useState(false);
  const needsMfa = useMemo(() => Boolean(state?.mfaRequired), [state?.mfaRequired]);
  const needsMfaSetup = useMemo(() => Boolean(state?.mfaSetupRequired), [state?.mfaSetupRequired]);

  async function lookupSso(email: string) {
    if (!email || !email.includes("@")) { setSsoProviders([]); return; }
    setSsoLoading(true);
    try {
      const response = await fetch(`/api/auth/sso/providers?email=${encodeURIComponent(email)}`, { cache: "no-store" });
      const data = await response.json().catch(() => []);
      setSsoProviders(Array.isArray(data) ? data : []);
    } finally {
      setSsoLoading(false);
    }
  }

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    const values = Object.fromEntries(new FormData(event.currentTarget).entries()) as Record<string, string>;
    const nextErrors = validateLogin(values);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      trackFrontendEvent("form_error", window.location.pathname, Object.keys(nextErrors).join(","));
      event.preventDefault();
    }
  }

  return (
    <div className="mt-6 space-y-4">
      {(state?.error || needsMfaSetup) ? (
        <UiMessage title={needsMfaSetup ? "Activa MFA para continuar" : "No pudimos iniciar sesión"} tone={needsMfaSetup ? "warning" : "error"}>
          {needsMfaSetup ? "Escanea el QR o usa el URI de configuración, valida un código y luego completa el challenge MFA para entrar." : state?.error}
        </UiMessage>
      ) : null}
      <form className="space-y-4" action={formAction} onSubmit={onSubmit} noValidate>
        <label className="field-label">Correo
          <input className="field-input" type="email" name="email" placeholder="tu@empresa.com" autoComplete="email" required aria-invalid={Boolean(errors.email)} onBlur={(event) => void lookupSso(event.currentTarget.value)} />
          <FieldError message={errors.email} />
        </label>
        <label className="field-label">Contraseña
          <input className="field-input" type="password" name="password" placeholder="Tu contraseña" autoComplete="current-password" required aria-invalid={Boolean(errors.password)} />
          <FieldError message={errors.password} />
        </label>
        {needsMfaSetup ? (
          <div className="space-y-3 rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4 text-sm text-slate-200">
            <div className="font-medium text-white">Paso 1 · Configura tu autenticador</div>
            {state?.mfaSetup?.qrSvgDataUrl ? <img src={state.mfaSetup.qrSvgDataUrl} alt="QR MFA" className="max-w-[220px] rounded-xl bg-white p-3" /> : null}
            {state?.mfaSetup?.provisioningUri ? <div className="break-all text-xs text-slate-300">{state.mfaSetup.provisioningUri}</div> : null}
            {state?.mfaSetup?.recoveryCodes?.length ? <div><div className="mb-2 text-white">Recovery codes</div><div className="grid gap-1 text-xs text-slate-300">{state.mfaSetup.recoveryCodes.map((item) => <code key={item}>{item}</code>)}</div></div> : null}
            <label className="field-label">Código inicial de MFA
              <input className="field-input" type="text" name="mfa_setup_code" inputMode="numeric" pattern="[0-9]{6}" placeholder="123456" autoComplete="one-time-code" required />
            </label>
          </div>
        ) : null}
        {needsMfa ? (
          <>
            <input type="hidden" name="challenge_id" value={state.challengeId || ""} />
            <UiMessage title="Confirma con MFA" tone="warning">Tu cuenta requiere un código de 6 dígitos antes de entrar.</UiMessage>
            <label className="field-label">Código MFA
              <input className="field-input" type="text" name="otp_code" inputMode="numeric" pattern="[0-9]{6}" placeholder="123456" autoComplete="one-time-code" required aria-invalid={Boolean(errors.otp_code)} />
              <FieldError message={errors.otp_code} />
            </label>
          </>
        ) : null}
        <button className="primary-btn w-full" type="submit" disabled={pending}>{pending ? "Entrando…" : needsMfa || needsMfaSetup ? "Validar y entrar" : "Entrar"}</button>
      </form>
      <div className="space-y-3 rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4 text-sm text-slate-300">
        <div className="font-medium text-white">Entrar con SSO</div>
        <p>Escribe tu correo y sal del campo para detectar proveedores activos de tu organización.</p>
        {ssoLoading ? <div>Cargando proveedores…</div> : null}
        {ssoProviders.length ? (
          <div className="flex flex-wrap gap-2">
            {ssoProviders.map((provider) => (
              <a key={provider.id || provider.organization_name} className="secondary-btn" href={`/api/auth/sso/start?provider_id=${encodeURIComponent(String(provider.id || ""))}`}>
                {provider.button_label || `Entrar con ${provider.organization_name || provider.provider || "SSO"}`}
              </a>
            ))}
          </div>
        ) : <div className="text-xs text-slate-400">No encontramos SSO para ese correo todavía.</div>}
      </div>
    </div>
  );
}
