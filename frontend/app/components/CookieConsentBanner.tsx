"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getClientApiBase } from "../lib/env";
import {
  type CookieConsent,
  COOKIE_CONSENT_VERSION,
  defaultCookieConsent,
  getOrCreateVisitorId,
  persistCookieConsent,
  readCookieConsent,
} from "../lib/legal-consent";

export default function CookieConsentBanner() {
  const [mounted, setMounted] = useState(false);
  const [open, setOpen] = useState(false);
  const [showManager, setShowManager] = useState(false);
  const [consent, setConsent] = useState<CookieConsent>(defaultCookieConsent());

  useEffect(() => {
    setMounted(true);
    const stored = readCookieConsent();
    if (!stored) {
      setOpen(true);
      return;
    }
    setConsent(stored);
  }, []);

  const canShowFloatingButton = useMemo(() => mounted && !open, [mounted, open]);

  async function syncConsent(next: CookieConsent) {
    const payload = persistCookieConsent({
      ...next,
      necessary: true,
      version: COOKIE_CONSENT_VERSION,
      updatedAt: new Date().toISOString(),
    });
    setConsent(payload);
    setOpen(false);
    setShowManager(false);

    const base = getClientApiBase();
    if (!base || typeof window === "undefined") return;
    const body = {
      anonymous_id: getOrCreateVisitorId(),
      consent_version: payload.version,
      source: "cookie_banner",
      page_url: window.location.href,
      categories: {
        necessary: payload.necessary,
        analytics: payload.analytics,
        preferences: payload.preferences,
        marketing: payload.marketing,
      },
    };
    try {
      await fetch(`${base}/api/public/legal/consents/cookies`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        keepalive: true,
      });
    } catch {
      // El consentimiento local no depende del backend.
    }
  }

  if (!mounted) return null;

  return (
    <>
      {open ? (
        <div className="fixed inset-x-0 bottom-0 z-50 p-4 sm:p-6">
          <div className="mx-auto max-w-5xl rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5 shadow-[var(--shadow-xl)]">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div className="max-w-3xl">
                <div className="text-lg font-semibold text-[color:var(--text-primary)]">Preferencias de cookies</div>
                <p className="mt-2 text-sm leading-7 text-[color:var(--text-secondary)]">Usamos cookies necesarias para que WAOS funcione y cookies opcionales para analítica, preferencias y marketing. Puedes aceptar, rechazar las opcionales o personalizar tu elección.</p>
                <div className="mt-3 text-sm text-[color:var(--text-secondary)]">Consulta la <Link href="/legal/cookies-tracking" className="underline">Política de Cookies y Tracking</Link>.</div>
              </div>
              <div className="flex flex-wrap gap-2">
                <button type="button" className="secondary-btn" onClick={() => setShowManager((value) => !value)}>Personalizar</button>
                <button type="button" className="secondary-btn" onClick={() => void syncConsent({ ...defaultCookieConsent() })}>Rechazar opcionales</button>
                <button type="button" className="primary-btn" onClick={() => void syncConsent({ necessary: true, analytics: true, preferences: true, marketing: true, version: COOKIE_CONSENT_VERSION, updatedAt: new Date().toISOString() })}>Aceptar todas</button>
              </div>
            </div>
            {showManager ? (
              <div className="mt-4 grid gap-3 rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4 sm:grid-cols-3">
                <label className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4 text-sm">
                  <div className="font-medium text-[color:var(--text-primary)]">Necesarias</div>
                  <div className="mt-2 leading-6 text-[color:var(--text-secondary)]">Siempre activas para seguridad, sesión y funcionamiento básico.</div>
                </label>
                <label className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4 text-sm">
                  <div className="flex items-center justify-between gap-3"><span className="font-medium text-[color:var(--text-primary)]">Analítica</span><input type="checkbox" checked={consent.analytics} onChange={(e) => setConsent((current) => ({ ...current, analytics: e.target.checked }))} /></div>
                  <div className="mt-2 leading-6 text-[color:var(--text-secondary)]">Mide uso agregado para mejorar rendimiento y experiencia.</div>
                </label>
                <label className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4 text-sm">
                  <div className="flex items-center justify-between gap-3"><span className="font-medium text-[color:var(--text-primary)]">Preferencias</span><input type="checkbox" checked={consent.preferences} onChange={(e) => setConsent((current) => ({ ...current, preferences: e.target.checked }))} /></div>
                  <div className="mt-2 leading-6 text-[color:var(--text-secondary)]">Recuerda elecciones no esenciales del usuario.</div>
                </label>
                <label className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4 text-sm sm:col-span-3">
                  <div className="flex items-center justify-between gap-3"><span className="font-medium text-[color:var(--text-primary)]">Marketing</span><input type="checkbox" checked={consent.marketing} onChange={(e) => setConsent((current) => ({ ...current, marketing: e.target.checked }))} /></div>
                  <div className="mt-2 leading-6 text-[color:var(--text-secondary)]">Permite medir campañas y personalizar comunicaciones cuando exista base legal válida.</div>
                </label>
                <div className="sm:col-span-3">
                  <button type="button" className="primary-btn" onClick={() => void syncConsent(consent)}>Guardar preferencias</button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {canShowFloatingButton ? (
        <button type="button" className="fixed bottom-4 right-4 z-40 rounded-full border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] px-4 py-2 text-sm font-medium text-[color:var(--text-primary)] shadow-[var(--shadow-soft)]" onClick={() => { setOpen(true); setShowManager(true); }}>Cookies</button>
      ) : null}
    </>
  );
}
