"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type CommandItem = {
  href: string;
  label: string;
  description: string;
  keywords?: string[];
};

const ITEMS: CommandItem[] = [
  { href: "/", label: "Inicio", description: "Ver qué falta para salir, qué urge hoy y a dónde entrar después.", keywords: ["home", "dashboard", "inicio"] },
  { href: "/onboarding", label: "Puesta en marcha", description: "Cerrar setup sin brincar entre conceptos técnicos.", keywords: ["setup", "wizard", "bot", "canal", "onboarding"] },
  { href: "/bot-studio", label: "Bot", description: "Crear o alinear un bot desde un solo lugar.", keywords: ["studio", "bot", "crear", "responder"] },
  { href: "/inbox", label: "Inbox", description: "Operar conversaciones con preview, prioridad y acciones rápidas.", keywords: ["chat", "conversaciones", "bandeja"] },
  { href: "/agenda", label: "Agenda", description: "Consultar citas y próximos seguimientos.", keywords: ["calendario", "citas"] },
  { href: "/operations", label: "Operaciones", description: "Revisar soporte, salud y trabajo operativo consolidado.", keywords: ["status", "support", "ops", "operacion"] },
  { href: "/releases", label: "Publicaciones", description: "Revisar readiness y publicar cambios con control.", keywords: ["launch", "release", "deploy", "publicar"] },
  { href: "/business-hub", label: "Comercial", description: "Catálogo, promociones, ingresos e insights en un solo dominio.", keywords: ["catalogo", "promociones", "ventas", "revenue", "commerce"] },
  { href: "/organizations", label: "Organizaciones", description: "Cambiar contexto y fijar la organización activa.", keywords: ["tenant", "contexto", "org"] },
  { href: "/security", label: "Seguridad", description: "Revisar roles, MFA y seguridad operativa.", keywords: ["mfa", "roles", "seguridad"] },
  { href: "/client/resumen", label: "Portal cliente", description: "Abrir la vista compartible para el cliente.", keywords: ["portal", "cliente", "resumen"] },
  { href: "/search", label: "Búsqueda avanzada", description: "Buscar dentro del sistema y saltar rápido a una pantalla.", keywords: ["search", "buscar", "comando"] },
];

export default function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const isShortcut = (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k";
      if (isShortcut) {
        event.preventDefault();
        setOpen((value) => !value);
      }
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return ITEMS;
    return ITEMS.filter((item) => [item.label, item.description, ...(item.keywords || [])].join(" ").toLowerCase().includes(needle));
  }, [query]);

  return (
    <>
      <button type="button" className="secondary-btn" onClick={() => setOpen(true)} aria-haspopup="dialog" aria-expanded={open}>
        Buscar o saltar
        <span className="ml-2 rounded-full border border-[color:var(--border-soft)] px-2 py-0.5 text-[11px] uppercase tracking-[0.16em] text-[color:var(--text-muted)]">Ctrl/⌘ K</span>
      </button>
      {open ? (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-[color:var(--text-inverse)]/55 px-4 py-10 backdrop-blur-sm">
          <div role="dialog" aria-modal="true" className="panel w-full max-w-3xl overflow-hidden">
            <div className="border-b border-[color:var(--border-soft)] p-4">
              <div className="eyebrow">Buscar pantalla</div>
              <div className="mt-2 text-xl font-semibold text-[color:var(--text-primary)]">Encuentra una pantalla sin recorrer todo el menú</div>
              <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">Piensa en intención: vender, responder, publicar, revisar agenda o abrir el portal cliente.</p>
              <input
                autoFocus
                type="search"
                className="field-input mt-4 w-full"
                placeholder="Ej. inbox, promociones, operaciones, cliente…"
                value={query}
                onChange={(event) => setQuery(event.currentTarget.value)}
              />
            </div>
            <div className="border-b border-[color:var(--border-soft)] px-4 py-3 text-xs text-[color:var(--text-muted)]">
              Atajos útiles: inbox, puesta en marcha, comercial, portal cliente, publicaciones.
            </div>
            <div className="max-h-[65vh] overflow-y-auto p-3">
              <div className="space-y-2">
                {filtered.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="block rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] px-4 py-3 transition hover:border-[color:var(--accent-border)] hover:bg-[color:var(--accent-soft)]"
                    onClick={() => setOpen(false)}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-medium text-[color:var(--text-primary)]">{item.label}</div>
                        <div className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{item.description}</div>
                      </div>
                      <span className="mono-pill">{item.href}</span>
                    </div>
                  </Link>
                ))}
                {!filtered.length ? <div className="rounded-2xl border border-dashed border-[color:var(--border-strong)] px-4 py-6 text-sm text-[color:var(--text-secondary)]">No encontramos una pantalla con ese texto. Prueba con inbox, puesta en marcha, operaciones o portal cliente.</div> : null}
              </div>
            </div>
            <div className="border-t border-[color:var(--border-soft)] px-4 py-3 text-xs text-[color:var(--text-muted)]">Tip: también puedes abrir esto con Ctrl/⌘ K y cerrarlo con Escape.</div>
          </div>
        </div>
      ) : null}
    </>
  );
}
