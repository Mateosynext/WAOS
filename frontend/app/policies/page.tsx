import Link from "next/link";
import { DataTable, ModuleCard, Section, Shell, StatCard } from "../components";
import { formatNumber, safeText } from "../lib/ui";
import { getAccessMatrix, getRateLimits } from "../lib/waos";

export default async function PoliciesPage() {
  const [matrix, rateLimits] = await Promise.all([getAccessMatrix(), getRateLimits()]);
  const roles = matrix.roles || {};
  return (
    <Shell title="Políticas y límites" subtitle="Una vista práctica de permisos y límites operativos para que sea fácil revisar quién puede hacer qué.">
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Rol actual" value={safeText(matrix.current_user_role)} hint="Nivel de acceso en esta sesión" icon="shield" tone="blue" />
        <StatCard label="Roles definidos" value={formatNumber(Object.keys(roles).length)} hint="Perfiles configurados" icon="layers" tone="green" />
        <StatCard label="Rate limits" value={formatNumber(rateLimits.length)} hint="Límites activos" icon="clock" tone="gold" />
      </div>
      <Section title="Matriz de acceso" subtitle="Resumen simple para revisar permisos por rol." icon="shield">
        <DataTable columns={["Rol", "Permisos"]} rows={Object.entries(roles).map(([role, permissions]) => [role, safeText(Array.isArray(permissions) ? permissions.join(', ') : JSON.stringify(permissions))])} />
      </Section>

      <Section title="Centro legal integrado" subtitle="La app ya incluye un centro legal público, banner de cookies y un paquete documental versionado a nombre de Josue Mendoza Mateo." icon="folder">
        <div className="grid gap-4 xl:grid-cols-2">
          <ModuleCard
            title="Centro legal público"
            description="Acceso a avisos, términos, MSA, DPA, seguridad, cookies, IA, soporte, pagos y portabilidad con slugs estables para enlazarlos desde producto."
            icon="shield"
            tone="green"
            footer={<Link href="/legal" className="primary-btn">Abrir centro legal</Link>}
          />
          <ModuleCard
            title="Controles y evidencias"
            description="El repositorio también contiene procedimientos internos, matrices, esquemas de consentimientos y plantillas para auditoría y onboarding legal."
            icon="folder"
            tone="blue"
            footer={<Link href="/legal/cookies-tracking" className="secondary-btn">Ver política de cookies</Link>}
          />
        </div>
      </Section>
    </Shell>
  );
}
