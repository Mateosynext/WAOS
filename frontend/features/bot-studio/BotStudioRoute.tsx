"use client";

import Link from "next/link";
import { UiMessage } from "@/app/components/UiMessage";
import { ActionBar, ProgressHeader, StepRail } from "./ui/flowUi";
import { StickySummaryRail } from "@/features/bot-studio/review/StickySummaryRail";
import { useBotStudioWizardState } from "@/features/bot-studio/context/useBotStudioWizardState";
import { BotStudioFlowBody } from "@/features/bot-studio/flow/BotStudioFlowBody";
import { useBotStudioFlowController } from "@/features/bot-studio/flow/useBotStudioFlowController";
import type { BotStudioFlowProps } from "@/features/bot-studio/flow/types";

export function BotStudioRoute(props: BotStudioFlowProps) {
  const state = useBotStudioWizardState({
    initialSelectedBotId: props.initialSelectedBotId,
    initialMode: props.routeMode,
    initialOrganizationId: props.initialOrganizationId,
    initialVerticalId: props.initialVerticalId,
    initialSubvertical: props.initialSubvertical,
    initialPrimaryObjective: props.initialPrimaryObjective,
    initialBlueprint: props.initialBlueprint,
    initialVerticalProfile: props.initialVerticalProfile,
    initialWizardId: props.initialWizardId,
    initialWizard: props.initialWizard,
    initialStepOverride: props.routeStep,
  });

  const controller = useBotStudioFlowController(props, state);

  return (
    <div className="grid gap-6">
      <ProgressHeader
        eyebrow={props.routeMode === "create" ? "Bot Studio · Create" : "Bot Studio · Reconfigure"}
        title={controller.currentStepMeta?.label || "Bot Studio"}
        description={controller.currentStepMeta?.description || "Flujo guiado por pantallas aisladas."}
        stepLabel={`${controller.currentIndex + 1} de ${controller.flowSteps.length}`}
        progress={controller.progress}
      />

      {controller.banner ? <UiMessage title={controller.banner.title} tone={controller.banner.tone}>{controller.banner.detail}</UiMessage> : null}
      {props.loadWarnings?.length ? (
        <UiMessage title="Bot Studio cargó en modo degradado" tone="warning">
          <p>Algunos datos opcionales fallaron. No interpretes listas vacías como estado real hasta revisar backend/API.</p>
          <ul className="mt-2 list-disc pl-5">{props.loadWarnings.map((warning) => <li key={`${warning.source}:${warning.message}`}>{warning.message}</li>)}</ul>
        </UiMessage>
      ) : null}
      {controller.busy ? <UiMessage title="Procesando" tone="info">{controller.busy}</UiMessage> : null}
      {state.slices.autosave.lastSavedAt ? <UiMessage title="Persistencia" tone="success">Último guardado visible: {state.slices.autosave.lastSavedAt}</UiMessage> : null}

      <div className="grid gap-6 xl:grid-cols-[300px,minmax(0,1fr),360px]">
        <StepRail title={props.routeMode === "create" ? "Flujo de creación" : "Flujo de reconfiguración"} items={controller.flowSteps} activeKey={props.routeStep} />
        <div className="grid gap-6">
          <BotStudioFlowBody
            routeMode={props.routeMode}
            routeStep={props.routeStep}
            createScreens={controller.createScreens}
            reconfigureScreens={controller.reconfigureScreens}
          />
        </div>
        <StickySummaryRail
          mode={props.routeMode}
          organizationName={controller.summary.organizationName}
          industry={controller.summary.industry}
          operationType={controller.summary.operationType}
          objective={controller.summary.objective}
          businessName={controller.summary.businessName}
          assistantName={controller.summary.assistantName}
          recommendedChannels={controller.summary.recommendedChannels}
          seededServices={controller.summary.seededServices}
          createdTemplates={controller.summary.createdTemplates}
          readinessScore={controller.summary.readinessScore}
          readinessLabel={controller.summary.readinessLabel}
          readinessTone={controller.summary.readinessTone}
          risks={controller.summary.risks}
        />
      </div>

      {controller.primaryLabel ? (
        <ActionBar
          helper={props.routeMode === "create" ? "Una pantalla, una decisión principal. Si el backend no completa el step, el flujo se queda aquí con feedback explícito." : "Reconfigure ya no comparte el mismo bloque pesado de create y no deja confirmar con dry run rojo."}
          previous={controller.prev ? <button type="button" className="secondary-btn" onClick={() => controller.goTo(controller.prev!)}>Anterior</button> : <Link href="/bot-studio" className="secondary-btn">Salir</Link>}
          next={<button data-testid={controller.primaryTestId} type="button" className="primary-btn" disabled={controller.primaryDisabled} onClick={controller.handleNext}>{controller.primaryLabel}</button>}
        />
      ) : null}
    </div>
  );
}

export default BotStudioRoute;
