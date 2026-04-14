import Link from "next/link";
import {
  refreshPaymentStatusAction,
  saveGoogleCalendarIntegrationAction,
  saveWhatsAppIntegrationAction,
  saveStripeIntegrationAction,
  startGoogleOAuthAction,
  syncIntegrationAction,
  testIntegrationAction,
} from "../actions";
import { Badge, ContextTip, DataTable, EmptyActionState, ModuleCard, PermissionGate, Section, Shell, SecondaryNav, StatCard, SuccessState } from "../components";
import ConfirmSubmitButton from "../components/ConfirmSubmitButton";
import { type IntegrationContract, type IntegrationEventContract, type IntegrationObservabilityContract, type SyncRunContract } from "../lib/contracts";
import { canManageSecrets, canOperateIntegrations, roleLabel } from "../lib/permissions";
import { getCurrentBotId, getSession } from "../lib/session";
import { formatNumber, safeText } from "../lib/ui";
import { getBots, getGoogleCalendars, getIntegrationEvents, getIntegrationObservability, getIntegrationSyncRuns, getIntegrations, getPayments, getVerticalProfile } from "../lib/waos";

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }

export default async function IntegrationsPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const section = first(params.section) || "estado";
  const oauthStatus = first(params.google_oauth);
  const focusIntegrationId = first(params.integration_id) || "";
  const session = await getSession();
  const role = session?.user.global_role;
  const organizationId = session?.organizationId || null;
  const currentBotId = await getCurrentBotId();
  const [bots, integrations, syncRuns, observability, events, payments] = await Promise.all([
    getBots(),
    getIntegrations(),
    getIntegrationSyncRuns(),
    getIntegrationObservability(),
    getIntegrationEvents(),
    getPayments(),
  ]);
  const selectedBot = bots.find((item) => item.id === currentBotId) || bots[0] || null;
  const selectedVertical = await getVerticalProfile(selectedBot?.vertical || session?.user.organizations.find((item) => item.id === organizationId)?.vertical || undefined, selectedBot?.id);
  const whatsappIntegration = integrations.find((item) => item.provider === "meta_cloud_api" || item.integration_type === "whatsapp") || null;
  const googleIntegration = integrations.find((item) => item.provider === "google_calendar") || null;
  const stripeIntegration = integrations.find((item) => item.provider === "stripe") || null;
  const googleCalendars = googleIntegration && ["connected", "configured"].includes(String(googleIntegration.credential_status || "").toLowerCase()) ? await getGoogleCalendars(googleIntegration.id) : [];
  const active = integrations.filter((item: IntegrationContract) => ["active", "connected", "configured"].includes(String(item.status || "").toLowerCase())).length;
  const risk = integrations.filter((item: IntegrationContract) => !["healthy", "connected", "ok"].includes(String(item.health_status || item.status || "").toLowerCase()));
  const expiring = integrations.filter((item: IntegrationContract) => item.expires_at || item.credential_expires_at);
  const observedEvents = Number(observability.totals?.ok || 0) + Number(observability.totals?.warning || 0) + Number(observability.totals?.failed || 0);
  const pendingPayments = payments.filter((item) => ["pending", "pending_provider"].includes(String(item.status || "").toLowerCase()));

  return (
    <Shell title="Integraciones" subtitle="Primero conecta, luego prueba, después sincroniza y solo al final entra a credenciales o mantenimiento. Aquí ya puedes configurar Google Calendar y Stripe como producto operable, no como demo." action={<Link href="/onboarding?step=canal" className="primary-btn">Conectar</Link>}>
      <SecondaryNav items={[
        { href: "/integrations?section=estado", label: "Estado", active: section === "estado" },
        { href: "/integrations?section=configuracion", label: "Configuración", active: section === "configuracion" },
        { href: "/integrations?section=riesgo", label: "Riesgo", active: section === "riesgo" },
        { href: "/integrations?section=sync", label: "Sincronizaciones", active: section === "sync" },
        { href: "/integrations?section=credenciales", label: "Credenciales", active: section === "credenciales" },
        { href: "/integrations?section=observabilidad", label: "Observabilidad", active: section === "observabilidad" },
      ]} />
      <ContextTip>Tu rol visible ahora es {roleLabel(role)}. Operación y soporte pueden probar; seguridad entra cuando toca revisar rotación, vencimiento o proveedores.</ContextTip>

      {oauthStatus === "connected" ? (
        <SuccessState title="Google Calendar quedó conectado" description="El callback OAuth ya vuelve al producto y la integración quedó lista para elegir calendario, probar y dejar auto-sync si aplica." actions={<Link href="/integrations?section=configuracion" className="primary-btn">Seguir configurando</Link>} />
      ) : null}

      {!integrations.length ? (
        <EmptyActionState title="Todavía no hay integraciones" description="Conecta primero el canal principal. Cuando eso quede listo, esta pantalla te servirá para probar, sincronizar y revisar riesgo sin ruido." primaryAction={<Link href="/integrations?section=configuracion" className="primary-btn">Configurar ahora</Link>} secondaryAction={<Link href="/status" className="secondary-btn">Ver estado</Link>} />
      ) : (
        <SuccessState title="Las integraciones ya tienen una lectura clara" description="Estado, configuración, riesgo, sincronización, credenciales y observabilidad ya viven separados para no mezclar trabajo diario con mantenimiento." actions={<Link href="/integrations?section=observabilidad" className="primary-btn">Ver observabilidad</Link>} />
      )}

      <div className="grid gap-4 md:grid-cols-5">
        <StatCard label="Integraciones" value={formatNumber(integrations.length)} hint="Conexiones registradas" icon="plug" tone="blue" />
        <StatCard label="Activas" value={formatNumber(active)} hint="Listas para operar" icon="check" tone="green" />
        <StatCard label="Con alerta" value={formatNumber(risk.length)} hint="Requieren revisión" icon={risk.length ? "alert" : "check"} tone={risk.length ? "gold" : "green"} />
        <StatCard label="Pagos pendientes" value={formatNumber(pendingPayments.length)} hint="Casos que pueden necesitar refresh o webhook" icon="money" tone={pendingPayments.length ? "gold" : "slate"} />
        <StatCard label="Eventos proveedor" value={formatNumber(observedEvents)} hint="Traza reciente por integración" icon="stats" tone="slate" />
      </div>

      {section === "configuracion" ? (
        <Section title="Asistente por vertical" subtitle={`La vertical ${safeText(selectedVertical.short_name || selectedVertical.name, "activa")} recomienda priorizar estas conexiones antes de salir a producción.`} icon="route">
          <div className="grid gap-4 md:grid-cols-3">
            {[
              { key: "whatsapp", label: "WhatsApp", ok: Boolean(whatsappIntegration), detail: "Canal principal para conversaciones reales." },
              { key: "google_calendar", label: "Google Calendar", ok: Boolean(googleIntegration), detail: "Disponibilidad y agenda alineadas al bot." },
              { key: "payments", label: "Payments", ok: Boolean(stripeIntegration), detail: "Cobro, anticipo y reconciliación." },
            ].map((item) => {
              const recommended = selectedVertical.recommended_integrations.some((value) => String(value).toLowerCase().includes(item.key === "payments" ? "payment" : item.key === "google_calendar" ? "calendar" : item.key));
              return (
                <ModuleCard
                  key={item.key}
                  title={item.label}
                  description={`${recommended ? "Recomendada para esta vertical. " : "Opcional para esta vertical. "}${item.ok ? "Ya existe una configuración visible." : "Todavía falta cerrarla."}`}
                  icon={item.ok ? "check" : "plug"}
                  tone={item.ok ? "green" : recommended ? "gold" : "slate"}
                  footer={<span className="mono-pill">{recommended ? "recomendada" : "opcional"}</span>}
                />
              );
            })}
          </div>
        </Section>
      ) : null}

      {section === "estado" ? (
        <Section title="Estado de conexiones" subtitle="Una tabla para revisar salud visible y decidir si probar o sincronizar." icon="plug">
          <DataTable columns={["Integración", "Tipo", "Estado", "Salud", "Acciones"]} rows={integrations.map((item: IntegrationContract) => [
            <div key={item.id}><div className="font-medium text-white">{safeText(item.name)}</div><div className="text-xs text-slate-400">{safeText(item.provider || item.integration_type)}</div></div>,
            safeText(item.integration_type),
            <Badge key={`${item.id}-status`} tone={["active", "connected", "configured"].includes(String(item.status || "").toLowerCase()) ? "green" : "amber"}>{safeText(item.status)}</Badge>,
            <div key={`${item.id}-health`} className="flex flex-wrap gap-2"><Badge tone={["healthy", "connected", "ok"].includes(String(item.health_status || item.status || "").toLowerCase()) ? "green" : String(item.health_status || "").toLowerCase() === "degraded" ? "amber" : "red"}>{safeText(item.health_status || item.status)}</Badge>{item.auto_sync_enabled ? <Badge tone="sky">auto</Badge> : <Badge tone="slate">manual</Badge>}</div>,
            <div key={`${item.id}-actions`} className="flex flex-wrap gap-2">
              <PermissionGate allowed={canOperateIntegrations(role)} fallback={<span className="mono-pill">Sin permiso operativo</span>}>
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
      ) : null}

      {section === "configuracion" ? (
        <Section title="Configuración operable" subtitle="Aquí cierras OAuth, calendario, Stripe, auto-sync y retorno de usuario. Ya no dependes de configuración fuera del producto para completar el ciclo." icon="gear">
          {!organizationId ? (
            <EmptyActionState title="Selecciona una organización" description="La configuración de proveedores se guarda por organización o bot. Primero fija el contexto arriba." primaryAction={<Link href="/organizations" className="primary-btn">Elegir organización</Link>} />
          ) : (
            <div className="grid gap-6 xl:grid-cols-3">
              <div className={`panel-soft p-5 ${focusIntegrationId && whatsappIntegration?.id === focusIntegrationId ? "ring-1 ring-emerald-400/30" : ""}`}>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="eyebrow">WhatsApp</div>
                    <h3 className="mt-2 text-xl font-semibold text-white">Cloud API operable</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-300">Deja aquí número, phone number ID, WABA, token y verify token para que el bot pueda salir a producción sin depender de una carga externa.</p>
                  </div>
                  <div className="flex flex-col gap-2">
                    <Badge tone={whatsappIntegration ? "green" : "slate"}>{whatsappIntegration ? safeText(whatsappIntegration.credential_status || whatsappIntegration.status) : "no creada"}</Badge>
                  </div>
                </div>
                <form action={saveWhatsAppIntegrationAction} className="mt-5 grid gap-4 md:grid-cols-2">
                  <input type="hidden" name="organization_id" value={organizationId} />
                  <input type="hidden" name="bot_id" value={whatsappIntegration?.bot_id || currentBotId || ""} />
                  <input type="hidden" name="status" value="configured" />
                  <input type="hidden" name="redirect_to" value="/integrations?section=configuracion" />
                  <label className="field-label">Nombre<input className="field-input" name="name" defaultValue={String(whatsappIntegration?.name || "WhatsApp Cloud API")} /></label>
                  <label className="field-label">Número<input className="field-input" name="phone_number" defaultValue={String(whatsappIntegration?.config.phone_number || "")} placeholder="+525512345678" /></label>
                  <label className="field-label">Phone number ID<input className="field-input" name="phone_number_id" defaultValue={String(whatsappIntegration?.config.phone_number_id || "")} placeholder="1234567890" /></label>
                  <label className="field-label">WABA ID<input className="field-input" name="waba_id" defaultValue={String(whatsappIntegration?.config.waba_id || "")} placeholder="waba_..." /></label>
                  <label className="field-label md:col-span-2">Access token (opcional si ya está guardado)<input className="field-input" name="access_token" placeholder="EAAG..." /></label>
                  <label className="field-label">Webhook verify token<input className="field-input" name="webhook_verify_token" defaultValue={String(whatsappIntegration?.config.webhook_verify_token || "")} placeholder="verify-token" /></label>
                  <label className="field-label">App secret (opcional)<input className="field-input" name="app_secret" placeholder="meta app secret" /></label>
                  <div className="md:col-span-2 flex flex-wrap gap-2">
                    <button className="primary-btn" type="submit">Guardar WhatsApp</button>
                    {whatsappIntegration ? (
                      <form action={testIntegrationAction}>
                        <input type="hidden" name="integration_id" value={whatsappIntegration.id} />
                        <input type="hidden" name="redirect_to" value="/integrations?section=configuracion" />
                        <button className="secondary-btn" type="submit">Probar</button>
                      </form>
                    ) : null}
                  </div>
                </form>
                <div className="mt-4 grid gap-2 text-sm text-slate-300">
                  <div className="surface-row">Recomendación vertical: {selectedVertical.recommended_integrations.some((value) => String(value).toLowerCase().includes("whatsapp")) ? "sí" : "opcional"}</div>
                  <div className="surface-row">Último provider event: {safeText(whatsappIntegration?.last_provider_event_at || "sin dato")}</div>
                  <div className="surface-row">Último error: {safeText(whatsappIntegration?.last_error || "sin error visible")}</div>
                </div>
              </div>
              <div className={`panel-soft p-5 ${focusIntegrationId && googleIntegration?.id === focusIntegrationId ? "ring-1 ring-emerald-400/30" : ""}`}>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="eyebrow">Google Calendar</div>
                    <h3 className="mt-2 text-xl font-semibold text-white">OAuth y sincronización</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-300">Configura client ID, callback, retorno al frontend y frecuencia de sync. Luego conecta la cuenta y elige calendario real.</p>
                  </div>
                  <div className="flex flex-col gap-2">
                    <Badge tone={googleIntegration ? "green" : "slate"}>{googleIntegration ? safeText(googleIntegration.credential_status || googleIntegration.status) : "no creada"}</Badge>
                    {googleIntegration?.auto_sync_enabled ? <Badge tone="sky">auto cada {safeText(String(googleIntegration.sync_frequency_minutes || 30))}m</Badge> : null}
                  </div>
                </div>
                <form action={saveGoogleCalendarIntegrationAction} className="mt-5 grid gap-4 md:grid-cols-2">
                  <input type="hidden" name="organization_id" value={organizationId} />
                  <input type="hidden" name="bot_id" value={googleIntegration?.bot_id || currentBotId || ""} />
                  <input type="hidden" name="status" value="configured" />
                  <input type="hidden" name="redirect_to" value="/integrations?section=configuracion" />
                  <input type="hidden" name="frontend_redirect_uri" value={`${process.env.NEXT_PUBLIC_APP_URL || ""}/integrations?section=configuracion`} />
                  <label className="field-label">Nombre<input className="field-input" name="name" defaultValue={String(googleIntegration?.name || "Google Calendar")} /></label>
                  <label className="field-label">Client ID<input className="field-input" name="client_id" defaultValue={String(googleIntegration?.config.client_id || "")} placeholder="google-client-id.apps.googleusercontent.com" required /></label>
                  <label className="field-label md:col-span-2">Client Secret (opcional si ya está guardado)<input className="field-input" name="client_secret" placeholder="Solo si vas a crear o rotar el secreto" /></label>
                  <label className="field-label md:col-span-2">Redirect URI<input className="field-input" name="redirect_uri" defaultValue={String(googleIntegration?.config.redirect_uri || `${process.env.NEXT_PUBLIC_API_BASE_URL || ""}/api/v1/integrations/oauth/google/callback`)} required /></label>
                  <label className="field-label">Calendario<select className="field-input" name="calendar_id" defaultValue={String(googleIntegration?.config.calendar_id || "primary")}><option value="primary">primary</option>{googleCalendars.map((item) => { const record = item as Record<string, unknown>; const id = String(record.id || ""); return <option key={id} value={id}>{safeText(String(record.summary || id))}</option>; })}</select></label>
                  <label className="field-label">Frecuencia de sync (min)<input className="field-input" name="sync_frequency_minutes" type="number" min="5" defaultValue={String(googleIntegration?.sync_frequency_minutes || googleIntegration?.config.sync_frequency_minutes || 30)} /></label>
                  <label className="field-label">Timezone<input className="field-input" name="timezone" defaultValue={String(googleIntegration?.config.timezone || "America/Mexico_City")} /></label>
                  <label className="field-label items-start justify-end pt-8"><span className="flex items-center gap-2"><input type="checkbox" name="auto_sync_enabled" defaultChecked={googleIntegration?.auto_sync_enabled ?? (googleIntegration?.config.sync_mode === "auto" || true)} /> Auto-sync habilitado</span></label>
                  <div className="md:col-span-2 flex flex-wrap gap-2">
                    <button className="primary-btn" type="submit">Guardar configuración</button>
                    {googleIntegration ? (
                      <form action={startGoogleOAuthAction}>
                        <input type="hidden" name="integration_id" value={googleIntegration.id} />
                        <button className="secondary-btn" type="submit">Conectar con Google</button>
                      </form>
                    ) : <span className="mono-pill">Guarda primero para iniciar OAuth</span>}
                    {googleIntegration ? (
                      <form action={testIntegrationAction}>
                        <input type="hidden" name="integration_id" value={googleIntegration.id} />
                        <input type="hidden" name="redirect_to" value="/integrations?section=configuracion" />
                        <button className="secondary-btn" type="submit">Probar</button>
                      </form>
                    ) : null}
                  </div>
                </form>
                <div className="mt-4 grid gap-2 text-sm text-slate-300">
                  <div className="surface-row">Último sync: {safeText(googleIntegration?.last_success_at || googleIntegration?.next_sync_at || "sin dato")}</div>
                  <div className="surface-row">Último provider event: {safeText(googleIntegration?.last_provider_event_at || "sin dato")}</div>
                  <div className="surface-row">Último error: {safeText(googleIntegration?.last_error || "sin error visible")}</div>
                </div>
              </div>

              <div className={`panel-soft p-5 ${focusIntegrationId && stripeIntegration?.id === focusIntegrationId ? "ring-1 ring-emerald-400/30" : ""}`}>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="eyebrow">Stripe</div>
                    <h3 className="mt-2 text-xl font-semibold text-white">Cobro real y reconciliación</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-300">Configura URLs reales, secretos, webhook y auto-reconciliación. Luego podrás refrescar pagos pendientes desde producto.</p>
                  </div>
                  <div className="flex flex-col gap-2">
                    <Badge tone={stripeIntegration ? "green" : "slate"}>{stripeIntegration ? safeText(stripeIntegration.credential_status || stripeIntegration.status) : "no creada"}</Badge>
                    {stripeIntegration?.auto_sync_enabled ? <Badge tone="sky">auto cada {safeText(String(stripeIntegration.sync_frequency_minutes || 10))}m</Badge> : null}
                  </div>
                </div>
                <form action={saveStripeIntegrationAction} className="mt-5 grid gap-4 md:grid-cols-2">
                  <input type="hidden" name="organization_id" value={organizationId} />
                  <input type="hidden" name="bot_id" value={stripeIntegration?.bot_id || currentBotId || ""} />
                  <input type="hidden" name="status" value="configured" />
                  <input type="hidden" name="redirect_to" value="/integrations?section=configuracion" />
                  <label className="field-label">Nombre<input className="field-input" name="name" defaultValue={String(stripeIntegration?.name || "Stripe Payments")} /></label>
                  <label className="field-label">Publishable key<input className="field-input" name="publishable_key" defaultValue={String(stripeIntegration?.config.publishable_key || "")} placeholder="pk_live_..." /></label>
                  <label className="field-label md:col-span-2">Secret key (opcional si ya está guardado)<input className="field-input" name="secret_key" placeholder="sk_live_..." /></label>
                  <label className="field-label md:col-span-2">Webhook secret (opcional si ya está guardado)<input className="field-input" name="webhook_secret" placeholder="whsec_..." /></label>
                  <label className="field-label md:col-span-2">Success URL<input className="field-input" name="success_url" defaultValue={String(stripeIntegration?.config.success_url || `${process.env.NEXT_PUBLIC_APP_URL || ""}/revenue?payment_success=1`)} required /></label>
                  <label className="field-label md:col-span-2">Cancel URL<input className="field-input" name="cancel_url" defaultValue={String(stripeIntegration?.config.cancel_url || `${process.env.NEXT_PUBLIC_APP_URL || ""}/revenue?payment_cancelled=1`)} required /></label>
                  <label className="field-label md:col-span-2">Webhook URL<input className="field-input" name="webhook_url" defaultValue={String(stripeIntegration?.config.webhook_url || `${process.env.NEXT_PUBLIC_API_BASE_URL || ""}/webhooks/stripe`)} placeholder="https://api.tuapp.com/webhooks/stripe" /></label>
                  <label className="field-label">Frecuencia de refresh (min)<input className="field-input" name="sync_frequency_minutes" type="number" min="5" defaultValue={String(stripeIntegration?.sync_frequency_minutes || stripeIntegration?.config.sync_frequency_minutes || 10)} /></label>
                  <label className="field-label items-start justify-end pt-8"><span className="flex items-center gap-2"><input type="checkbox" name="auto_sync_enabled" defaultChecked={stripeIntegration?.auto_sync_enabled ?? (stripeIntegration?.config.sync_mode === "auto" || true)} /> Auto-reconciliación</span></label>
                  <div className="md:col-span-2 flex flex-wrap gap-2">
                    <button className="primary-btn" type="submit">Guardar Stripe</button>
                    {stripeIntegration ? (
                      <form action={testIntegrationAction}>
                        <input type="hidden" name="integration_id" value={stripeIntegration.id} />
                        <input type="hidden" name="redirect_to" value="/integrations?section=configuracion" />
                        <button className="secondary-btn" type="submit">Probar</button>
                      </form>
                    ) : null}
                    {stripeIntegration ? (
                      <form action={syncIntegrationAction}>
                        <input type="hidden" name="integration_id" value={stripeIntegration.id} />
                        <input type="hidden" name="redirect_to" value="/integrations?section=configuracion" />
                        <button className="secondary-btn" type="submit">Reconciliar ahora</button>
                      </form>
                    ) : null}
                  </div>
                </form>
                <div className="mt-4 grid gap-2 text-sm text-slate-300">
                  <div className="surface-row">Último provider event: {safeText(stripeIntegration?.last_provider_event_at || "sin dato")}</div>
                  <div className="surface-row">Último HTTP status: {safeText(stripeIntegration?.last_provider_status_code ? String(stripeIntegration.last_provider_status_code) : "sin dato")}</div>
                  <div className="surface-row">Último error: {safeText(stripeIntegration?.last_error || "sin error visible")}</div>
                </div>
              </div>
            </div>
          )}
        </Section>
      ) : null}

      {section === "riesgo" ? (
        <Section title="Integraciones con riesgo" subtitle="Solo aparecen las conexiones que pueden frenar operación, reporting, agenda o cobros." icon="alert">
          {risk.length ? <DataTable columns={["Integración", "Proveedor", "Salud", "Detalle"]} rows={risk.map((item: IntegrationContract) => [safeText(item.name), safeText(item.provider), safeText(item.health_status || item.status), safeText(item.last_error || item.credential_status || item.status)])} /> : <EmptyActionState title="No hay integraciones con riesgo visible" description="Buen signo: por ahora la salud visible no muestra conexiones degradadas o cortadas." primaryAction={<Link href="/status" className="primary-btn">Ver estado</Link>} />}
        </Section>
      ) : null}

      {section === "sync" ? (
        <Section title="Últimas sincronizaciones" subtitle="Aquí ves si la integración corre, falla o se queda a medias sin entrar a logs densos." icon="refresh">
          {syncRuns.length ? <DataTable columns={["Run", "Integración", "Estado", "Resumen"]} rows={syncRuns.map((item: SyncRunContract) => [safeText(item.id), safeText(item.integration_id || item.provider), <Badge key={`${item.id}-sync`} tone={String(item.status).toLowerCase() === "completed" ? "green" : String(item.status).toLowerCase() === "running" ? "sky" : "red"}>{safeText(item.status)}</Badge>, safeText(item.detail || JSON.stringify(item.summary || {}))])} /> : <EmptyActionState title="Todavía no hay sincronizaciones visibles" description="Cuando ejecutes pruebas o sincronizaciones manuales, el historial aparecerá aquí para soporte y operación." primaryAction={<Link href="/integrations?section=estado" className="primary-btn">Probar</Link>} />}
          {pendingPayments.length ? (
            <div className="mt-5">
              <div className="eyebrow mb-3">Pagos que conviene refrescar</div>
              <DataTable columns={["Pago", "Estado", "Proveedor", "Acción"]} rows={pendingPayments.slice(0, 10).map((item) => [safeText(item.reference || item.id), safeText(item.status), safeText(item.provider_status || item.provider || item.checkout_status), <form key={item.id} action={refreshPaymentStatusAction}><input type="hidden" name="payment_id" value={item.id} /><input type="hidden" name="redirect_to" value="/integrations?section=sync" /><button className="secondary-btn" type="submit">Refrescar</button></form>])} />
            </div>
          ) : null}
        </Section>
      ) : null}

      {section === "credenciales" ? (
        <Section title="Credenciales y vencimientos" subtitle="Separa conexión viva de vencimiento operativo. Aquí importa saber qué puede romperse aunque hoy parezca conectado." icon="shield">
          {expiring.length ? <DataTable columns={["Integración", "Estado credencial", "Vence", "Siguiente acción"]} rows={expiring.map((item: IntegrationContract) => [safeText(item.name), safeText(item.credential_status || item.status), safeText(item.credential_expires_at || item.expires_at || item.updated_at), safeText(item.credential_status === "expired" ? "Rotar o reconectar" : "Monitorear y avisar")])} /> : <EmptyActionState title="No se ven vencimientos visibles" description="Cuando un proveedor exponga expiración o rotación pendiente, aparecerá aquí para soporte, seguridad y mantenimiento." primaryAction={<Link href="/security?view=providers" className="primary-btn">Ver seguridad</Link>} />}
          <div className="mt-4 flex flex-wrap gap-2">
            <PermissionGate allowed={canManageSecrets(role)} fallback={<span className="mono-pill">La rotación fina de credenciales queda visible solo para seguridad.</span>}>
              <Link href="/secrets" className="secondary-btn">Ver secretos</Link>
            </PermissionGate>
          </div>
        </Section>
      ) : null}

      {section === "observabilidad" ? (
        <Section title="Observabilidad por integración" subtitle="Aquí ya se ve el provider de verdad: eventos recientes, errores y último código HTTP reportado por proveedor." icon="stats">
          <div className="grid gap-4 md:grid-cols-3 mb-4">
            <StatCard label="OK" value={formatNumber(Number(observability.totals?.ok || 0))} hint="Eventos saludables" icon="check" tone="green" />
            <StatCard label="Warnings" value={formatNumber(Number(observability.totals?.warning || 0))} hint="Estados degradados o expirados" icon="alert" tone="gold" />
            <StatCard label="Fallos" value={formatNumber(Number(observability.totals?.failed || 0))} hint="Eventos con error visible" icon="alert" tone="red" />
          </div>
          {events.length ? <DataTable columns={["Proveedor", "Evento", "Estado", "Detalle"]} rows={events.slice(0, 20).map((item: IntegrationEventContract) => [safeText(item.provider), safeText(item.event_type), <Badge key={`${item.id}-evt`} tone={String(item.status || "").toLowerCase() === "ok" || String(item.status || "").toLowerCase() === "paid" ? "green" : String(item.status || "").toLowerCase() === "warning" ? "amber" : "red"}>{safeText(item.status)}</Badge>, safeText(item.detail || item.summary)])} /> : <EmptyActionState title="Todavía no hay eventos de proveedor" description="Cuando empiecen pruebas reales, OAuth, syncs o webhooks, aquí quedará la traza operativa sin ir a logs crudos." primaryAction={<Link href="/integrations?section=estado" className="primary-btn">Probar</Link>} />}
        </Section>
      ) : null}
    </Shell>
  );
}
