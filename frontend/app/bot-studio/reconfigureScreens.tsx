"use client";

import { safeText } from "../lib/ui";
import { DiffCard, ValidationSnapshotPanel, VerticalScorecardPanel } from "./wizardReviewSections";
import { FieldGroup, SelectField, SummaryCard } from "./flowUi";

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function splitList(value: unknown) {
  return Array.isArray(value) ? value.map((item) => String(item || "").trim()).filter(Boolean) : [];
}

function botServices(bot: any) {
  return splitList(asRecord(asRecord(bot?.config_draft).business_knowledge).services);
}

function botPolicies(bot: any) {
  return splitList(asRecord(asRecord(bot?.config_draft).business_knowledge).policies);
}

function botIntegrations(bot: any) {
  return Object.keys(asRecord(asRecord(bot?.config_draft).integrations)).filter(Boolean);
}

export function ReconfigureSelectScreen({ state, handlers }: any) {
  return (
    <FieldGroup testId="reconfigure-select-step" title="Selecciona el bot a reconfigurar" description="En reconfigure el primer paso es explícito: eliges el bot.">
      <SelectField
        testId="reconfigure-bot-select"
        label="Bot objetivo"
        value={state.selectedBot?.id || ""}
        onChange={handlers.setSelectedBotId}
        options={[{ label: "Selecciona un bot", value: "" }, ...state.bots.map((item: any) => ({ label: `${item.name} · ${item.organization_id}`, value: item.id }))]}
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <SummaryCard title="Bot activo" tone="accent">{safeText(state.selectedBot?.name, "Ninguno")}</SummaryCard>
        <SummaryCard title="Industria">{safeText(state.selectedBot?.vertical, "Sin industria visible")}</SummaryCard>
        <SummaryCard title="Última release">{safeText(state.selectedBot?.last_release_at, "Sin release visible")}</SummaryCard>
      </div>
    </FieldGroup>
  );
}

export function ReconfigureDiffScreen({ state }: any) {
  const selectedBot = state.selectedBot;
  const blueprint = state.blueprint;
  return (
    <div className="grid gap-6" data-testid="diff-step">
      <FieldGroup title="Aísla el diff antes de tocar producción" description="Aquí solo ves qué cambiaría respecto al estado actual del bot.">
        <div className="grid gap-4 lg:grid-cols-3">
          <SummaryCard title="Bot">{safeText(selectedBot?.name, "Sin bot seleccionado")}</SummaryCard>
          <SummaryCard title="Blueprint propuesto">{safeText(blueprint?.profile?.short_name || blueprint?.profile?.name, "Sin blueprint visible")}</SummaryCard>
          <SummaryCard title="Wizard">{safeText(state.wizard?.id, "Sin wizard")}</SummaryCard>
        </div>
      </FieldGroup>
      <div className="grid gap-4 xl:grid-cols-2">
        <DiffCard title="Oferta" before={botServices(selectedBot).join(" · ") || "Sin servicios visibles"} after={splitList(blueprint?.setup?.services).join(" · ") || "Sin propuesta visible"} status={botServices(selectedBot).join("|") === splitList(blueprint?.setup?.services).join("|") ? "keep" : "replace"} detail="La oferta propuesta ya no se mezcla con confirmación ni publicación." />
        <DiffCard title="Knowledge" before={botPolicies(selectedBot).join(" · ") || "Sin políticas visibles"} after={splitList(blueprint?.setup?.wizard?.policies).join(" · ") || "Sin políticas propuestas"} status={botPolicies(selectedBot).join("|") === splitList(blueprint?.setup?.wizard?.policies).join("|") ? "keep" : "replace"} detail="Las políticas sugeridas quedan en su propio bloque." />
        <DiffCard title="Integraciones" before={botIntegrations(selectedBot).join(" · ") || "Sin integraciones visibles"} after={(blueprint?.setup?.wizard?.recommended_integrations || []).map((item: any) => item.name || item.provider || item.integration_key || "").filter(Boolean).join(" · ") || "Sin propuesta visible"} status={botIntegrations(selectedBot).length ? "suggest" : "add"} detail="La vista separa integraciones actuales y propuestas." />
        <DiffCard title="Tono" before={safeText(selectedBot?.tone, "Sin tono visible")} after={safeText(blueprint?.setup?.personality?.tone, "Sin tono propuesto")} status={safeText(selectedBot?.tone) === safeText(blueprint?.setup?.personality?.tone) ? "keep" : "replace"} detail="La reconfiguración trata el tono como un cambio aislado y visible." />
      </div>
    </div>
  );
}

export function ReconfigureDryRunScreen({ state }: any) {
  const snapshot = state.validationSnapshot || state.wizard?.validation_snapshot || null;
  return (
    <div className="grid gap-6" data-testid="dry-run-step">
      <FieldGroup title="Corre el dry run" description="Esta pantalla existe solo para validar impacto.">
        <div className="grid gap-4 lg:grid-cols-3">
          <SummaryCard title="Bot">{safeText(state.selectedBot?.name, "Sin bot")}</SummaryCard>
          <SummaryCard title="Dry run">{safeText(state.dryRunResult?.summary?.status || snapshot?.simulation_result?.status, "Pendiente")}</SummaryCard>
          <SummaryCard title="Gate">{safeText(snapshot?.gate?.label, "Sin gate visible")}</SummaryCard>
        </div>
      </FieldGroup>
      <ValidationSnapshotPanel title="Checklist de reconfiguración" description="La validación vive sola aquí." snapshot={snapshot} />
      <VerticalScorecardPanel title="Cobertura del cambio" description="Lectura de señales para no aplicar una reconfiguración a ciegas." snapshot={snapshot} />
    </div>
  );
}

export function ReconfigureConfirmScreen({ state }: any) {
  const snapshot = state.validationSnapshot || state.wizard?.validation_snapshot || null;
  return (
    <FieldGroup testId="confirm-step" title="Confirma la reconfiguración" description="Confirmar es su propia pantalla.">
      <div className="grid gap-4 lg:grid-cols-3">
        <SummaryCard title="Bot" tone="accent">{safeText(state.selectedBot?.name, "Sin bot")}</SummaryCard>
        <SummaryCard title="Gate de salida" tone={snapshot?.gate?.status === "green" ? "success" : "warning"}>{safeText(snapshot?.gate?.detail, "Sin detalle")}</SummaryCard>
        <SummaryCard title="Wizard">{safeText(state.wizard?.id, "Sin wizard")}</SummaryCard>
      </div>
    </FieldGroup>
  );
}
