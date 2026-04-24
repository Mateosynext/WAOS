import { PermissionGate } from "@/app/components/feedback";
import ConfirmSubmitButton from "@/app/components/ConfirmSubmitButton";
import { Section } from "@/app/components/primitives/cards";
import { DataTable } from "@/app/components/primitives/data-display";
import { Badge } from "@/app/components/primitives/shared";
import { safeText } from "@/app/lib/ui";
import { syncIntegrationAction, testIntegrationAction } from "@/features/integrations/actions";
import type { IntegrationsPageModel } from "@/features/integrations/server/getIntegrationsPageModel";

export function StatusSection({ model }: { model: IntegrationsPageModel }) {
  const { integrations, permissions } = model;
  return (
    <Section title="Estado de conexiones" subtitle="Una tabla para revisar salud visible y decidir si probar o sincronizar." icon="plug">
      <DataTable columns={["Integración", "Tipo", "Estado", "Salud", "Acciones"]} rows={integrations.map((item) => [
        <div key={item.id}><div className="font-medium text-white">{safeText(item.name)}</div><div className="text-xs text-slate-400">{safeText(item.provider || item.integration_type)}</div></div>,
        safeText(item.integration_type),
        <Badge key={`${item.id}-status`} tone={["active", "connected", "configured"].includes(String(item.status || "").toLowerCase()) ? "green" : "amber"}>{safeText(item.status)}</Badge>,
        <div key={`${item.id}-health`} className="flex flex-wrap gap-2"><Badge tone={["healthy", "connected", "ok"].includes(String(item.health_status || item.status || "").toLowerCase()) ? "green" : String(item.health_status || "").toLowerCase() === "degraded" ? "amber" : "red"}>{safeText(item.health_status || item.status)}</Badge>{item.auto_sync_enabled ? <Badge tone="sky">auto</Badge> : <Badge tone="slate">manual</Badge>}</div>,
        <div key={`${item.id}-actions`} className="flex flex-wrap gap-2">
          <PermissionGate allowed={permissions.canOperateIntegrations} fallback={<span className="mono-pill">Sin permiso operativo</span>}>
            <form action={testIntegrationAction}>
              <input type="hidden" name="integration_id" value={item.id} />
              <input type="hidden" name="redirect_to" value="/integrations?section=estado" />
              <ConfirmSubmitButton message="¿Seguro que quieres probar esta integración ahora?">Probar</ConfirmSubmitButton>
            </form>
            <form action={syncIntegrationAction}>
              <input type="hidden" name="integration_id" value={item.id} />
              <input type="hidden" name="redirect_to" value="/integrations?section=estado" />
              <ConfirmSubmitButton className="primary-btn" message="¿Seguro que quieres sincronizar esta integración ahora?">Sincronizar</ConfirmSubmitButton>
            </form>
          </PermissionGate>
        </div>,
      ])} />
    </Section>
  );
}
