"use client";

export type CookieConsent = {
  necessary: boolean;
  analytics: boolean;
  preferences: boolean;
  marketing: boolean;
  version: string;
  updatedAt: string;
};

export const COOKIE_CONSENT_STORAGE_KEY = "waos-cookie-consent-v1";
export const COOKIE_CONSENT_COOKIE = "waos_cookie_consent";
export const COOKIE_CONSENT_VERSION = "1.0.0";
export const VISITOR_ID_STORAGE_KEY = "waos-visitor-id";

export function defaultCookieConsent(): CookieConsent {
  return {
    necessary: true,
    analytics: false,
    preferences: false,
    marketing: false,
    version: COOKIE_CONSENT_VERSION,
    updatedAt: new Date().toISOString(),
  };
}

export function readCookieConsent(): CookieConsent | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(COOKIE_CONSENT_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as CookieConsent) : null;
  } catch {
    return null;
  }
}

export function hasAnalyticsConsent(): boolean {
  return Boolean(readCookieConsent()?.analytics);
}

export function getOrCreateVisitorId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const existing = window.localStorage.getItem(VISITOR_ID_STORAGE_KEY);
    if (existing) return existing;
    const next = typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `visitor-${Date.now()}`;
    window.localStorage.setItem(VISITOR_ID_STORAGE_KEY, next);
    return next;
  } catch {
    return null;
  }
}

export function persistCookieConsent(consent: CookieConsent): CookieConsent {
  const payload = {
    ...consent,
    necessary: true,
    version: consent.version || COOKIE_CONSENT_VERSION,
    updatedAt: consent.updatedAt || new Date().toISOString(),
  };
  if (typeof window !== "undefined") {
    try {
      window.localStorage.setItem(COOKIE_CONSENT_STORAGE_KEY, JSON.stringify(payload));
    } catch {}
  }
  if (typeof document !== "undefined") {
    const encoded = encodeURIComponent(JSON.stringify(payload));
    const secure = typeof window !== "undefined" && window.location.protocol === "https:" ? "; Secure" : "";
    document.cookie = `${COOKIE_CONSENT_COOKIE}=${encoded}; Max-Age=${60 * 60 * 24 * 365}; Path=/; SameSite=Lax${secure}`;
  }
  return payload;
}
