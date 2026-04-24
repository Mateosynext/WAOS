import Link from "next/link";
import { ContextTip, EmptyActionState, SuccessState } from "@/app/components/feedback";
import { Shell } from "@/app/components/layout/shell";
import { SecondaryNav } from "@/app/components/navigation";
import type { IntegrationsPageModel } from "@/features/integrations/server/getIntegrationsPageModel";
import { ConfigurationSection } from "../configuration/ConfigurationSection";
import { CredentialsSection } from "../configuration/CredentialsSection";
import { ObservabilitySection } from "../observability/ObservabilitySection";
import { RiskSection } from "../risk/RiskSection";
import { StatusSection } from "../sync/StatusSection";
import { SyncSection } from "../sync/SyncSection";
import { IntegrationStats } from "./IntegrationStats";

export function IntegrationsShell({ model }: { model: IntegrationsPageModel }) {
  const { section, oauthStatus, integrations, roleLabel } = model;

  return (
    <Shell title="Integraciones" subtitle="Integraciones ya no compite con setup ni publish: aquí solo conectas, pruebas y sincronizas canales, agenda y pagos antes de operar o publicar." action={<Link href="/integrations?section=configuracion" className="primary-btn">Abrir configuración</Link>} requireBot>
      <SecondaryNav items={[
        { href: "/integrations?section=estado", label: "Estado", active: section === "estado" },
        { href: "/integrations?section=configuracion", label: "Configuración", active: section === "configuracion" },
        { href: "/integrations?section=riesgo", label: "Riesgo", active: section === "riesgo" },
        { href: "/integrations?section=sync", label: "Sincronizaciones", active: section === "sync" },
        { href: "/integrations?section=credenciales", label: "Credenciales", active: section === "credenciales" },
        { href: "/integrations?section=observabilidad", label: "Observabilidad", active: section === "observabilidad" },
      ]} />
      <ContextTip>Tu rol visible ahora es {roleLabel}. Bot Studio crea o reconfigura; aquí conectas y pruebas. Releases publica después. Seguridad entra cuando toca revisar rotación, vencimiento o proveedores.</ContextTip>

      {oauthStatus === "connected" ? (
        <SuccessState title="Google Calendar quedó conectado" description="El callback OAuth ya vuelve al producto y la integración quedó lista para elegir calendario, probar y dejar auto-sync si aplica." actions={<Link href="/integrations?section=configuracion" className="primary-btn">Seguir configurando</Link>} />
      ) : null}

      {!integrations.length ? (
        <EmptyActionState title="Todavía no hay integraciones" description="Este módulo solo conecta y prueba. Cierra aquí el canal principal antes de pasar a operación o publicación." primaryAction={<Link href="/integrations?section=configuracion" className="primary-btn">Configurar ahora</Link>} secondaryAction={<Link href="/bot-studio" className="secondary-btn">Volver a Bot Studio</Link>} />
      ) : (
        <SuccessState title="Las integraciones ya tienen una lectura clara" description="Estado, configuración, riesgo, sincronización, credenciales y observabilidad ya viven separados para no mezclar trabajo diario con mantenimiento." actions={<Link href="/integrations?section=observabilidad" className="primary-btn">Ver observabilidad</Link>} />
      )}

      <IntegrationStats model={model} />
      {section === "estado" ? <StatusSection model={model} /> : null}
      {section === "configuracion" ? <ConfigurationSection model={model} /> : null}
      {section === "riesgo" ? <RiskSection model={model} /> : null}
      {section === "sync" ? <SyncSection model={model} /> : null}
      {section === "credenciales" ? <CredentialsSection model={model} /> : null}
      {section === "observabilidad" ? <ObservabilitySection model={model} /> : null}
    </Shell>
  );
}
