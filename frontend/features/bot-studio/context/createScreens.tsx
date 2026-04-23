"use client";

import { safeText } from "../../../app/lib/ui";
import SubverticalPicker from "../../../app/bot-studio/SubverticalPicker";
import VerticalPicker from "../../../app/bot-studio/VerticalPicker";
import { ValidationSnapshotPanel, VerticalScorecardPanel } from "../review/wizardReviewSections";
import { ChecklistChips, FieldGroup, InputField, SelectField, SummaryCard, TextAreaField } from "../../../app/bot-studio/flowUi";
import type { WizardSubverticalProfile } from "../../../app/bot-studio/wizard-types";

function unique(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.map((item) => String(item || "").trim()).filter(Boolean)));
}

function lines(value: string) {
  return unique(value.split(/\r?\n/).map((item) => item.trim()));
}

function subverticalProfiles(state: any): WizardSubverticalProfile[] {
  if (state.verticalProfile?.subvertical_profiles?.length) return state.verticalProfile.subvertical_profiles;
  if (state.blueprint?.selected_subvertical?.name) return [state.blueprint.selected_subvertical];
  return unique([
    state.blueprint?.selected_subvertical?.name,
    ...(state.blueprint?.profile?.recommended_subverticals || []),
    ...(state.blueprint?.profile?.subverticals || []),
  ]).map((name) => ({ id: name.toLowerCase().replace(/[^a-z0-9]+/g, "-"), name }));
}

function recInts(state: any) {
  return unique((state.blueprint?.setup?.wizard?.recommended_integrations || []).map((item: any) => item.name || item.provider || item.integration_key));
}

function recPlaybooks(state: any) {
  return unique((state.blueprint?.setup?.wizard?.recommended_playbooks || []).map((item: any) => item.label || item.key));
}

export function CreateContextScreen({ state, handlers }: any) {
  const profiles = subverticalProfiles(state);
  return (
    <div className="grid gap-6">
      <FieldGroup
        testId="create-context-step"
        title="Define el contexto base del bot"
        description="En este paso solo decides el terreno de juego: organización, industria, subvertical y objetivo principal. No mezclamos todavía identidad ni contenido."
      >
        <div className="grid gap-4 lg:grid-cols-2">
          <SelectField
            testId="organization-select"
            label="Organización"
            value={state.selectedOrganizationId}
            onChange={handlers.setSelectedOrganizationId}
            options={[{ label: "Selecciona una organización", value: "" }, ...state.organizations.map((item: any) => ({ label: item.name, value: item.id }))]}
          />
          <SelectField
            testId="primary-objective-select"
            label="Objetivo principal"
            value={state.selectedPrimaryObjective}
            onChange={handlers.setSelectedPrimaryObjective}
            options={[
              { label: "Agendar", value: "agendar" },
              { label: "Vender", value: "vender" },
              { label: "Calificar", value: "calificar" },
              { label: "Responder", value: "responder" },
              { label: "Reactivar", value: "reactivar" },
            ]}
          />
        </div>
        <VerticalPicker
          verticals={state.verticals}
          strongestVerticals={state.strongestVerticals}
          candidateVerticalId={state.candidateVerticalId}
          confirmedVerticalId={state.selectedVerticalId}
          onPreview={handlers.setCandidateVerticalId}
          onConfirm={(verticalId) => {
            handlers.setCandidateVerticalId(verticalId);
            handlers.setSelectedVerticalId(verticalId);
          }}
        />
        <SubverticalPicker
          verticalName={safeText(state.verticals.find((item: any) => item.id === state.candidateVerticalId || item.id === state.selectedVerticalId)?.name, "Industria pendiente")}
          candidateSubvertical={state.candidateSubvertical}
          confirmedSubvertical={state.selectedSubvertical}
          subverticalProfiles={profiles}
          loading={state.previewLoading}
          verticalConfirmed={Boolean(state.selectedVerticalId)}
          onPreview={handlers.setCandidateSubvertical}
          onConfirm={(subvertical: string) => {
            handlers.setCandidateSubvertical(subvertical);
            handlers.setSelectedSubvertical(subvertical);
          }}
        />
        {state.previewError ? <SummaryCard title="Señal de contexto" tone="warning">{state.previewError}</SummaryCard> : null}
      </FieldGroup>

      <div className="grid gap-4 lg:grid-cols-3">
        <SummaryCard title="Contexto confirmado" tone="accent">
          {safeText(state.verticals.find((item: any) => item.id === state.selectedVerticalId)?.name, "Industria pendiente")} · {state.selectedSubvertical || "Subvertical pendiente"}
        </SummaryCard>
        <SummaryCard title="Objetivo principal">{state.selectedPrimaryObjective || "Sin objetivo visible"}</SummaryCard>
        <SummaryCard title="Blueprint activo">{safeText(state.blueprint?.profile?.short_name || state.blueprint?.profile?.name, "Sin blueprint generado todavía")}</SummaryCard>
      </div>
    </div>
  );
}

