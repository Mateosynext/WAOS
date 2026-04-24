import Link from "next/link";
import { confirmTalentCandidateAction, createTalentVacancyAction, updateTalentPolicyAction } from "@/app/actions/talent";
import BotScopeSwitcher from "../components/BotScopeSwitcher";
import { EmptyActionState } from "@/app/components/feedback";
import { Shell } from "@/app/components/layout/shell";
import { Section, StatCard } from "@/app/components/primitives/cards";
import { DataTable } from "@/app/components/primitives/data-display";
import { getCurrentBotId } from "../lib/session";
import { formatNumber, safeText, yesNo } from "../lib/ui";
import { getBots, getTalentOverview } from "@/app/lib/data/bots";

function summaryNumber(value: unknown) {
  const n = Number(value || 0);
  return Number.isFinite(n) ? n : 0;
}

export default async function VacantesPage() {
  const [bots, selectedBotId] = await Promise.all([getBots(), getCurrentBotId()]);
  const selectedBot = bots.find((item) => item.id === selectedBotId) || null;

  if (!selectedBot) {
    return (
      <Shell title="Vacantes" subtitle="Primero necesitas un bot seleccionado para operar vacantes, entrevistas y reconocimiento de trabajadores.">
        <EmptyActionState title="No hay bot seleccionado" description="Selecciona un bot para que este módulo quede amarrado al alcance correcto. Aquí las vacantes viven por bot, no por organización." primaryAction={<Link href="/bots" className="primary-btn">Elegir bot</Link>} />
      </Shell>
    );
  }

  const overview = await getTalentOverview(selectedBot.id);
  const config = overview.config || {};
  const workerConfig = (config.worker_recognition as Record<string, unknown> | undefined) || {};
  const interviewPolicy = (config.interview_policy as Record<string, unknown> | undefined) || {};
  const salaryPolicy = (config.salary_policy as Record<string, unknown> | undefined) || {};

  return (
    <Shell
      title="Vacantes"
      subtitle="Módulo de talento por bot: vacantes, entrevistas, candidatos y reconocimiento de trabajadores bajo la regla de nunca quedarse callado."
      action={<BotScopeSwitcher bots={bots} selectedBotId={selectedBot.id} redirectTo="/vacantes" />}
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Bot activo" value={safeText(selectedBot.name)} hint="Contexto operativo" icon="bot" tone="blue" />
        <StatCard label="Vacantes activas" value={formatNumber(summaryNumber(overview.summary.active_vacancies))} hint="Publicadas en este bot" icon="briefcase" tone="green" />
        <StatCard label="Sin horario de entrevista" value={formatNumber(summaryNumber(overview.summary.vacancies_without_interview_schedule))} hint="Vacantes que usarán fallback" icon="clock" tone="gold" />
        <StatCard label="Candidatos confirmados" value={formatNumber(summaryNumber(overview.summary.confirmed_candidates))} hint="Registrados tras confirmar entrevista" icon="check" tone="slate" />
      </div>

      <Section title="Política del módulo" subtitle="Aquí cierras las reglas madre del bot para vacantes, entrevistas y trabajadores." icon="shield">
        <form action={updateTalentPolicyAction} className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <input type="hidden" name="bot_id" value={selectedBot.id} />
          <input type="hidden" name="redirect_to" value="/vacantes" />
          <label className="field-label flex items-center gap-3"><input type="checkbox" name="enabled" defaultChecked={Boolean(config.enabled)} /><span>Módulo talento activo</span></label>
          <label className="field-label flex items-center gap-3"><input type="checkbox" name="vacancies_enabled" defaultChecked={Boolean(config.vacancies_enabled)} /><span>Vacantes activas</span></label>
          <label className="field-label flex items-center gap-3"><input type="checkbox" name="worker_recognition_enabled" defaultChecked={Boolean(config.worker_recognition_enabled)} /><span>Reconocer trabajadores</span></label>
          <label className="field-label flex items-center gap-3"><input type="checkbox" name="never_silent" defaultChecked={Boolean(config.never_silent ?? true)} /><span>Never silent</span></label>
          <label className="field-label flex items-center gap-3"><input type="checkbox" name="default_handoff_on_unknown" defaultChecked={Boolean(config.default_handoff_on_unknown)} /><span>Escalar dudas desconocidas</span></label>
          <label className="field-label flex items-center gap-3"><input type="checkbox" name="route_worker_to_human" defaultChecked={Boolean(workerConfig.route_worker_to_human ?? true)} /><span>Mandar trabajadores a humano</span></label>
          <label className="field-label md:col-span-2 xl:col-span-3">Mensaje sin horario de entrevista
            <textarea className="field-input min-h-24" name="no_schedule_message" defaultValue={safeText(interviewPolicy.no_schedule_message, "Por ahora no cuento con horarios definidos para entrevista. En cuanto estén disponibles te lo confirmaremos.")} />
          </label>
          <label className="field-label md:col-span-2 xl:col-span-3">Mensaje cuando el sueldo no es visible
            <textarea className="field-input min-h-20" name="salary_hide_message" defaultValue={safeText(salaryPolicy.hide_message, "El sueldo se comparte durante el proceso de selección.")} />
          </label>
          <label className="field-label md:col-span-2 xl:col-span-3">Keywords para reconocer trabajadores
            <textarea className="field-input min-h-24" name="worker_keywords" defaultValue={Array.isArray(workerConfig.keywords) ? workerConfig.keywords.join("\n") : "soy empleado\nmi turno\nRH\nnomina"} />
          </label>
          <label className="field-label md:col-span-2 xl:col-span-3">Respuesta para trabajadores
            <textarea className="field-input min-h-20" name="worker_fallback_message" defaultValue={safeText(workerConfig.worker_fallback_message, "Gracias por escribir. Ya detecté que hablas como parte del equipo. Te ayudaremos a canalizar esto con RH o con la persona responsable.")} />
          </label>
          <div className="md:col-span-2 xl:col-span-3"><button className="primary-btn" type="submit">Guardar política</button></div>
        </form>
      </Section>

      <Section title="Crear vacante" subtitle="Alta rápida para dejar al bot listo para responder qué trata la vacante, dónde es y cómo se entrevista." icon="briefcase">
        <form action={createTalentVacancyAction} className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <input type="hidden" name="bot_id" value={selectedBot.id} />
          <input type="hidden" name="redirect_to" value="/vacantes" />
          <label className="field-label">Título<input className="field-input" name="title" placeholder="Ej. Cajero de sucursal" required /></label>
          <label className="field-label">Estado<select className="field-input" name="status" defaultValue="active"><option value="draft">Draft</option><option value="active">Activa</option><option value="paused">Pausada</option><option value="closed">Cerrada</option></select></label>
          <label className="field-label">Modalidad<select className="field-input" name="modality" defaultValue="presencial"><option value="presencial">Presencial</option><option value="remota">Remota</option><option value="hibrida">Híbrida</option></select></label>
          <label className="field-label md:col-span-2 xl:col-span-3">Resumen<input className="field-input" name="summary" placeholder="Ej. Atención a clientes y corte de caja." /></label>
          <label className="field-label md:col-span-2 xl:col-span-3">Descripción<textarea className="field-input min-h-20" name="description" placeholder="Explica de qué trata la vacante." /></label>
          <label className="field-label">Ubicación<input className="field-input" name="location_label" placeholder="Ej. Plaza Centro" /></label>
          <label className="field-label">Dirección<input className="field-input" name="address" placeholder="Ej. Av. Reforma 123" /></label>
          <label className="field-label">Horario laboral<input className="field-input" name="work_hours" placeholder="Ej. 9:00 a 18:00" /></label>
          <label className="field-label">Días<input className="field-input" name="work_days" placeholder="Ej. Lun a Vie" /></label>
          <label className="field-label flex items-center gap-3"><input type="checkbox" name="salary_visible" defaultChecked /><span>Mostrar sueldo</span></label>
          <label className="field-label">Sueldo mínimo<input className="field-input" name="salary_min" type="number" placeholder="8000" /></label>
          <label className="field-label">Sueldo máximo<input className="field-input" name="salary_max" type="number" placeholder="12000" /></label>
          <label className="field-label">Moneda<input className="field-input" name="currency" defaultValue="MXN" /></label>
          <label className="field-label md:col-span-2 xl:col-span-3">Requisitos<textarea className="field-input min-h-20" name="requirements" placeholder="Secundaria terminada\nExperiencia en atención a clientes" /></label>
          <label className="field-label md:col-span-2 xl:col-span-3">Beneficios<textarea className="field-input min-h-20" name="benefits" placeholder="Prestaciones de ley\nBonos por desempeño" /></label>
          <label className="field-label flex items-center gap-3"><input type="checkbox" name="interview_slots_enabled" /><span>La entrevista ya tiene horario definido</span></label>
          <label className="field-label">Horario de entrevista<input className="field-input" name="interview_schedule" placeholder="Ej. Miércoles 10:30 am" /></label>
          <label className="field-label">Lugar de entrevista<input className="field-input" name="interview_location" placeholder="Ej. Sucursal Centro" /></label>
          <label className="field-label md:col-span-2 xl:col-span-3">Notas de entrevista<textarea className="field-input min-h-20" name="interview_notes" placeholder="Ej. Llevar INE y solicitud elaborada" /></label>
          <label className="field-label md:col-span-2 xl:col-span-3">Documentos requeridos<textarea className="field-input min-h-20" name="documents_required" placeholder="INE\nComprobante de domicilio" /></label>
          <div className="md:col-span-2 xl:col-span-3"><button className="primary-btn" type="submit">Crear vacante</button></div>
        </form>
      </Section>

      <Section title="Vacantes cargadas" subtitle="Vista operativa de lo que el bot ya puede responder con precisión." icon="layers">
        {overview.vacancies.length ? (
          <DataTable
            columns={["Vacante", "Estado", "Sueldo", "Entrevista", "Resumen"]}
            rows={overview.vacancies.map((item) => [
              <div key={item.id}><div className="font-medium text-white">{safeText(item.title)}</div><div className="text-xs text-slate-400">{safeText(item.location_label || item.address || item.modality)}</div></div>,
              safeText(item.status),
              item.salary_visible ? safeText(item.salary_min && item.salary_max ? `${item.salary_min}-${item.salary_max} ${item.currency || "MXN"}` : item.salary_min ? `${item.salary_min} ${item.currency || "MXN"}` : "visible") : "oculto",
              item.interview_schedule ? safeText(item.interview_schedule) : "sin horario",
              safeText(item.summary || item.description),
            ])}
          />
        ) : (
          <EmptyActionState title="Todavía no hay vacantes" description="En cuanto cargues la primera, el bot ya podrá responder sobre puesto, requisitos, ubicación, sueldo y entrevista con las reglas de este bot." primaryAction={<Link href="/bot-studio" className="secondary-btn">Ir al bot</Link>} />
        )}
      </Section>

      <Section title="Candidatos confirmados" subtitle="Aquí caen los contactos que ya confirmaron asistencia a entrevista." icon="check">
        <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <div>
            {overview.candidates.length ? (
              <DataTable columns={["Contacto", "Vacante", "Estado", "Confirmado", "Conversación"]} rows={overview.candidates.map((item) => [safeText(item.contact_id), safeText(item.vacancy_title || item.vacancy_id), safeText(item.status), safeText(item.interview_confirmed_at), safeText(item.conversation_id)])} />
            ) : (
              <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] px-4 py-4 text-sm text-slate-300">Aún no hay candidatos confirmados en este bot.</div>
            )}
          </div>
          <form action={confirmTalentCandidateAction} className="grid gap-4 self-start rounded-3xl border border-white/[0.08] bg-white/[0.03] p-4">
            <input type="hidden" name="bot_id" value={selectedBot.id} />
            <input type="hidden" name="redirect_to" value="/vacantes" />
            <div className="text-sm font-medium text-white">Alta manual de candidato</div>
            <label className="field-label">Contact ID<input className="field-input" name="contact_id" placeholder="contact_xxx" required /></label>
            <label className="field-label">Conversation ID<input className="field-input" name="conversation_id" placeholder="conv_xxx" /></label>
            <label className="field-label">Vacancy ID<input className="field-input" name="vacancy_id" placeholder="vac_xxx" /></label>
            <label className="field-label">Vacante<input className="field-input" name="vacancy_title" placeholder="Ej. Cajero de sucursal" /></label>
            <label className="field-label">Notas<textarea className="field-input min-h-20" name="notes" placeholder="Confirmó asistencia por WhatsApp" /></label>
            <button className="primary-btn" type="submit">Registrar confirmación</button>
          </form>
        </div>
      </Section>

      <Section title="Lectura rápida de reglas activas" subtitle="Te deja ver si el módulo está comportándose como pediste sin revisar JSON a mano." icon="spark">
        <DataTable columns={["Regla", "Estado"]} rows={[
          ["Las vacantes viven por bot", "sí"],
          ["El bot nunca se queda callado", yesNo(Boolean(config.never_silent ?? true))],
          ["Reconocer trabajadores", yesNo(Boolean(config.worker_recognition_enabled))],
          ["Escalar trabajadores a humano", yesNo(Boolean(workerConfig.route_worker_to_human ?? true))],
          ["Mensaje sin horario", safeText(interviewPolicy.no_schedule_message)],
          ["Mensaje sueldo oculto", safeText(salaryPolicy.hide_message)],
        ]} />
      </Section>
    </Shell>
  );
}
