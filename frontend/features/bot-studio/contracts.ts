export type BotStudioCreateStep =
  | "context"
  | "identity"
  | "offer"
  | "knowledge"
  | "integrations"
  | "review"
  | "validate"
  | "apply"
  | "success";

export type BotStudioReconfigureStep =
  | "select"
  | "diff"
  | "dry-run"
  | "confirm"
  | "result";

export type BotStudioMode = "create" | "reconfigure";