export function CreateIdentityScreen({ state, handlers }: any) {
  return (
    <FieldGroup testId="create-identity-step" title="Define la identidad operativa" description="Aquí decides cómo se presenta el bot. No mezclamos catálogo ni reglas todavía.">
      <div className="grid gap-4 lg:grid-cols-2">
        <InputField testId="business-name-input" label="Nombre del negocio" value={state.businessName} onChange={handlers.setBusinessName} />
        <InputField testId="bot-name-input" label="Nombre del bot" value={state.botName} onChange={handlers.setBotName} />
        <InputField testId="tone-input" label="Tono" value={state.tone} onChange={handlers.setTone} />
        <SelectField
          testId="language-select"
          label="Idioma"
          value={state.language}
          onChange={handlers.setLanguage}
          options={[{ label: "Español", value: "es" }, { label: "English", value: "en" }]}
        />
        <InputField testId="timezone-input" label="Zona horaria" value={state.timezone} onChange={handlers.setTimezone} />
        <InputField testId="whatsapp-number-input" label="WhatsApp visible" value={state.whatsappNumber} onChange={handlers.setWhatsappNumber} />
      </div>
      <TextAreaField testId="hours-textarea" label="Horario operativo" value={state.hours} onChange={handlers.setHours} rows={4} />
    </FieldGroup>
  );
}

export function CreateOfferScreen({ state, handlers }: any) {
  return (
    <FieldGroup testId="create-offer-step" title="Captura la oferta comercial" description="CTA, servicios y pricing viven aislados aquí.">
      <TextAreaField testId="services-textarea" label="Servicios" value={state.servicesText} onChange={handlers.setServicesText} />
      <TextAreaField testId="featured-offers-textarea" label="Ofertas destacadas" value={state.featuredOffersText} onChange={handlers.setFeaturedOffersText} />
      <TextAreaField testId="primary-ctas-textarea" label="CTA principales" value={state.primaryCtasText} onChange={handlers.setPrimaryCtasText} />
      <TextAreaField testId="pricing-notes-textarea" label="Notas de pricing" value={state.pricingNotesText} onChange={handlers.setPricingNotesText} />
    </FieldGroup>
  );
}

export function CreateKnowledgeScreen({ state, handlers }: any) {
  return (
    <FieldGroup testId="create-knowledge-step" title="Separa el knowledge del bot" description="FAQs, políticas y fuentes viven en esta pantalla.">
      <TextAreaField testId="faq-textarea" label="FAQs" hint="Formato: pregunta | respuesta" value={state.faqText} onChange={handlers.setFaqText} rows={8} />
      <TextAreaField testId="policies-textarea" label="Políticas" value={state.policiesText} onChange={handlers.setPoliciesText} />
      <TextAreaField testId="knowledge-sources-textarea" label="Fuentes de conocimiento" value={state.knowledgeSourcesText} onChange={handlers.setKnowledgeSourcesText} />
    </FieldGroup>
  );
}

export function CreateIntegrationsScreen({ state, handlers }: any) {
  const options = recInts(state);
  return (
    <FieldGroup testId="create-integrations-step" title="Configura integraciones y reglas operativas" description="Aquí solo decides qué sistemas toca el bot y cuándo debe escalar.">
      {options.length ? (
        <ChecklistChips
          label="Integraciones recomendadas"
          options={options}
          selected={state.selectedIntegrationKeys}
          onToggle={(value) => handlers.setSelectedIntegrationKeys((prev: string[]) => prev.includes(value) ? prev.filter((item) => item !== value) : [...prev, value])}
        />
      ) : null}
      <TextAreaField testId="escalate-when-textarea" label="Escalar cuando" value={state.escalateWhenText} onChange={handlers.setEscalateWhenText} />
      <TextAreaField testId="handoff-keywords-textarea" label="Palabras clave de handoff" value={state.handoffKeywordsText} onChange={handlers.setHandoffKeywordsText} rows={4} />
      <div className="grid gap-4 lg:grid-cols-2">
        <InputField testId="handoff-sla-input" label="SLA de handoff" value={state.handoffSlaText} onChange={handlers.setHandoffSlaText} />
        <InputField testId="human-destination-input" label="Destino humano" value={state.humanDestinationChannelText} onChange={handlers.setHumanDestinationChannelText} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <TextAreaField testId="can-say-textarea" label="Puede decir" value={state.canSayText} onChange={handlers.setCanSayText} rows={5} />
        <TextAreaField testId="cannot-say-textarea" label="No puede decir" value={state.cannotSayText} onChange={handlers.setCannotSayText} rows={5} />
      </div>
      <TextAreaField testId="rule-overrides-textarea" label="Overrides avanzados" value={state.ruleOverridesText} onChange={handlers.setRuleOverridesText} rows={6} />
    </FieldGroup>
  );
}

