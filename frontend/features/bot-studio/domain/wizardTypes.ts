export type WizardMode = "create" | "reconfigure";

export type WizardSubverticalTemplate = {
  key?: string;
  template_key?: string;
  title?: string;
  name?: string;
  content?: string;
};

export type WizardSubverticalProfile = {
  id?: string;
  name?: string;
  strength_score?: number;
  promise?: string;
  buyer?: string;
  growth_motion?: string;
  monetizes?: string[];
  qualification_questions?: string[];
  objections?: string[];
  service_bundle?: string[];
  automation_priorities?: string[];
  kpi_pack?: string[];
  launch_assets?: string[];
  recommended_commands?: string[];
  templates?: WizardSubverticalTemplate[];
};

export type WizardStep = {
  key: string;
  label?: string;
  required?: boolean;
  status?: string;
  completed?: boolean;
  payload?: Record<string, unknown>;
};

export type WizardRecommendedIntegration = {
  integration_key?: string;
  provider?: string;
  name?: string;
  required?: boolean;
  status?: string;
  integration_type?: string;
};

export type WizardRecommendedPlaybook = {
  key?: string;
  label?: string;
  priority?: number;
  goal?: string;
};

export type WizardRecommendedCta = {
  key?: string;
  label?: string;
  goal?: string;
};

export type WizardBlueprint = {
  wizard_version?: string;
  profile?: {
    id?: string;
    name?: string;
    short_name?: string;
    description?: string;
    problem?: string;
    recommended_integrations?: string[];
    subverticals?: string[];
    recommended_subverticals?: string[];
  };
  selected_subvertical?: WizardSubverticalProfile;
  steps?: WizardStep[];
  answers?: Record<string, Record<string, unknown>>;
  progress_percent?: number;
  current_step?: string | null;
  setup?: {
    services?: string[];
    faqs?: Array<{ q?: string; a?: string }>;
    personality?: { tone?: string; response_length?: string; sales_intensity?: string };
    objective?: { primary?: string };
    rules?: { escalate_when?: string[] };
    agenda?: Record<string, unknown>;
    followups?: Record<string, unknown>;
    handoff?: Record<string, unknown>;
    integrations?: Record<string, unknown>;
    business_knowledge?: { policies?: string[]; hours?: string };
    response_templates?: Array<Record<string, unknown>>;
    wizard?: {
      selected_subvertical?: string;
      recommended_integrations?: WizardRecommendedIntegration[];
      recommended_playbooks?: WizardRecommendedPlaybook[];
      recommended_ctas?: WizardRecommendedCta[];
      knowledge_sources?: Array<Record<string, unknown>>;
      featured_offers?: string[];
      pricing_notes?: string[];
      policies?: string[];
      launch_notes?: string[];
      autopublish_knowledge?: boolean;
      rule_overrides?: Record<string, unknown>;
      owner_user_id?: string | null;
      bot_id?: string | null;
    };
  };
  checklist?: Array<{ key?: string; label?: string; completed?: boolean }>;
};

export type WizardStepRun = {
  step_key: string;
  step_status?: string;
  payload?: Record<string, unknown>;
  is_required?: number;
  completed_at?: string | null;
};

export type WizardValidationChecklistItem = {
  key?: string;
  label?: string;
  status?: "green" | "yellow" | "red";
  detail?: string;
  blocking?: boolean;
};

export type WizardVerticalScorecardItem = {
  key?: string;
  label?: string;
  status?: "green" | "yellow" | "red";
  detail?: string;
  covered_signals?: string[];
  missing_signals?: string[];
};

export type WizardVerticalScorecard = {
  vertical_id?: string;
  label?: string;
  status?: "green" | "yellow" | "red";
  summary?: string;
  counts?: {
    green?: number;
    yellow?: number;
    red?: number;
  };
  items?: WizardVerticalScorecardItem[];
};

export type WizardValidationSnapshot = {
  generated_at?: string;
  source?: string;
  mode?: string;
  validation_hash?: string;
  apply_ready?: boolean;
  gate?: {
    status?: "green" | "yellow" | "red";
    label?: string;
    detail?: string;
  };
  counts?: {
    green?: number;
    yellow?: number;
    red?: number;
  };
  diff_summary?: Array<{
    key?: string;
    label?: string;
    status?: "replace" | "keep" | "suggest" | "add" | "remove";
    summary?: string;
    counters?: WizardDryRunCounters;
  }>;
  checklist?: WizardValidationChecklistItem[];
  simulation_result?: {
    status?: string;
    approved?: boolean;
    pass_rate?: number;
    cases_total?: number;
    created_at?: string | null;
    compare_target?: string;
    run_id?: string | null;
  };
  warnings?: WizardDryRunIssue[];
  next_cta?: {
    key?: string;
    title?: string;
    description?: string;
    cta_label?: string;
    href?: string;
  };
  scorecard?: WizardVerticalScorecard;
  exit_score?: {
    value?: number;
    label?: string;
    tone?: "success" | "warning" | "danger";
  };
};


