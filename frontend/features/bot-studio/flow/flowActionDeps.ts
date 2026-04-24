"use client";

import type { buildWizardPayloads } from "@/features/bot-studio/services/wizardPayloadBuilders";
import type { RouteStep } from "@/features/bot-studio/domain/flowConfig";
import type { WizardInstance, WizardValidationSnapshot } from "@/features/bot-studio/domain/wizardTypes";
import type { BotStudioWizardStateModel } from "../context/useBotStudioWizardState";
import type { BannerState, BotStudioFlowProps } from "./types";

export type BotStudioFlowActionDeps = {
  props: BotStudioFlowProps;
  state: BotStudioWizardStateModel;
  payloads: ReturnType<typeof buildWizardPayloads>;
  snapshot: WizardValidationSnapshot | null;
  goTo: (step: RouteStep, wizard?: Pick<WizardInstance, "id"> | null) => void;
  setBanner: (banner: BannerState | null) => void;
  setBusy: (value: string) => void;
  recordOperationEvent: (type: string, payload?: Record<string, unknown>, wizardIdOverride?: string | null) => void;
  recordAutosaveResult: (result: "success" | "error", durationMs: number, stepCount?: number, wizardIdOverride?: string | null) => void;
};
