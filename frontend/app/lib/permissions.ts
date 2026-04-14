export function normalizeRole(role: string | null | undefined) {
  return String(role || "anonymous").toLowerCase();
}

export function canApproveRelease(role: string | null | undefined) {
  return ["super_admin", "admin", "ops_admin", "release_manager"].includes(normalizeRole(role));
}

export function canPublishRelease(role: string | null | undefined) {
  return ["super_admin", "admin", "release_manager"].includes(normalizeRole(role));
}

export function canAccessSecurity(role: string | null | undefined) {
  return ["super_admin", "admin", "security_admin", "ops_admin"].includes(normalizeRole(role));
}

export function canUseSupportMode(role: string | null | undefined) {
  return ["super_admin", "admin", "ops_admin", "support"].includes(normalizeRole(role));
}

export function roleLabel(role: string | null | undefined) {
  const normalized = normalizeRole(role);
  const labels: Record<string, string> = {
    super_admin: "Super admin",
    admin: "Admin",
    ops_admin: "Operacion",
    support: "Soporte",
    security_admin: "Seguridad",
    release_manager: "Releases",
    sales: "Ventas",
    client_success: "Cliente",
    client: "Cliente",
    anonymous: "Sin sesion",
  };
  return labels[normalized] || normalized;
}

export const screenPermissionReview = [
  { screen: "Inbox", action: "Tomar conversaciones y reactivar casos", roles: "super_admin, admin, ops_admin, support, sales" },
  { screen: "Releases", action: "Aprobar cambios antes de publicar", roles: "super_admin, admin, ops_admin, release_manager" },
  { screen: "Releases", action: "Publicar a produccion", roles: "super_admin, admin, release_manager" },
  { screen: "Security", action: "Ver politicas, proveedores y limites", roles: "super_admin, admin, security_admin, ops_admin" },
  { screen: "Support", action: "Inspeccionar sin acceder al panel completo", roles: "super_admin, admin, ops_admin, support" },
  { screen: "Secrets", action: "Crear y listar secretos", roles: "super_admin, admin, security_admin" },
  { screen: "Secrets", action: "Rotar secretos operativos", roles: "super_admin, admin, security_admin" },
  { screen: "Security", action: "Editar politicas y SSO", roles: "super_admin, admin, security_admin" },
  { screen: "Security", action: "Editar rate limits", roles: "super_admin, admin, security_admin, ops_admin" },
  { screen: "Status", action: "Ver observabilidad y salud interna", roles: "super_admin, admin, ops_admin, support, security_admin" },
];

export const sensitiveEvents = [
  "login",
  "mfa_failed",
  "session_refreshed",
  "secret_rotated",
  "release_approved",
  "release_published",
  "bot_paused",
  "bot_reactivated",
];

export function canManageBots(role: string | null | undefined) {
  return ["super_admin", "admin", "ops_admin"].includes(normalizeRole(role));
}

export function canOperateIntegrations(role: string | null | undefined) {
  return ["super_admin", "admin", "ops_admin", "support"].includes(normalizeRole(role));
}

export function canTakeoverConversation(role: string | null | undefined) {
  return ["super_admin", "admin", "ops_admin", "support", "sales", "client_success"].includes(normalizeRole(role));
}

export function canReactivateConversation(role: string | null | undefined) {
  return ["super_admin", "admin", "ops_admin", "support"].includes(normalizeRole(role));
}

export function canReplyConversation(role: string | null | undefined) {
  return ["super_admin", "admin", "ops_admin", "support", "sales", "client_success"].includes(normalizeRole(role));
}


export function canManageSecrets(role: string | null | undefined) {
  return ["super_admin", "admin", "security_admin"].includes(normalizeRole(role));
}

export function canRotateSecrets(role: string | null | undefined) {
  return ["super_admin", "admin", "security_admin"].includes(normalizeRole(role));
}

export function canManageRateLimits(role: string | null | undefined) {
  return ["super_admin", "admin", "security_admin", "ops_admin"].includes(normalizeRole(role));
}

export function canManageSecurityPolicy(role: string | null | undefined) {
  return ["super_admin", "admin", "security_admin"].includes(normalizeRole(role));
}

export function canManageSSOProviders(role: string | null | undefined) {
  return ["super_admin", "admin", "security_admin"].includes(normalizeRole(role));
}

export function canViewObservability(role: string | null | undefined) {
  return ["super_admin", "admin", "ops_admin", "support", "security_admin"].includes(normalizeRole(role));
}


export function isRoleAllowed(role: string | null | undefined, allowed: string[]) {
  return allowed.includes(normalizeRole(role));
}

export function permissionMessage(action: string) {
  return `Tu rol actual no puede ${action.toLowerCase()} desde esta pantalla.`;
}
