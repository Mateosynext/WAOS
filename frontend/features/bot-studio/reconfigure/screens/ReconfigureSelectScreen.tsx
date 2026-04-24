"use client";

import { safeText } from "@/app/lib/ui";
import { FieldGroup, SelectField, SummaryCard } from "@/features/bot-studio/ui/flowUi";
import type { ReconfigureSelectActions, ReconfigureSelectViewModel } from "../reconfigureScreenTypes";

export function ReconfigureSelectScreen({ viewModel: state, actions: handlers }: { viewModel: ReconfigureSelectViewModel; actions: ReconfigureSelectActions }) {
  return (
    <FieldGroup testId="reconfigure-select-step" title="Selecciona el bot a reconfigurar" description="En reconfigure el primer paso es explícito: eliges el bot.">
      <SelectField
        testId="reconfigure-bot-select"
        label="Bot objetivo"
        value={state.selectedBot?.id || ""}
        onChange={handlers.setSelectedBotId}
        options={[{ label: "Selecciona un bot", value: "" }, ...state.bots.map((item) => ({ label: `${item.name} · ${item.organization_id}`, value: item.id }))]}
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <SummaryCard title="Bot activo" tone="accent">{safeText(state.selectedBot?.name, "Ninguno")}</SummaryCard>
        <SummaryCard title="Industria">{safeText(state.selectedBot?.vertical, "Sin industria visible")}</SummaryCard>
        <SummaryCard title="Última release">{safeText(state.selectedBot?.last_release_at, "Sin release visible")}</SummaryCard>
      </div>
    </FieldGroup>
  );
}
