import { UI_GLOSSARY } from "../../lib/ui-glossary";

export const superAdminNavigation = [
  {
    group: "Empezar",
    items: [
      { label: "Inicio", href: "/", icon: "dashboard" as const, exact: true },
      { label: "Onboarding", href: "/onboarding", icon: "route" as const },
      { label: "Bot Studio", href: "/bot-studio", icon: "bot" as const },
      { label: UI_GLOSSARY.organizations, href: "/organizations", icon: "client" as const },
      { label: "Integraciones", href: "/integrations", icon: "plug" as const },
    ],
  },
  {
    group: "Operación diaria",
    items: [
      { label: "Inbox", href: "/inbox", icon: "chat" as const },
      { label: "Agenda", href: "/agenda", icon: "calendar" as const },
      { label: "Operaciones", href: "/operations", icon: "stats" as const },
      { label: "Vacantes", href: "/vacantes", icon: "briefcase" as const },
      { label: "Releases", href: "/releases", icon: "rocket" as const },
    ],
  },
  {
    group: "Comercial y cliente",
    items: [
      { label: "Comercial", href: "/business-hub", icon: "briefcase" as const },
      { label: "Documentos", href: "/business-hub?tab=documentos", icon: "folder" as const },
      { label: "Portal cliente", href: "/client/resumen", icon: "client" as const },
      { label: "Búsqueda", href: "/search", icon: "target" as const },
      { label: "Seguridad", href: "/security", icon: "shield" as const },
    ],
  },
] as const;

export const clientNavigation = [
  { label: "Resumen", href: "/client/resumen", icon: "dashboard" as const },
  { label: "Conversaciones", href: "/client/conversaciones", icon: "chat" as const },
  { label: "Agenda", href: "/client/agenda", icon: "calendar" as const },
  { label: "Promociones", href: "/client/promociones", icon: "promo" as const },
  { label: "Solicitudes", href: "/client/solicitudes", icon: "folder" as const },
  { label: "Salud del asistente operativo", href: "/client/bot", icon: "bot" as const },
  { label: "Operación", href: "/client/operaciones", icon: "tool" as const },
] as const;