export function CreateReviewScreen({ state, handlers }: any) {
  const options = recPlaybooks(state);
  return (
    <div className="grid gap-6" data-testid="create-review-step">
      <FieldGroup title="Revisa el setup antes de validar" description="Esta pantalla resume el draft y te deja decidir si está listo para validar.">
        {options.length ? (
          <ChecklistChips
            label="Playbooks sugeridos"
            options={options}
            selected={state.selectedPlaybookKeys}
            onToggle={(value) => handlers.setSelectedPlaybookKeys((prev: string[]) => prev.includes(value) ? prev.filter((item) => item !== value) : [...prev, value])}
          />
        ) : null}
        <TextAreaField testId="launch-notes-textarea" label="Notas de lanzamiento" value={state.launchNotesText} onChange={handlers.setLaunchNotesText} rows={5} />
        <div className="rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4">
          <label className="flex items-center gap-3 text-sm text-[color:var(--text-primary)]">
            <input data-testid="autopublish-knowledge-checkbox" type="checkbox" checked={state.autopublishKnowledge} onChange={() => handlers.setAutopublishKnowledge((prev: boolean) => !prev)} />
            Autopublicar knowledge al aplicar
          </label>
        </div>
      </FieldGroup>

      <div className="grid gap-4 xl:grid-cols-2">
        <SummaryCard title="Contexto" tone="accent">{safeText(state.verticals.find((item: any) => item.id === state.selectedVerticalId)?.name, "Sin industria")} · {state.selectedSubvertical || "Sin subvertical"} · objetivo {state.selectedPrimaryObjective || "sin objetivo"}</SummaryCard>
        <SummaryCard title="Oferta">{lines(state.servicesText).slice(0, 4).join(" · ") || "Sin servicios visibles"}</SummaryCard>
        <SummaryCard title="Knowledge">{lines(state.policiesText).slice(0, 4).join(" · ") || "Sin políticas visibles"}</SummaryCard>
        <SummaryCard title="Integraciones">{state.selectedIntegrationKeys.join(" · ") || "Sin integraciones seleccionadas"}</SummaryCard>
      </div>
    </div>
  );
}

export function CreateValidateScreen({ state }: any) {
  const snapshot = state.validationSnapshot || state.wizard?.validation_snapshot || null;
  return (
    <div className="grid gap-6" data-testid="validate-step">
      <FieldGroup title="Valida antes de aplicar" description="La decisión de esta pantalla es simple: ver si el draft está listo o si debe regresar a un paso anterior.">
        <div className="grid gap-4 lg:grid-cols-3">
          <SummaryCard title="Wizard">{safeText(state.wizard?.id, "Sin wizard")}</SummaryCard>
          <SummaryCard title="Gate" tone={snapshot?.gate?.status === "green" ? "success" : snapshot?.gate?.status === "yellow" ? "warning" : "default"}>{safeText(snapshot?.gate?.label, "Pendiente de validación")}</SummaryCard>
          <SummaryCard title="Dry run">{safeText(state.dryRunResult?.summary?.status || snapshot?.simulation_result?.status, "Aún no corre")}</SummaryCard>
        </div>
      </FieldGroup>
      <ValidationSnapshotPanel title="Checklist de salida" description="Esta lectura ya no compite con edición ni confirmación." snapshot={snapshot} />
      <VerticalScorecardPanel title="Cobertura por vertical" description="Señales visibles para saber si el setup cubre la vertical elegida." snapshot={snapshot} />
    </div>
  );
}

export function CreateApplyScreen({ state }: any) {
  const snapshot = state.validationSnapshot || state.wizard?.validation_snapshot || null;
  return (
    <div className="grid gap-6" data-testid="apply-step">
      <FieldGroup title="Confirma el apply" description="Aquí solo decides si aplicar el draft validado.">
        <div className="grid gap-4 lg:grid-cols-3">
          <SummaryCard title="Wizard" tone="accent">{safeText(state.wizard?.id, "Sin wizard")}</SummaryCard>
          <SummaryCard title="Gate de validación" tone={snapshot?.gate?.status === "green" ? "success" : "warning"}>{safeText(snapshot?.gate?.detail, "Revisa la validación antes de aplicar.")}</SummaryCard>
          <SummaryCard title="Knowledge autopublish">{state.autopublishKnowledge ? "Sí" : "No"}</SummaryCard>
        </div>
      </FieldGroup>
    </div>
  );
}
