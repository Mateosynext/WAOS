"use client";

import { safeText } from "@/app/lib/ui";
import SubverticalPicker from "@/features/bot-studio/ui/SubverticalPicker";
import VerticalPicker from "@/features/bot-studio/ui/VerticalPicker";
import { FieldGroup, SelectField, SummaryCard } from "@/features/bot-studio/ui/flowUi";
import { subverticalProfiles } from "../createScreenHelpers";
import type { CreateContextActions, CreateContextViewModel } from "../createScreenTypes";

export function CreateContextScreen({ viewModel: state, actions: handlers }: { viewModel: CreateContextViewModel; actions: CreateContextActions }) {
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
            options={[{ label: "Selecciona una organización", value: "" }, ...state.organizations.map((item) => ({ label: item.name, value: item.id }))]}
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
          verticalName={safeText(state.verticals.find((item) => item.id === state.candidateVerticalId || item.id === state.selectedVerticalId)?.name, "Industria pendiente")}
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
          {safeText(state.verticals.find((item) => item.id === state.selectedVerticalId)?.name, "Industria pendiente")} · {state.selectedSubvertical || "Subvertical pendiente"}
        </SummaryCard>
        <SummaryCard title="Objetivo principal">{state.selectedPrimaryObjective || "Sin objetivo visible"}</SummaryCard>
        <SummaryCard title="Blueprint activo">{safeText(state.blueprint?.profile?.short_name || state.blueprint?.profile?.name, "Sin blueprint generado todavía")}</SummaryCard>
      </div>
    </div>
  );
}
