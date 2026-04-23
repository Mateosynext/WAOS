"use client";

import type { buildWizardPayloads } from "../../../app/bot-studio/wizardPayloadBuilders";
import type { RouteStep } from "../../../app/bot-studio/flowConfig";
import type { WizardInstance } from "../../../app/bot-studio/wizard-types";
import type { useBotStudioWizardState } from "../context/useBotStudioWizardState";
import type { BannerState, BotStudioFlowProps } from "./types";

export type BotStudioFlowActionDeps = {
  props: BotStudioFlowProps;
  state: ReturnType<typeof useBotStudioWizardState>;
  payloads: ReturnType<typeof buildWizardPayloads>;
  snapshot: Record<string, unknown> | null;
  goTo: (step: RouteStep, wizard?: Pick<WizardInstance, "id"> | null) => void;
  setBanner: (banner: BannerState | null) => void;
  setBusy: (value: string) => void;
  recordOperationEvent: (type: string, payload?: Record<string, unknown>, wizardIdOverride?: string | null) => void;
  recordAutosaveResult: (result: "success" | "error", durationMs: number, stepCount?: number, wizardIdOverride?: string | null) => void;
};
