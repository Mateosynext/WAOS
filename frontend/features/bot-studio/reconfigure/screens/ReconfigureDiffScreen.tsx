"use client";

import { safeText } from "@/shared/lib/ui";
import { DiffCard } from "@/features/bot-studio/review/DiffCard";
import { FieldGroup, SummaryCard } from "@/features/bot-studio/ui/flowUi";
import { botIntegrations, botPolicies, botServices, integrationLabel, splitList } from "../reconfigureScreenHelpers";
import type { ReconfigureDiffViewModel } from "../reconfigureScreenTypes";

export function ReconfigureDiffScreen({ viewModel: state }: { viewModel: ReconfigureDiffViewModel }) {
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
        <DiffCard title="Integraciones" before={botIntegrations(selectedBot).join(" · ") || "Sin integraciones visibles"} after={(blueprint?.setup?.wizard?.recommended_integrations || []).map(integrationLabel).filter(Boolean).join(" · ") || "Sin propuesta visible"} status={botIntegrations(selectedBot).length ? "suggest" : "add"} detail="La vista separa integraciones actuales y propuestas." />
        <DiffCard title="Tono" before={safeText(selectedBot?.tone, "Sin tono visible")} after={safeText(blueprint?.setup?.personality?.tone, "Sin tono propuesto")} status={safeText(selectedBot?.tone) === safeText(blueprint?.setup?.personality?.tone) ? "keep" : "replace"} detail="La reconfiguración trata el tono como un cambio aislado y visible." />
      </div>
    </div>
  );
}
