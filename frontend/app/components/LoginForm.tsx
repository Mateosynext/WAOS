"use client";

import { useActionState, useEffect, useMemo, useState } from "react";
import { loginAction } from "@/app/actions/auth";
import { trackFrontendEvent } from "../lib/analytics";
import { validateLogin } from "../lib/forms";
import { FieldError, UiMessage } from "./UiMessage";

type SsoProvider = { id?: string; button_label?: string; organization_name?: string; provider?: string };
type LoginFormProps = { initialMessage?: string | null };

const initialState = { ok: false };

function CopyButton({ value, label }: { value: string; label: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className="secondary-btn"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value);
          setCopied(true);
          setTimeout(() => setCopied(false), 1400);
        } catch {
          setCopied(false);
        }
      }}
    >
      {copied ? `${label} copiado` : label}
    </button>
  );
}

function StepChip({ active, done, label }: { active?: boolean; done?: boolean; label: string }) {
  return (
    <div className={`rounded-2xl border px-3 py-2 text-xs uppercase tracking-[0.16em] ${active ? "border-emerald-400/[0.24] bg-emerald-400/[0.12] text-emerald-100" : done ? "border-sky-400/[0.22] bg-sky-400/[0.10] text-sky-100" : "border-white/[0.08] bg-white/[0.03] text-slate-400"}`}>
      {label}
    </div>
  );
}

