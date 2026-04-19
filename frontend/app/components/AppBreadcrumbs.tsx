"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const labelMap: Record<string, string> = {
  login: "Acceso",
  recovery: "Recuperar acceso",
  organizations: "Organizaciones",
  onboarding: "Puesta en marcha",
  inbox: "Inbox",
  bots: "Bots",
  "bot-studio": "Bot",
  integrations: "Canales",
  releases: "Publicaciones",
  "launch-center": "Publicaciones",
  "business-hub": "Comercial",
  catalog: "Catálogo",
  promotions: "Promociones",
  "commerce-insights": "Insights comerciales",
  revenue: "Ingresos",
  status: "Operaciones",
  operations: "Operaciones",
  support: "Soporte",
  observability: "Estado interno",
  security: "Seguridad",
  scheduler: "Automatizaciones",
  agenda: "Agenda",
  client: "Portal cliente",
  resumen: "Resumen",
  conversaciones: "Conversaciones",
  solicitudes: "Solicitudes",
  promociones: "Promociones",
  bot: "Salud del bot",
};

function prettifySegment(segment: string) {
  if (labelMap[segment]) return labelMap[segment];
  const cleaned = decodeURIComponent(segment).replace(/[-_]/g, " ").trim();
  if (!cleaned) return "Detalle";
  if (cleaned.length > 22) return `${cleaned.slice(0, 22)}…`;
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

export default function AppBreadcrumbs() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);
  const crumbs = segments.map((segment, index) => ({
    href: `/${segments.slice(0, index + 1).join("/")}`,
    label: prettifySegment(segment),
  }));

  return (
    <nav aria-label="Breadcrumb" className="flex flex-wrap items-center gap-2 text-xs text-[color:var(--text-muted)]">
      <Link href="/" className="transition hover:text-[color:var(--text-primary)]">Inicio</Link>
      {crumbs.map((crumb, index) => (
        <span key={`${crumb.href}-${index}`} className="inline-flex items-center gap-2">
          <span className="text-[color:var(--border-strong)]">/</span>
          {index === crumbs.length - 1 ? (
            <span className="font-medium text-[color:var(--text-primary)]">{crumb.label}</span>
          ) : (
            <Link href={crumb.href} className="transition hover:text-[color:var(--text-primary)]">{crumb.label}</Link>
          )}
        </span>
      ))}
    </nav>
  );
}
