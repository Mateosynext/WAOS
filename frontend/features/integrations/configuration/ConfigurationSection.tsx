import Link from "next/link";
import { EmptyActionState } from "@/app/components/feedback";
import { ModuleCard, Section } from "@/app/components/primitives/cards";
import { Badge } from "@/app/components/primitives/shared";
import { safeText } from "@/app/lib/ui";
import {
  saveGoogleCalendarIntegrationAction,
  saveStripeIntegrationAction,
  saveWhatsAppIntegrationAction,
  startGoogleOAuthAction,
  syncIntegrationAction,
  testIntegrationAction,
} from "@/features/integrations/actions";
import type { IntegrationsPageModel } from "@/features/integrations/server/getIntegrationsPageModel";

function isRecommended(model: IntegrationsPageModel, key: string) {
  return (model.selectedVertical?.recommended_integrations || []).some((value) => String(value).toLowerCase().includes(key));
}

export function ConfigurationSection({ model }: { model: IntegrationsPageModel }) {
  const { selectedVertical, whatsappIntegration, googleIntegration, stripeIntegration, googleCalendars, organizationId, currentBotId, focusIntegrationId } = model;
  return (
    <>
      <Section title="Asistente operativo por industria" subtitle={`La industria ${safeText(selectedVertical?.short_name || selectedVertical?.name, "activa")} recomienda priorizar estas conexiones antes de salir a producción.`} icon="route">
        <div className="grid gap-4 md:grid-cols-3">
          {[
            { key: "whatsapp", label: "WhatsApp", ok: Boolean(whatsappIntegration), detail: "Canal principal para conversaciones reales." },
            { key: "calendar", label: "Google Calendar", ok: Boolean(googleIntegration), detail: "Disponibilidad y agenda alineadas al asistente operativo." },
            { key: "payment", label: "Payments", ok: Boolean(stripeIntegration), detail: "Cobro, anticipo y reconciliación." },
          ].map((item) => {
            const recommended = isRecommended(model, item.key);
            return (
              <ModuleCard
                key={item.key}
                title={item.label}
                description={`${recommended ? "Recomendada para esta industria. " : "Opcional para esta industria. "}${item.ok ? "Ya existe una configuración visible." : "Todavía falta cerrarla."} ${item.detail}`}
                icon={item.ok ? "check" : "plug"}
                tone={item.ok ? "green" : recommended ? "gold" : "slate"}
                footer={<span className="mono-pill">{recommended ? "recomendada" : "opcional"}</span>}
              />
            );
          })}
        </div>
      </Section>

      <Section title="Configuración operable" subtitle="Aquí cierras OAuth, calendario, Stripe, auto-sync y retorno de usuario. Ya no dependes de configuración fuera del producto para completar el ciclo." icon="gear">
        {!organizationId ? (
          <EmptyActionState title="Selecciona una organización" description="La configuración de proveedores se guarda por organización o asistente operativo. Primero fija el contexto arriba." primaryAction={<Link href="/organizations" className="primary-btn">Elegir organización</Link>} />
        ) : (
          <div className="grid gap-6 xl:grid-cols-3">
            <div className={`panel-soft p-5 ${focusIntegrationId && whatsappIntegration?.id === focusIntegrationId ? "ring-1 ring-emerald-400/30" : ""}`}>
              <div className="flex items-start justify-between gap-4">
                <div><div className="eyebrow">WhatsApp</div><h3 className="mt-2 text-xl font-semibold text-white">Cloud API operable</h3><p className="mt-2 text-sm leading-6 text-slate-300">Número, phone number ID, WABA, token y verify token para producción.</p></div>
                <Badge tone={whatsappIntegration ? "green" : "slate"}>{whatsappIntegration ? safeText(whatsappIntegration.credential_status || whatsappIntegration.status) : "no creada"}</Badge>
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
                <label className="field-label md:col-span-2">Access token<input className="field-input" name="access_token" placeholder="EAAG..." /></label>
                <label className="field-label">Webhook verify token<input className="field-input" name="webhook_verify_token" defaultValue={String(whatsappIntegration?.config.webhook_verify_token || "")} /></label>
                <label className="field-label">App secret<input className="field-input" name="app_secret" placeholder="meta app secret" /></label>
                <div className="md:col-span-2"><button className="primary-btn" type="submit">Guardar WhatsApp</button></div>
              </form>
              {whatsappIntegration ? <form action={testIntegrationAction} className="mt-3"><input type="hidden" name="integration_id" value={whatsappIntegration.id} /><input type="hidden" name="redirect_to" value="/integrations?section=configuracion" /><button className="secondary-btn" type="submit">Probar</button></form> : null}
              <div className="mt-4 grid gap-2 text-sm text-slate-300"><div className="surface-row">Último provider event: {safeText(whatsappIntegration?.last_provider_event_at || "sin dato")}</div><div className="surface-row">Último error: {safeText(whatsappIntegration?.last_error || "sin error visible")}</div></div>
            </div>

            <div className={`panel-soft p-5 ${focusIntegrationId && googleIntegration?.id === focusIntegrationId ? "ring-1 ring-emerald-400/30" : ""}`}>
              <div className="flex items-start justify-between gap-4"><div><div className="eyebrow">Google Calendar</div><h3 className="mt-2 text-xl font-semibold text-white">OAuth y sincronización</h3><p className="mt-2 text-sm leading-6 text-slate-300">Configura client ID, callback, retorno al frontend y calendario real.</p></div><Badge tone={googleIntegration ? "green" : "slate"}>{googleIntegration ? safeText(googleIntegration.credential_status || googleIntegration.status) : "no creada"}</Badge></div>
              <form action={saveGoogleCalendarIntegrationAction} className="mt-5 grid gap-4 md:grid-cols-2">
                <input type="hidden" name="organization_id" value={organizationId} /><input type="hidden" name="bot_id" value={googleIntegration?.bot_id || currentBotId || ""} /><input type="hidden" name="status" value="configured" /><input type="hidden" name="redirect_to" value="/integrations?section=configuracion" /><input type="hidden" name="frontend_redirect_uri" value={`${process.env.NEXT_PUBLIC_APP_URL || ""}/integrations?section=configuracion`} />
                <label className="field-label">Nombre<input className="field-input" name="name" defaultValue={String(googleIntegration?.name || "Google Calendar")} /></label>
                <label className="field-label">Client ID<input className="field-input" name="client_id" defaultValue={String(googleIntegration?.config.client_id || "")} required /></label>
                <label className="field-label md:col-span-2">Client Secret<input className="field-input" name="client_secret" placeholder="Solo si vas a crear o rotar el secreto" /></label>
                <label className="field-label md:col-span-2">Redirect URI<input className="field-input" name="redirect_uri" defaultValue={String(googleIntegration?.config.redirect_uri || `${process.env.NEXT_PUBLIC_API_BASE_URL || ""}/api/v1/integrations/oauth/google/callback`)} required /></label>
                <label className="field-label">Calendario<select className="field-input" name="calendar_id" defaultValue={String(googleIntegration?.config.calendar_id || "primary")}><option value="primary">primary</option>{googleCalendars.map((item) => { const record = item as Record<string, unknown>; const id = String(record.id || ""); return <option key={id} value={id}>{safeText(String(record.summary || id))}</option>; })}</select></label>
                <label className="field-label">Frecuencia de sync (min)<input className="field-input" name="sync_frequency_minutes" type="number" min="5" defaultValue={String(googleIntegration?.sync_frequency_minutes || googleIntegration?.config.sync_frequency_minutes || 30)} /></label>
                <label className="field-label">Timezone<input className="field-input" name="timezone" defaultValue={String(googleIntegration?.config.timezone || "America/Mexico_City")} /></label>
                <label className="field-label items-start justify-end pt-8"><span className="flex items-center gap-2"><input type="checkbox" name="auto_sync_enabled" defaultChecked={googleIntegration?.auto_sync_enabled ?? (googleIntegration?.config.sync_mode === "auto" || true)} /> Auto-sync habilitado</span></label>
                <div className="md:col-span-2"><button className="primary-btn" type="submit">Guardar configuración</button></div>
              </form>
              <div className="mt-3 flex flex-wrap gap-2">{googleIntegration ? <form action={startGoogleOAuthAction}><input type="hidden" name="integration_id" value={googleIntegration.id} /><button className="secondary-btn" type="submit">Conectar con Google</button></form> : <span className="mono-pill">Guarda primero para iniciar OAuth</span>}{googleIntegration ? <form action={testIntegrationAction}><input type="hidden" name="integration_id" value={googleIntegration.id} /><input type="hidden" name="redirect_to" value="/integrations?section=configuracion" /><button className="secondary-btn" type="submit">Probar</button></form> : null}</div>
              <div className="mt-4 grid gap-2 text-sm text-slate-300"><div className="surface-row">Último sync: {safeText(googleIntegration?.last_success_at || googleIntegration?.next_sync_at || "sin dato")}</div><div className="surface-row">Último error: {safeText(googleIntegration?.last_error || "sin error visible")}</div></div>
            </div>

            <div className={`panel-soft p-5 ${focusIntegrationId && stripeIntegration?.id === focusIntegrationId ? "ring-1 ring-emerald-400/30" : ""}`}>
              <div className="flex items-start justify-between gap-4"><div><div className="eyebrow">Stripe</div><h3 className="mt-2 text-xl font-semibold text-white">Cobro real y reconciliación</h3><p className="mt-2 text-sm leading-6 text-slate-300">Configura URLs reales, secretos, webhook y auto-reconciliación.</p></div><Badge tone={stripeIntegration ? "green" : "slate"}>{stripeIntegration ? safeText(stripeIntegration.credential_status || stripeIntegration.status) : "no creada"}</Badge></div>
              <form action={saveStripeIntegrationAction} className="mt-5 grid gap-4 md:grid-cols-2">
                <input type="hidden" name="organization_id" value={organizationId} /><input type="hidden" name="bot_id" value={stripeIntegration?.bot_id || currentBotId || ""} /><input type="hidden" name="status" value="configured" /><input type="hidden" name="redirect_to" value="/integrations?section=configuracion" />
                <label className="field-label">Nombre<input className="field-input" name="name" defaultValue={String(stripeIntegration?.name || "Stripe Payments")} /></label>
                <label className="field-label">Publishable key<input className="field-input" name="publishable_key" defaultValue={String(stripeIntegration?.config.publishable_key || "")} /></label>
                <label className="field-label md:col-span-2">Secret key<input className="field-input" name="secret_key" placeholder="sk_live_..." /></label>
                <label className="field-label md:col-span-2">Webhook secret<input className="field-input" name="webhook_secret" placeholder="whsec_..." /></label>
                <label className="field-label md:col-span-2">Success URL<input className="field-input" name="success_url" defaultValue={String(stripeIntegration?.config.success_url || `${process.env.NEXT_PUBLIC_APP_URL || ""}/revenue?payment_success=1`)} required /></label>
                <label className="field-label md:col-span-2">Cancel URL<input className="field-input" name="cancel_url" defaultValue={String(stripeIntegration?.config.cancel_url || `${process.env.NEXT_PUBLIC_APP_URL || ""}/revenue?payment_cancelled=1`)} required /></label>
                <label className="field-label md:col-span-2">Webhook URL<input className="field-input" name="webhook_url" defaultValue={String(stripeIntegration?.config.webhook_url || `${process.env.NEXT_PUBLIC_API_BASE_URL || ""}/webhooks/stripe`)} /></label>
                <label className="field-label">Frecuencia de refresh (min)<input className="field-input" name="sync_frequency_minutes" type="number" min="5" defaultValue={String(stripeIntegration?.sync_frequency_minutes || stripeIntegration?.config.sync_frequency_minutes || 10)} /></label>
                <label className="field-label items-start justify-end pt-8"><span className="flex items-center gap-2"><input type="checkbox" name="auto_sync_enabled" defaultChecked={stripeIntegration?.auto_sync_enabled ?? (stripeIntegration?.config.sync_mode === "auto" || true)} /> Auto-reconciliación</span></label>
                <div className="md:col-span-2"><button className="primary-btn" type="submit">Guardar Stripe</button></div>
              </form>
              <div className="mt-3 flex flex-wrap gap-2">{stripeIntegration ? <form action={testIntegrationAction}><input type="hidden" name="integration_id" value={stripeIntegration.id} /><input type="hidden" name="redirect_to" value="/integrations?section=configuracion" /><button className="secondary-btn" type="submit">Probar</button></form> : null}{stripeIntegration ? <form action={syncIntegrationAction}><input type="hidden" name="integration_id" value={stripeIntegration.id} /><input type="hidden" name="redirect_to" value="/integrations?section=configuracion" /><button className="secondary-btn" type="submit">Reconciliar ahora</button></form> : null}</div>
              <div className="mt-4 grid gap-2 text-sm text-slate-300"><div className="surface-row">Último provider event: {safeText(stripeIntegration?.last_provider_event_at || "sin dato")}</div><div className="surface-row">Último HTTP status: {safeText(stripeIntegration?.last_provider_status_code ? String(stripeIntegration.last_provider_status_code) : "sin dato")}</div><div className="surface-row">Último error: {safeText(stripeIntegration?.last_error || "sin error visible")}</div></div>
            </div>
          </div>
        )}
      </Section>
    </>
  );
}