export default function LoginForm({ initialMessage }: LoginFormProps) {
  const [state, formAction, pending] = useActionState(loginAction, initialState);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [email, setEmail] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [ssoProviders, setSsoProviders] = useState<SsoProvider[]>([]);
  const [ssoLoading, setSsoLoading] = useState(false);
  const [savedCodes, setSavedCodes] = useState(false);
  const needsMfa = useMemo(() => Boolean(state?.mfaRequired), [state?.mfaRequired]);
  const needsMfaSetup = useMemo(() => Boolean(state?.mfaSetupRequired), [state?.mfaSetupRequired]);

  async function lookupSso(targetEmail = email) {
    if (!targetEmail || !targetEmail.includes("@")) {
      setSsoProviders([]);
      return;
    }
    setSsoLoading(true);
    try {
      const response = await fetch(`/api/auth/sso/providers?email=${encodeURIComponent(targetEmail)}`, { cache: "no-store" });
      const data = await response.json().catch(() => []);
      setSsoProviders(Array.isArray(data) ? data : []);
    } finally {
      setSsoLoading(false);
    }
  }

  useEffect(() => {
    if (!email || !email.includes("@")) {
      setSsoProviders([]);
      return;
    }
    const timer = window.setTimeout(() => {
      void lookupSso(email);
    }, 500);
    return () => window.clearTimeout(timer);
  }, [email]);

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    const values = Object.fromEntries(new FormData(event.currentTarget).entries()) as Record<string, string>;
    const nextErrors = validateLogin(values);
    if (needsMfaSetup && !savedCodes) {
      nextErrors.recovery_codes = "Confirma primero que guardaste tus recovery codes.";
    }
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      trackFrontendEvent("form_error", window.location.pathname, Object.keys(nextErrors).join(","));
      event.preventDefault();
    }
  }

  const message = needsMfaSetup
    ? "Primero termina la configuración de seguridad. Guarda los recovery codes y valida el código inicial antes de entrar."
    : state?.error || initialMessage || null;

  const currentStep = needsMfaSetup ? 2 : needsMfa ? 2 : 1;

  return (
    <div className="mt-6 space-y-4">
      <div className="flex flex-wrap gap-2">
        <StepChip label="1. Credenciales" active={currentStep === 1} done={currentStep > 1} />
        <StepChip label="2. Seguridad" active={currentStep === 2} done={false} />
        <StepChip label="3. Entrando" active={pending} />
      </div>

      {message ? (
        <UiMessage title={needsMfaSetup ? "Configura seguridad antes de entrar" : "Revisa tu acceso"} tone={needsMfaSetup ? "warning" : "error"}>
          {message}
        </UiMessage>
      ) : null}

      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4">
          <div className="eyebrow">Entrar con cuenta</div>
          <div className="mt-2 text-base font-semibold text-white">Correo y contraseña</div>
          <p className="mt-2 text-sm leading-6 text-slate-300">Usa tu acceso normal y aquí mismo terminas MFA si tu organización lo requiere.</p>
        </div>
        <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4">
          <div className="eyebrow">Entrar con empresa</div>
          <div className="mt-2 text-base font-semibold text-white">SSO corporativo</div>
          <p className="mt-2 text-sm leading-6 text-slate-300">Escribe tu correo y te mostramos si hay inicio de sesión corporativo activo para ese dominio.</p>
        </div>
      </div>

      <form className="space-y-4" action={formAction} onSubmit={onSubmit} noValidate>
        <label className="field-label">
          Correo
          <div className="flex flex-col gap-2 md:flex-row">
            <input
              className="field-input flex-1"
              type="email"
              name="email"
              placeholder="tu@empresa.com"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.currentTarget.value)}
              required
              aria-invalid={Boolean(errors.email)}
            />
            <button type="button" className="secondary-btn md:self-end" onClick={() => void lookupSso(email)} disabled={!email || ssoLoading}>
              {ssoLoading ? "Buscando…" : "Ver SSO"}
            </button>
          </div>
          <FieldError message={errors.email} />
        </label>

        {!needsMfa && !needsMfaSetup ? (
          <label className="field-label">
            Contraseña
            <div className="flex flex-col gap-2 md:flex-row">
              <input
                className="field-input flex-1"
                type={showPassword ? "text" : "password"}
                name="password"
                placeholder="Tu contraseña"
                autoComplete="current-password"
                required
                aria-invalid={Boolean(errors.password)}
              />
              <button type="button" className="secondary-btn md:self-end" onClick={() => setShowPassword((value) => !value)}>
                {showPassword ? "Ocultar" : "Mostrar"}
              </button>
            </div>
            <FieldError message={errors.password} />
          </label>
        ) : null}

        {needsMfaSetup ? (
          <div className="space-y-4 rounded-3xl border border-amber-400/[0.18] bg-amber-400/[0.08] p-4 text-sm text-slate-100">
            <div>
              <div className="eyebrow text-amber-100">Paso 2A</div>
              <div className="mt-1 text-lg font-semibold text-white">Configura tu autenticador</div>
              <p className="mt-2 leading-6 text-slate-200">Escanea el QR o usa el URI manual, guarda los recovery codes y solo después valida el código inicial.</p>
            </div>
            {state?.mfaSetup?.qrSvgDataUrl ? <img src={state.mfaSetup.qrSvgDataUrl} alt="QR MFA" className="max-w-[220px] rounded-xl bg-white p-3" /> : null}
            {state?.mfaSetup?.provisioningUri ? (
              <div className="space-y-2 rounded-2xl border border-white/[0.08] bg-slate-950/40 p-3">
                <div className="text-xs uppercase tracking-[0.16em] text-slate-500">URI manual</div>
                <div className="break-all text-xs text-slate-300">{state.mfaSetup.provisioningUri}</div>
                <CopyButton value={state.mfaSetup.provisioningUri} label="Copiar URI" />
              </div>
            ) : null}
            {state?.mfaSetup?.recoveryCodes?.length ? (
              <div className="space-y-2">
                <div className="text-white">Recovery codes</div>
                <div className="grid gap-1 rounded-2xl border border-white/[0.08] bg-slate-950/40 p-3 text-xs text-slate-300">
                  {state.mfaSetup.recoveryCodes.map((item) => <code key={item}>{item}</code>)}
                </div>
                <div className="flex flex-wrap gap-2">
                  <CopyButton value={state.mfaSetup.recoveryCodes.join("\n")} label="Copiar códigos" />
                </div>
                <label className="flex items-start gap-3 rounded-2xl border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-sm text-slate-200">
                  <input type="checkbox" checked={savedCodes} onChange={(event) => setSavedCodes(event.currentTarget.checked)} className="mt-1" />
                  <span>Ya guardé mis recovery codes en un lugar seguro.</span>
                </label>
                <FieldError message={errors.recovery_codes} />
              </div>
            ) : null}
            <label className="field-label">
              Paso 2B · Código inicial de MFA
              <input className="field-input" type="text" name="mfa_setup_code" inputMode="numeric" pattern="[0-9]{6}" placeholder="123456" autoComplete="one-time-code" required />
            </label>
          </div>
        ) : null}

        {needsMfa ? (
          <>
            <input type="hidden" name="challenge_id" value={state.challengeId || ""} />
            <UiMessage title="Paso 2 · Confirma con MFA" tone="warning">Tu cuenta requiere un código de 6 dígitos antes de entrar.</UiMessage>
            <label className="field-label">
              Código MFA
              <input className="field-input" type="text" name="otp_code" inputMode="numeric" pattern="[0-9]{6}" placeholder="123456" autoComplete="one-time-code" required aria-invalid={Boolean(errors.otp_code)} />
              <FieldError message={errors.otp_code} />
            </label>
          </>
        ) : null}

        <button className="primary-btn w-full" type="submit" disabled={pending}>
          {pending ? "Entrando…" : needsMfa || needsMfaSetup ? "Validar y entrar" : "Entrar con correo y contraseña"}
        </button>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <a href="/login/recovery" className="text-sm font-medium text-emerald-300 transition hover:text-emerald-200">Olvidé mi contraseña o mi MFA</a>
          <span className="text-xs text-slate-500">Ruta sugerida: correo → detectar SSO → contraseña → MFA</span>
        </div>
      </form>

      <div className="space-y-3 rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4 text-sm text-slate-300">
        <div className="font-medium text-white">Entrar con SSO</div>
        <p>Buscamos proveedores activos según tu correo. Así no mezclas contraseña local con acceso corporativo.</p>
        {ssoLoading ? <div>Cargando proveedores…</div> : null}
        {ssoProviders.length ? (
          <div className="flex flex-wrap gap-2">
            {ssoProviders.map((provider) => (
              <a key={provider.id || provider.organization_name} className="secondary-btn" href={`/api/auth/sso/start?provider_id=${encodeURIComponent(String(provider.id || ""))}`}>
                {provider.button_label || `Entrar con ${provider.organization_name || provider.provider || "SSO"}`}
              </a>
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-white/[0.10] px-4 py-3 text-xs text-slate-400">
            {email && email.includes("@") ? "No encontramos SSO activo para este correo. Si tu empresa sí usa SSO, confirma el dominio o intenta con otra cuenta." : "Escribe tu correo y te diremos si tu organización tiene acceso corporativo habilitado."}
          </div>
        )}
      </div>
    </div>
  );
}
