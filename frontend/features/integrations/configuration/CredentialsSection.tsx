import Link from "next/link";
import { EmptyActionState, PermissionGate } from "@/app/components/feedback";
import { Section } from "@/app/components/primitives/cards";
import { DataTable } from "@/app/components/primitives/data-display";
import { safeText } from "@/app/lib/ui";
import type { IntegrationsPageModel } from "@/features/integrations/server/getIntegrationsPageModel";

export function CredentialsSection({ model }: { model: IntegrationsPageModel }) {
  const { stats, permissions } = model;
  return (
    <Section title="Credenciales y vencimientos" subtitle="Separa conexión viva de vencimiento operativo. Aquí importa saber qué puede romperse aunque hoy parezca conectado." icon="shield">
      {stats.expiring.length ? <DataTable columns={["Integración", "Estado credencial", "Vence", "Siguiente acción"]} rows={stats.expiring.map((item) => [safeText(item.name), safeText(item.credential_status || item.status), safeText(item.credential_expires_at || item.expires_at || item.updated_at), safeText(item.credential_status === "expired" ? "Rotar o reconectar" : "Monitorear y avisar")])} /> : <EmptyActionState title="No se ven vencimientos visibles" description="Cuando un proveedor exponga expiración o rotación pendiente, aparecerá aquí para soporte, seguridad y mantenimiento." primaryAction={<Link href="/security?view=providers" className="primary-btn">Ver seguridad</Link>} />}
      <div className="mt-4 flex flex-wrap gap-2">
        <PermissionGate allowed={permissions.canManageSecrets} fallback={<span className="mono-pill">La rotación fina de credenciales queda visible solo para seguridad.</span>}>
          <Link href="/secrets" className="secondary-btn">Ver secretos</Link>
        </PermissionGate>
      </div>
    </Section>
  );
}
