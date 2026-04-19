import Link from "next/link";
import { Badge, ContextTip, DataTable, EmptyActionState, ModuleCard, Section, Shell, StatCard, TimelineList } from "../components";
import { formatDateTime, formatNumber, humanizeToken, safeText } from "../lib/ui";
import { getHealth, getIntegrations, getObservability, getQueue, getSystemStatus } from "../lib/waos";

function asArray(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.filter((item) => item && typeof item === "object") as Array<Record<string, unknown>> : [];
}

export default async function StatusPage() {
  const [health, systemStatus, observability, integrations, queue] = await Promise.all([
    getHealth(),
    getSystemStatus(),
    getObservability(),
    getIntegrations(),
    getQueue(),
  ]);

  const checks = asArray((systemStatus as Record<string, unknown>).checks);
  const launchChecks = asArray((systemStatus as Record<string, unknown>).launch_checks);
  const configEntries = Object.entries(((systemStatus as Record<string, unknown>).config as Record<string, unknown>) || {});
  const recentFailures = observability.recent_failures || [];
  const recentLogs = observability.recent_logs || [];
  const degradedIntegrations = integrations.filter((item) => !["active", "configured", "connected", "healthy"].includes(String(item.health_status || item.status || "").toLowerCase()));
  const queueCount = (queue.automation_jobs || []).reduce((total, item) => total + Number(item.count || 0), 0);
  const failingChecks = checks.filter((item) => !Boolean(item.ok ?? item.healthy ?? item.passed));

  return (
    <Shell
      title="Estado interno"
      subtitle="Salud del sistema, señal operativa y checks de salida en una sola vista. Esta pantalla existe para decidir rápido si el problema es de producto, runtime o integración."
      action={<Link href="/operations?view=observability" className="secondary-btn">Abrir operaciones</Link>}
    >
      <ContextTip title="Lectura recomendada">
        Empieza por salud global, luego revisa checks fallando, fallos recientes e integraciones degradadas. Así reduces el tiempo entre detectar ruido y abrir la pantalla correcta.
      </ContextTip>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Salud global" value={humanizeToken((health as Record<string, unknown>).status, "Sin dato")} hint={`Servicio ${safeText((health as Record<string, unknown>).service, "WAOS")}`} icon="check" tone={String((health as Record<string, unknown>).status || "").toLowerCase() === "ok" ? "green" : "gold"} />
        <StatCard label="Checks fallando" value={formatNumber(failingChecks.length)} hint="Validaciones de sistema o release con señal negativa" icon="alert" tone={failingChecks.length ? "red" : "green"} />
        <StatCard label="Integraciones con alerta" value={formatNumber(degradedIntegrations.length)} hint="Conexiones que requieren revisión operativa" icon="plug" tone={degradedIntegrations.length ? "gold" : "blue"} />
        <StatCard label="Jobs en cola" value={formatNumber(queueCount)} hint="Trabajo pendiente en runtime" icon="layers" tone="slate" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <Section title="Salud de plataforma" subtitle="Versión, entorno y checks de backend visibles para operación diaria." icon="shield">
          <DataTable
            columns={["Tema", "Valor"]}
            rows={[
              ["Servicio", safeText((health as Record<string, unknown>).service, "WAOS")],
              ["Estado", <Badge key="health-status" tone={String((health as Record<string, unknown>).status || "").toLowerCase() === "ok" ? "green" : "gold"}>{humanizeToken((health as Record<string, unknown>).status, "Sin dato")}</Badge>],
              ["Versión", safeText((health as Record<string, unknown>).version || (systemStatus as Record<string, unknown>).version, "-")],
              ["Entorno", safeText((health as Record<string, unknown>).environment || (systemStatus as Record<string, unknown>).environment, "-")],
            ]}
          />
        </Section>

        <Section title="Dónde mirar primero" subtitle="La primera decisión para enrutar el incidente correcto." icon="target">
          <div className="grid gap-4 sm:grid-cols-2">
            <ModuleCard title="Runtime y colas" description="Si hay atraso, callbacks o jobs acumulados, entra a scheduler u operations/runtime." icon="refresh" tone={queueCount ? "gold" : "blue"} footer={<Link href="/scheduler" className="secondary-btn">Ver scheduler</Link>} />
            <ModuleCard title="Integraciones" description="Si el ruido viene de credenciales, sincronización o expiación, entra a integraciones." icon="plug" tone={degradedIntegrations.length ? "red" : "green"} footer={<Link href="/integrations" className="secondary-btn">Ver integraciones</Link>} />
            <ModuleCard title="Auditoría" description="Si el problema implica cambios sensibles o revisión de acciones, entra a audit." icon="logs" tone="slate" footer={<Link href="/audit" className="secondary-btn">Ver audit</Link>} />
            <ModuleCard title="Soporte" description="Si el impacto ya llegó a conversaciones o takeover humano, entra a soporte." icon="support" tone="gold" footer={<Link href="/support" className="secondary-btn">Ver soporte</Link>} />
          </div>
        </Section>
      </div>

      <Section title="Checks activos" subtitle="Checks de sistema y launch checks visibles sin brincar a otra vista." icon="check">
        {checks.length || launchChecks.length ? (
          <DataTable
            columns={["Check", "Resultado", "Detalle", "Última señal"]}
            rows={[...checks, ...launchChecks].slice(0, 16).map((item, index) => {
              const ok = Boolean(item.ok ?? item.healthy ?? item.passed);
              const name = safeText(item.name || item.key || item.id || `check-${index}`);
              const detail = safeText(item.detail || item.message || item.description, "Sin detalle adicional");
              const seenAt = safeText(item.updated_at || item.checked_at || item.last_seen_at, "Sin fecha");
              return [
                name,
                <Badge key={`${name}-badge`} tone={ok ? "green" : "red"}>{ok ? "OK" : "Revisar"}</Badge>,
                detail,
                formatDateTime(seenAt),
              ];
            })}
          />
        ) : (
          <EmptyActionState title="No llegaron checks desde backend" description="La vista ya está lista, pero esta organización todavía no expone checks o el backend devolvió vacío." primaryAction={<Link href="/operations?view=observability" className="primary-btn">Abrir observabilidad</Link>} />
        )}
      </Section>

      <div className="grid gap-6 xl:grid-cols-2">
        <Section title="Señal reciente" subtitle="Fallos y eventos recientes para decidir si el problema ya está vivo o fue puntual." icon="alert">
          {recentFailures.length || recentLogs.length ? (
            <TimelineList
              items={[...recentFailures.slice(0, 4).map((item) => ({ title: safeText(item.kind || item.type || item.id, "Fallo reciente"), detail: `${safeText(item.message || item.detail, "Sin detalle")} · ${formatDateTime(safeText(item.created_at || item.updated_at, ""))}`, tone: "red" as const })),
                ...recentLogs.slice(0, 4).map((item) => ({ title: safeText(item.source || item.kind || item.id, "Log reciente"), detail: `${safeText(item.message || item.detail, "Sin detalle")} · ${formatDateTime(safeText(item.created_at || item.updated_at, ""))}`, tone: "slate" as const }))]}
            />
          ) : (
            <EmptyActionState title="Sin ruido reciente" description="No se recibieron fallos ni eventos recientes en esta respuesta de backend." />
          )}
        </Section>

        <Section title="Configuración expuesta" subtitle="Variables o banderas visibles desde el backend para entender el modo actual de la plataforma." icon="gear">
          {configEntries.length ? (
            <DataTable
              columns={["Clave", "Valor"]}
              rows={configEntries.slice(0, 12).map(([key, value]) => [humanizeToken(key), typeof value === "boolean" ? (value ? "Sí" : "No") : safeText(value, "-")])}
            />
          ) : (
            <EmptyActionState title="Sin configuración visible" description="El endpoint no expuso flags o configuración pública en esta organización." />
          )}
        </Section>
      </div>

      <Section title="Integraciones degradadas" subtitle="La lista corta que conviene revisar antes de concluir que el problema es del bot o del inbox." icon="plug">
        {degradedIntegrations.length ? (
          <DataTable
            columns={["Integración", "Proveedor", "Estado", "Detalle"]}
            rows={degradedIntegrations.slice(0, 12).map((item) => [
              safeText(item.name),
              safeText(item.provider || item.integration_type),
              <Badge key={`${item.id}-status`} tone="gold">{safeText(item.health_status || item.status)}</Badge>,
              safeText(item.last_error || item.updated_at || item.id),
            ])}
          />
        ) : (
          <EmptyActionState title="No se ven integraciones degradadas" description="En esta organización no aparecieron integraciones con health o estado de alerta." secondaryAction={<Link href="/integrations" className="secondary-btn">Abrir integraciones</Link>} />
        )}
      </Section>
    </Shell>
  );
}