export type WizardRuntimeDiagnostics = {
  first_incomplete_required_step?: string | null;
  required_steps_completed?: string[];
  required_steps_pending?: string[];
  can_update_up_to_step?: string | null;
  validation_snapshot_pending?: boolean;
  dry_run_pending?: boolean;
  last_event_type?: string | null;
  event_count?: number;
  step_statuses?: Array<{ key?: string; status?: string; completed?: boolean }>;
  stored_current_step?: string | null;
  computed_current_step?: string | null;
  stored_progress_percent?: number;
  computed_progress_percent?: number;
  stored_subvertical?: string | null;
  computed_subvertical?: string | null;
  integrity_signature?: string | null;
  integrity_mismatch?: boolean;
  integrity_mismatch_fields?: string[];
  step_run_drift?: {
    missing?: string[];
    mismatched?: string[];
    extra?: string[];
    count?: number;
  };
};

export type WizardInstance = {
  id: string;
  organization_id: string;
  bot_id?: string | null;
  vertical_id?: string;
  subvertical?: string | null;
  status?: string;
  current_step?: string | null;
  progress_percent?: number;
  business_name?: string;
  bot_name?: string;
  tone?: string;
  language?: string;
  timezone?: string;
  primary_objective?: string;
  answers?: Record<string, Record<string, unknown>>;
  setup?: WizardBlueprint["setup"];
  checklist?: WizardBlueprint["checklist"];
  step_runs?: WizardStepRun[];
  event_log?: Array<Record<string, unknown>>;
  applied_summary?: Record<string, unknown>;
  validation_snapshot?: WizardValidationSnapshot;
  wizard_revision?: number;
  diagnostics?: WizardRuntimeDiagnostics;
  created_at?: string;
  updated_at?: string;
  applied_at?: string | null;
};

export type WizardApplyResult = {
  wizard: WizardInstance;
  validation_snapshot?: WizardValidationSnapshot;
  behavior?: Record<string, unknown>;
  pack_result?: Record<string, unknown>;
  created_services?: string[];
  knowledge_documents?: string[];
  planned_integrations?: Array<Record<string, unknown>>;
  summary?: {
    vertical_id?: string;
    subvertical?: string;
    created_services?: string[];
    template_count?: number;
    knowledge_documents?: number;
    planned_integrations?: number;
    behavior_id?: string | null;
    pack_result?: Record<string, unknown>;
  };
};


export type WizardDryRunDiffItem = {
  key?: string;
  label?: string;
  status?: "replace" | "keep" | "suggest" | "add" | "remove";
  before?: string;
  after?: string;
  detail?: string;
};

export type WizardDryRunCounters = {
  added?: number;
  removed?: number;
  replaced?: number;
  kept?: number;
};

export type WizardDryRunDomainItem = {
  key?: string;
  label?: string;
  status?: "replace" | "keep" | "suggest" | "add" | "remove";
  before?: string;
  after?: string;
  detail?: string;
  counters?: WizardDryRunCounters;
  badges?: string[];
};

export type WizardDryRunDomain = {
  key?: string;
  label?: string;
  status?: "replace" | "keep" | "suggest" | "add" | "remove";
  summary?: string;
  detail?: string;
  counters?: WizardDryRunCounters;
  badges?: string[];
  items?: WizardDryRunDomainItem[];
};

export type WizardDryRunIssue = {
  key?: string;
  severity?: "blocking" | "high" | "medium" | "low";
  label?: string;
  detail?: string;
};

export type WizardDryRunChecklistItem = {
  key?: string;
  label?: string;
  completed?: boolean;
  required?: boolean;
};


export type WizardHandoffPreviewState = {
  escalate_when?: string[];
  handoff_keywords?: string[];
  expected_handoff_sla?: string;
  human_destination_channel?: string;
  rule_overrides?: Record<string, unknown>;
};

export type WizardHandoffPreview = {
  current?: WizardHandoffPreviewState;
  proposed?: WizardHandoffPreviewState;
};

export type WizardDryRunResult = {
  wizard: WizardInstance;
  validation_snapshot?: WizardValidationSnapshot;
  validation_hash?: string;
  diff_summary?: WizardDryRunDiffItem[];
  diff_domains?: WizardDryRunDomain[];
  handoff_preview?: WizardHandoffPreview;
  risks?: WizardDryRunIssue[];
  conflicts?: WizardDryRunIssue[];
  checklist?: WizardDryRunChecklistItem[];
  exit_score?: {
    value?: number;
    label?: string;
    tone?: "success" | "warning" | "danger";
  };
  summary?: {
    status?: string;
    mode?: string;
    snapshot_required?: boolean;
    apply_ready?: boolean;
    validated_at?: string;
    bot_id?: string | null;
    organization_id?: string | null;
  };
};

export type WizardIssue = {
  key?: string;
  code?: string;
  label?: string;
  detail?: string;
  message?: string;
  severity?: "blocking" | "high" | "medium" | "low" | "error" | "warning" | "info";
};

export type WizardError = {
  code?: string;
  error_code?: string;
  title?: string;
  detail?: string;
  message?: string;
  issues?: WizardIssue[];
};
