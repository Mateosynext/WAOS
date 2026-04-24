import { ContextTip, PermissionGate } from "@/app/components/feedback";
import { Shell } from "@/app/components/layout/shell";
import { SecondaryNav } from "@/app/components/navigation";
import { Section, StatCard } from "@/app/components/primitives/cards";
import { DataTable } from "@/app/components/primitives/data-display";
import { canAccessSecurity, canManageRateLimits, canManageSecurityPolicy, canManageSSOProviders, roleLabel, screenPermissionReview, sensitiveEvents } from "../lib/permissions";
import { requireSession } from "../lib/session";
import { formatNumber, listOrFallback, safeText, yesNo } from "../lib/ui";
import { getAccessMatrix, getRateLimits, getSecurityPolicy, getSSOProviders } from "@/app/lib/data/integrations";

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }
export default async function SecurityPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const view = first(params.view) || "policy";
  const session = await requireSession();
  const role = session?.user.global_role;
  const [policy, providers, matrix, rateLimits] = await Promise.all([getSecurityPolicy(), getSSOProviders(), getAccessMatrix(), getRateLimits()]);
  const providerRows = providers.map((item) => [safeText(item.name || item.provider || "Proveedor"), safeText(item.status || item.health_status || "sin estado"), safeText(item.expires_at || item.updated_at || "-")]);
  const rateRows = rateLimits.map((item) => [safeText(item.scope || item.kind || "scope"), safeText(item.limit || item.max_requests || "-"), safeText(item.window_seconds || item.window || "-")]);
  return (
    <Shell title="Seguridad y acceso" subtitle="Aqui se separan politicas, proveedores y limites con una revision simple de permisos por pantalla y por accion.">
      <SecondaryNav items={[{ href: "/security?view=policy", label: "Politica", active: view === "policy" }, { href: "/security?view=providers", label: "Proveedores", active: view === "providers" }, { href: "/security?view=permissions", label: "Permisos", active: view === "permissions" }, { href: "/security?view=limits", label: "Limites", active: view === "limits" }]} />
      <ContextTip>Tu rol visible ahora es {roleLabel(role)}. Esta pantalla ya usa una capa de permisos en frontend para esconder acciones sensibles cuando no corresponden.</ContextTip>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="MFA" value={yesNo(policy.require_mfa)} hint="Proteccion extra al entrar" icon="shield" tone="green" />
        <StatCard label="SSO" value={yesNo(policy.require_sso)} hint="Inicio centralizado" icon="plug" tone="blue" />
        <StatCard label="TTL sesion" value={safeText(policy.session_ttl_minutes ? `${policy.session_ttl_minutes} min` : null, "-")} hint="Duracion de sesion" icon="clock" tone="gold" />
        <StatCard label="Rate limits" value={formatNumber(rateLimits.length)} hint="Limites configurados" icon="alert" tone="slate" />
      </div>
      <PermissionGate allowed={canAccessSecurity(role)} fallback={<Section title="Acceso restringido" subtitle="Tu rol no deberia modificar o inspeccionar seguridad profunda. Puedes pedir apoyo a un perfil con alcance operativo o de seguridad." icon="shield"><div className="text-sm text-slate-300">Consulta a un perfil con alcance de seguridad para continuar.</div></Section>}>
        {view === "policy" ? <Section title="Politica actual" subtitle="Lo importante de la configuracion de seguridad en lenguaje simple." icon="shield"><DataTable columns={["Tema", "Valor"]} rows={[["MFA obligatorio", yesNo(policy.require_mfa)], ["SSO obligatorio", yesNo(policy.require_sso)], ["Firma de webhook", yesNo(policy.webhook_signature_required)], ["Idempotencia estricta", yesNo(policy.strict_idempotency)], ["IPs permitidas", listOrFallback(policy.ip_allowlist)], ["Origenes permitidos", listOrFallback(policy.allowed_origins)]]} /><div className="mt-4"><PermissionGate allowed={canManageSecurityPolicy(role)} fallback={<span className="mono-pill">Tu rol puede revisar politica pero no editarla.</span>}><span className="mono-pill">Edicion de politica permitida para tu rol</span></PermissionGate></div></Section> : null}
        {view === "providers" ? <Section title="Proveedores e integraciones de acceso" subtitle="Aqui deberia quedar visible cual proveedor existe, en que estado esta y cuando toca revisarlo." icon="plug"><DataTable columns={["Proveedor", "Estado", "Vence o se actualizo"]} rows={providerRows.length ? providerRows : [["Sin proveedores", "-", "-"]]} /><div className="mt-4"><PermissionGate allowed={canManageSSOProviders(role)} fallback={<span className="mono-pill">Tu rol puede inspeccionar proveedores pero no modificarlos.</span>}><span className="mono-pill">Gestion de proveedores habilitada para tu rol</span></PermissionGate></div></Section> : null}
        {view === "permissions" ? <Section title="Revision por pantalla y accion" subtitle="La frontera entre super admin y cliente se vuelve mas clara cuando defines que accion se ve y quien la puede tocar." icon="layers"><DataTable columns={["Pantalla", "Accion", "Roles permitidos"]} rows={screenPermissionReview.map((item) => [item.screen, item.action, item.roles])} /><div className="mt-6"><DataTable columns={["Rol", "Permisos backend visibles"]} rows={Object.entries(matrix.roles || {}).map(([roleName, permissions]) => [roleName, safeText(Array.isArray(permissions) ? permissions.join(", ") : JSON.stringify(permissions))])} /></div></Section> : null}
        {view === "limits" ? <Section title="Limites y eventos sensibles" subtitle="No se trata solo de politica. Tambien importa ver que eventos deben quedar auditados y donde hay rate limiting visible." icon="alert"><DataTable columns={["Scope", "Limite", "Ventana"]} rows={rateRows.length ? rateRows : [["Sin limites visibles", "-", "-"]]} /><div className="mt-4"><PermissionGate allowed={canManageRateLimits(role)} fallback={<span className="mono-pill">Tu rol puede revisar limites pero no cambiarlos.</span>}><span className="mono-pill">Gestion de rate limits habilitada para tu rol</span></PermissionGate></div><div className="mt-6"><DataTable columns={["Evento sensible", "Debe quedar auditado"]} rows={sensitiveEvents.map((item) => [item, "Si"])} /></div></Section> : null}
      </PermissionGate>
    </Shell>
  );
}
