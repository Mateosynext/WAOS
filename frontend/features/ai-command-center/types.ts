export type AiCommandOrganization = {
  id: string;
  name: string;
  vertical?: string | null;
  subvertical?: string | null;
  timezone?: string | null;
};
export type AiCommandBotOption = { id: string; name: string };

export type AiCommandVerticalOption = {
  id: string;
  name: string;
  short_name?: string | null;
  subverticals?: string[];
  recommended_subverticals?: string[];
  subvertical_profiles?: Array<{ name?: string | null; id?: string | null }>;
};

export type AiWorkflowEvent = {
  id?: string;
  event_type?: string;
  message?: string;
  progress?: number;
  payload_json?: Record<string, unknown> | null;
  created_at?: string;
  [key: string]: unknown;
};

export type AiWorkflowRunEnvelope = {
  run?: Record<string, unknown>;
  steps?: Array<Record<string, unknown>>;
  events?: AiWorkflowEvent[];
  human_confirmations?: Array<Record<string, unknown>>;
  result?: Record<string, unknown>;
};

export type BotAutopilotStartResponse = {
  run_id?: string;
  wizard_id?: string | null;
  bot_id?: string | null;
  status?: string;
  progress?: number;
  requested_intensity?: string;
  effective_intensity?: string;
  safety_warnings?: string[];
  next_action?: Record<string, unknown>;
};

export type AiCommandPayload = {
  organization_id: string;
  bot_id?: string | null;
  user_description: string;
  vertical_id?: string | null;
  subvertical?: string | null;
  primary_objective?: string | null;
  language: string;
  timezone: string;
  intensity: "conservative" | "balanced" | "aggressive" | "savage" | "godmode";
  auto_generate_knowledge: boolean;
  auto_generate_templates: boolean;
  auto_generate_tools: boolean;
  auto_run_simulations: boolean;
  auto_autofix: boolean;
  auto_prepare_go_live: boolean;
  auto_apply: boolean;
  max_cost_usd?: number | null;
};
