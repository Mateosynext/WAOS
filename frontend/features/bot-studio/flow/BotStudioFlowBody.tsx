"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import SuccessState from "@/app/components/SuccessState";
import type { BotStudioFlowProps } from "./types";
import type { CreateWizardScreenModels, ReconfigureWizardScreenModels } from "./useBotStudioFlowStateModel";

const StepScreenFallback = () => (
  <div className="grid gap-4" aria-busy="true" aria-label="Cargando paso del wizard">
    <div className="h-8 w-56 animate-pulse rounded-full bg-[color:var(--surface-subtle)]" />
    <div className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5">
      <div className="h-4 w-2/3 animate-pulse rounded-full bg-[color:var(--surface-subtle)]" />
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="h-24 animate-pulse rounded-2xl bg-[color:var(--surface-subtle)]" />
        <div className="h-24 animate-pulse rounded-2xl bg-[color:var(--surface-subtle)]" />
      </div>
    </div>
  </div>
);

const CreateContextScreen = dynamic(() => import("../context/screens/CreateContextScreen").then((mod) => mod.CreateContextScreen), { loading: StepScreenFallback });
const CreateIdentityScreen = dynamic(() => import("../context/screens/CreateIdentityScreen").then((mod) => mod.CreateIdentityScreen), { loading: StepScreenFallback });
const CreateOfferScreen = dynamic(() => import("../context/screens/CreateOfferScreen").then((mod) => mod.CreateOfferScreen), { loading: StepScreenFallback });
const CreateKnowledgeScreen = dynamic(() => import("../context/screens/CreateKnowledgeScreen").then((mod) => mod.CreateKnowledgeScreen), { loading: StepScreenFallback });
const CreateIntegrationsScreen = dynamic(() => import("../context/screens/CreateIntegrationsScreen").then((mod) => mod.CreateIntegrationsScreen), { loading: StepScreenFallback });
const CreateReviewScreen = dynamic(() => import("../context/screens/CreateReviewScreen").then((mod) => mod.CreateReviewScreen), { loading: StepScreenFallback });
const CreateValidateScreen = dynamic(() => import("../context/screens/CreateValidateScreen").then((mod) => mod.CreateValidateScreen), { loading: StepScreenFallback });
const CreateApplyScreen = dynamic(() => import("../context/screens/CreateApplyScreen").then((mod) => mod.CreateApplyScreen), { loading: StepScreenFallback });

const ReconfigureSelectScreen = dynamic(() => import("../reconfigure/screens/ReconfigureSelectScreen").then((mod) => mod.ReconfigureSelectScreen), { loading: StepScreenFallback });
const ReconfigureDiffScreen = dynamic(() => import("../reconfigure/screens/ReconfigureDiffScreen").then((mod) => mod.ReconfigureDiffScreen), { loading: StepScreenFallback });
const ReconfigureDryRunScreen = dynamic(() => import("../reconfigure/screens/ReconfigureDryRunScreen").then((mod) => mod.ReconfigureDryRunScreen), { loading: StepScreenFallback });
const ReconfigureConfirmScreen = dynamic(() => import("../reconfigure/screens/ReconfigureConfirmScreen").then((mod) => mod.ReconfigureConfirmScreen), { loading: StepScreenFallback });

type BotStudioFlowBodyProps = Pick<BotStudioFlowProps, "routeMode" | "routeStep"> & {
  createScreens: CreateWizardScreenModels;
  reconfigureScreens: ReconfigureWizardScreenModels;
};

export function BotStudioFlowBody({ routeMode, routeStep, createScreens, reconfigureScreens }: BotStudioFlowBodyProps) {
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
    if (routeStep === "context") return <CreateContextScreen viewModel={createScreens.context.viewModel} actions={createScreens.context.actions} />;
    if (routeStep === "identity") return <CreateIdentityScreen viewModel={createScreens.identity.viewModel} actions={createScreens.identity.actions} />;
    if (routeStep === "offer") return <CreateOfferScreen viewModel={createScreens.offer.viewModel} actions={createScreens.offer.actions} />;
    if (routeStep === "knowledge") return <CreateKnowledgeScreen viewModel={createScreens.knowledge.viewModel} actions={createScreens.knowledge.actions} />;
    if (routeStep === "integrations") return <CreateIntegrationsScreen viewModel={createScreens.integrations.viewModel} actions={createScreens.integrations.actions} />;
    if (routeStep === "review") return <CreateReviewScreen viewModel={createScreens.review.viewModel} actions={createScreens.review.actions} />;
    if (routeStep === "validate") return <CreateValidateScreen viewModel={createScreens.validate.viewModel} />;
    if (routeStep === "apply") return <CreateApplyScreen viewModel={createScreens.apply.viewModel} />;
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
    if (routeStep === "select") return <ReconfigureSelectScreen viewModel={reconfigureScreens.select.viewModel} actions={reconfigureScreens.select.actions} />;
    if (routeStep === "diff") return <ReconfigureDiffScreen viewModel={reconfigureScreens.diff.viewModel} />;
    if (routeStep === "dry-run") return <ReconfigureDryRunScreen viewModel={reconfigureScreens.dryRun.viewModel} />;
    if (routeStep === "confirm") return <ReconfigureConfirmScreen viewModel={reconfigureScreens.confirm.viewModel} />;
  }

  return null;
}
