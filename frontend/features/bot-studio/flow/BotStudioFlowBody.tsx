"use client";

import Link from "next/link";
import SuccessState from "../../../app/components/SuccessState";
import {
  CreateApplyScreen,
  CreateContextScreen,
  CreateIdentityScreen,
  CreateIntegrationsScreen,
  CreateKnowledgeScreen,
  CreateOfferScreen,
  CreateReviewScreen,
  CreateValidateScreen,
} from "../context/createScreens";
import {
  ReconfigureConfirmScreen,
  ReconfigureDiffScreen,
  ReconfigureDryRunScreen,
  ReconfigureSelectScreen,
} from "../../../app/bot-studio/reconfigureScreens";
import type { BotStudioFlowProps } from "./types";

type BotStudioFlowBodyProps = Pick<BotStudioFlowProps, "routeMode" | "routeStep"> & {
  createState: Record<string, unknown>;
  reconfigureState: Record<string, unknown>;
  handlers: Record<string, unknown>;
};

export function BotStudioFlowBody({ routeMode, routeStep, createState, reconfigureState, handlers }: BotStudioFlowBodyProps) {
  if (routeMode === "create") {
    if (routeStep === "success") {
      return (
        <div data-testid="success-step">
          <SuccessState
            title="Bot aplicado desde un flujo por etapas"
            description="El wizard terminó en una pantalla de resultado aislada. Ya no mezclamos review, validación y apply en la misma vista."
            actions={<><Link href="/bots" className="primary-btn">Ver bots</Link><Link href="/launch-center" className="secondary-btn">Ir a Launch center</Link></>}
          />
        </div>
      );
    }
    if (routeStep === "context") return <CreateContextScreen state={createState} handlers={handlers} />;
    if (routeStep === "identity") return <CreateIdentityScreen state={createState} handlers={handlers} />;
    if (routeStep === "offer") return <CreateOfferScreen state={createState} handlers={handlers} />;
    if (routeStep === "knowledge") return <CreateKnowledgeScreen state={createState} handlers={handlers} />;
    if (routeStep === "integrations") return <CreateIntegrationsScreen state={createState} handlers={handlers} />;
    if (routeStep === "review") return <CreateReviewScreen state={createState} handlers={handlers} />;
    if (routeStep === "validate") return <CreateValidateScreen state={createState} />;
    if (routeStep === "apply") return <CreateApplyScreen state={createState} />;
  }

  if (routeMode === "reconfigure") {
    if (routeStep === "result") {
      return (
        <div data-testid="success-step">
          <SuccessState
            title="Reconfiguración aplicada"
            description="La salida final vive en su propia pantalla de resultado."
            actions={<><Link href="/launch-center" className="primary-btn">Ir a Launch center</Link></>}
          />
        </div>
      );
    }
    if (routeStep === "select") return <ReconfigureSelectScreen state={reconfigureState} handlers={{ setSelectedBotId: handlers.setSelectedBotId }} />;
    if (routeStep === "diff") return <ReconfigureDiffScreen state={reconfigureState} />;
    if (routeStep === "dry-run") return <ReconfigureDryRunScreen state={reconfigureState} />;
    if (routeStep === "confirm") return <ReconfigureConfirmScreen state={reconfigureState} />;
  }

  return null;
}
