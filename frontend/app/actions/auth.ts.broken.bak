"use server";
import { redirect } from "next/navigation";
import { ACCESS_COOKIE, API_BASE, BOT_COOKIE, ORG_COOKIE, REFRESH_COOKIE, ActionState, cookies, normalizeActionError, readString, sessionCookieOptions } from "./shared";

export async function loginAction(_: ActionState, formData: FormData): Promise<ActionState> {
  const email = readString(formData, "email");
  const password = readString(formData, "password");
  const otpCode = readString(formData, "otp_code");
  const challengeId = readString(formData, "challenge_id");
  const mfaSetupCode = readString(formData, "mfa_setup_code");

  if (!API_BASE) {
    return { ok: false, error: "Configura API_INTERNAL_URL o API_BASE_URL para iniciar sesión." };
  }

  let redirectTo = "/";

  try {
    const response = await fetch(${API_BASE}/api/v1/auth/login, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        password,
        otp_code: otpCode || null,
        challenge_id: challengeId || null,
        mfa_setup_code: mfaSetupCode || null
      }),
      cache: "no-store",
    });

    if (!response.ok) {
      let detail = "No se pudo iniciar sesión";
      try {
        const data = await response.json();
        detail =
          typeof data?.detail === "string"
            ? data.detail
            : data?.detail?.message || JSON.stringify(data?.detail || data);
      } catch {
        detail = await response.text();
      }
      return { ok: false, error: detail || "No se pudo iniciar sesión" };
    }

    const data = await response.json();

    if (data.mfa_required) {
      return { ok: false, mfaRequired: true, challengeId: data.challenge_id };
    }

    if (data.mfa_setup_required) {
      return {
        ok: false,
        mfaSetupRequired: true,
        mfaSetup: {
          qrSvgDataUrl: data?.mfa_setup?.qr_svg_data_url,
          provisioningUri: data?.mfa_setup?.provisioning_uri,
          recoveryCodes: data?.mfa_setup?.recovery_codes || [],
        },
      };
    }

    const store = await cookies();
    const organizations = data.user?.organizations || [];
    const orgId = organizations.length === 1 ? organizations[0]?.id || "" : "";

    store.set(ACCESS_COOKIE, data.access_token, sessionCookieOptions.access());
    store.set(REFRESH_COOKIE, data.refresh_token, sessionCookieOptions.refresh());

    if (orgId) {
      store.set(ORG_COOKIE, orgId, sessionCookieOptions.scope());
    } else {
      store.delete(ORG_COOKIE);
    }

    redirectTo =
      organizations.length > 1 && data.user?.global_role !== "client"
        ? "/organizations?source=login"
        : data.user?.global_role === "client"
          ? "/client"
          : "/";
  } catch (error) {
    return { ok: false, error: normalizeActionError(error, "No se pudo iniciar sesión en este momento.") };
  }

  redirect(redirectTo);
}

export async function logoutAction() {
  const store = await cookies();
  const access = store.get(ACCESS_COOKIE)?.value;
  const refresh = store.get(REFRESH_COOKIE)?.value;

  if (access && refresh && API_BASE) {
    await fetch(${API_BASE}/api/v1/auth/logout, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: Bearer  },
      body: JSON.stringify({ refresh_token: refresh }),
      cache: "no-store",
    }).catch(() => null);
  }

  store.delete(ACCESS_COOKIE);
  store.delete(REFRESH_COOKIE);
  store.delete(ORG_COOKIE);
  store.delete(BOT_COOKIE);

  redirect("/login");
}
