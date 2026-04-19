export const UI_GLOSSARY = {
  organization: "Organización",
  organizations: "Organizaciones",
  industry: "Industria",
  operationType: "Tipo de operación",
  operationalAssistant: "Asistente operativo",
  operationalAssistants: "Asistentes operativos",
} as const;

export function industryWithValue(value?: string | null, fallback = "Sin industria activa") {
  const normalized = String(value || "").trim();
  return normalized ? `${UI_GLOSSARY.industry} · ${normalized}` : fallback;
}

export function operationTypeWithValue(value?: string | null, fallback = "Sin tipo de operación activo") {
  const normalized = String(value || "").trim();
  return normalized ? `${UI_GLOSSARY.operationType} · ${normalized}` : fallback;
}

export function organizationWithValue(value?: string | null, fallback = "Organización pendiente") {
  const normalized = String(value || "").trim();
  return normalized ? `${UI_GLOSSARY.organization} · ${normalized}` : fallback;
}

export function operationalAssistantWithValue(value?: string | null, fallback = "Asistente operativo pendiente") {
  const normalized = String(value || "").trim();
  return normalized ? `${UI_GLOSSARY.operationalAssistant} · ${normalized}` : fallback;
}
