import {
  asArray,
  asRecord,
  booleanOrNull,
  booleanValue,
  JsonMap,
  nullableNumber,
  numberOrNull,
  numberValue,
  pickString,
  pickTimestamp,
  stringList,
  stringOrNull,
  stringValue,
  unwrapApiEnvelope,
} from "./shared";

export type VerticalBuyerContract = {
  primary?: string;
  secondary: string[];
};

export type VerticalOnePagerContract = {
  headline?: string;
  thesis?: string;
  problem?: string;
  promise?: string;
  monetizes: string[];
  packaging: string[];
  strategic_care?: string;
};

export type VerticalNativeObjectsContract = {
  core: string[];
  commercial: string[];
  operations: string[];
};

export type VerticalPipelineStageContract = {
  name: string;
  states: string[];
};

export type VerticalPipelineContract = {
  primary?: VerticalPipelineStageContract;
  secondary: VerticalPipelineStageContract[];
};

export type VerticalBotPlaybookContract = {
  must_do: string[];
  must_ask: string[];
  objections: string[];
  escalate_when: string[];
  forbidden: string[];
  success_signals: string[];
};

export type VerticalAutomationSequenceContract = {
  key: string;
  name: string;
  trigger?: string;
  goal?: string;
  steps: string[];
};

export type VerticalDashboardSectionContract = {
  name: string;
  metrics: string[];
};

export type VerticalDashboardContract = {
  north_star?: string;
  sections: VerticalDashboardSectionContract[];
};

export type VerticalHardeningModelContract = {
  goal?: string;
  wave?: string;
  entity_queen?: string;
  reusable_modules: string[];
  minimum_viable_hardening: string[];
  hard_checklist: string[];
};

export type VerticalSpecialistLayersContract = {
  persistent_entities: string[];
  business_pipeline: JsonMap;
  pricing_and_quotes: string[];
  agenda_and_resources: string[];
  post_sale_and_recurrence: string[];
  documents_compliance: string[];
  kpis_that_matter: string[];
  money_automations: string[];
};

export type VerticalDomainContractContract = {
  vertical_entity_types: string[];
  vertical_pipeline_stages: JsonMap;
  vertical_quote_types: string[];
  vertical_resource_types: string[];
  vertical_followup_policies: string[];
  vertical_kpi_definitions: string[];
  vertical_playbooks: string[];
  vertical_document_types: string[];
};

export type VerticalNamedFocusContract = {
  name: string;
  focus?: string;
  status?: string;
};

export type VerticalRuntimeContract = {
  pipeline_machine: JsonMap;
  pricing_engine: JsonMap;
  resource_capacity: JsonMap;
  recurrence_engine: JsonMap;
  kpi_engine: JsonMap;
  automation_engine: JsonMap;
  document_flow: JsonMap;
  matching_engine: JsonMap;
};

export type VerticalTransactionalMotorV12Contract = {
  version?: string;
  aggregate_root?: string;
  main_business_entity?: string;
  transaction_unit?: string;
  system_of_record: JsonMap;
  transaction_primitives: JsonMap;
  aggregates: JsonMap;
  orchestration: JsonMap;
  finance: JsonMap;
  operations: JsonMap;
  audit_compliance: JsonMap;
  transaction_views: JsonMap;
  command_catalog: JsonMap[];
  event_catalog: JsonMap[];
};



export type VerticalSubverticalProfileContract = {
  id: string;
  name: string;
  strength_score?: number;
  promise?: string;
  growth_motion?: string;
  buyer?: string;
  monetizes: string[];
  service_bundle: string[];
  qualification_questions: string[];
  objections: string[];
  automation_priorities: string[];
  kpi_pack: string[];
  recommended_commands: string[];
  launch_assets: string[];
  templates: JsonMap[];
};

export type VerticalRuntimeConnectionContract = {
  active_vertical?: string;
  active_subvertical?: string;
  pack_status: JsonMap;
  surface_focus: JsonMap;
};

export type VerticalProfileContract = {
  id: string;
  name: string;
  short_name?: string;
  description?: string;
  problem?: string;
  portfolio_tier?: string;
  master_thesis?: string;
  subverticals: string[];
  objects: string[];
  flows: string[];
  kpis: string[];
  recommended_integrations: string[];
  buyer: VerticalBuyerContract;
  one_pager: VerticalOnePagerContract;
  demo_flow: string[];
  native_objects: VerticalNativeObjectsContract;
  pipeline: VerticalPipelineContract;
  bot_playbook: VerticalBotPlaybookContract;
  automation_sequences: VerticalAutomationSequenceContract[];
  dashboard: VerticalDashboardContract;
  hardening_model: VerticalHardeningModelContract;
  specialist_layers: VerticalSpecialistLayersContract;
  domain_contract: VerticalDomainContractContract;
  vertical_runtime: VerticalRuntimeContract;
  transactional_motor_v12: VerticalTransactionalMotorV12Contract;
  subvertical_playbooks: VerticalNamedFocusContract[];
  business_e2e_tests: VerticalNamedFocusContract[];
  is_strongest_vertical?: boolean;
  strongest_rank?: number;
  ten_x_score?: number;
  ten_x_narrative?: string;
  ten_x_growth_loops: string[];
  recommended_subverticals: string[];
  ten_x_operational_pack: JsonMap;
  subvertical_profiles: VerticalSubverticalProfileContract[];
  selected_subvertical?: VerticalSubverticalProfileContract;
  runtime_connection?: VerticalRuntimeConnectionContract;
};

function normalizeVerticalBuyer(raw: unknown): VerticalBuyerContract {
  const record = asRecord(raw);
  return {
    primary: stringOrNull(record.primary) ?? undefined,
    secondary: stringList(record.secondary),
  };
}

function normalizeVerticalOnePager(raw: unknown): VerticalOnePagerContract {
  const record = asRecord(raw);
  return {
    headline: stringOrNull(record.headline) ?? undefined,
    thesis: stringOrNull(record.thesis) ?? undefined,
    problem: stringOrNull(record.problem) ?? undefined,
    promise: stringOrNull(record.promise) ?? undefined,
    monetizes: stringList(record.monetizes),
    packaging: stringList(record.packaging),
    strategic_care: stringOrNull(record.strategic_care) ?? undefined,
  };
}

function normalizeVerticalNativeObjects(raw: unknown): VerticalNativeObjectsContract {
  const record = asRecord(raw);
  return {
    core: stringList(record.core),
    commercial: stringList(record.commercial),
    operations: stringList(record.operations),
  };
}

function normalizeVerticalPipelineStage(raw: unknown): VerticalPipelineStageContract {
  const record = asRecord(raw);
  return {
    name: pickString(record, ["name", "title"], "Pipeline"),
    states: stringList(record.states),
  };
}

function normalizeVerticalPipeline(raw: unknown): VerticalPipelineContract {
  const record = asRecord(raw);
  const primaryRecord = asRecord(record.primary);
  return {
    primary: Object.keys(primaryRecord).length ? normalizeVerticalPipelineStage(primaryRecord) : undefined,
    secondary: asArray(record.secondary).map(normalizeVerticalPipelineStage),
  };
}

function normalizeVerticalBotPlaybook(raw: unknown): VerticalBotPlaybookContract {
  const record = asRecord(raw);
  return {
    must_do: stringList(record.must_do),
    must_ask: stringList(record.must_ask),
    objections: stringList(record.objections),
    escalate_when: stringList(record.escalate_when),
    forbidden: stringList(record.forbidden),
    success_signals: stringList(record.success_signals),
  };
}

function normalizeVerticalAutomationSequence(raw: unknown): VerticalAutomationSequenceContract {
  const record = asRecord(raw);
  return {
    key: stringValue(record.key),
    name: pickString(record, ["name", "title"], "Secuencia"),
    trigger: stringOrNull(record.trigger) ?? undefined,
    goal: stringOrNull(record.goal) ?? undefined,
    steps: stringList(record.steps),
  };
}

function normalizeVerticalDashboard(raw: unknown): VerticalDashboardContract {
  const record = asRecord(raw);
  return {
    north_star: stringOrNull(record.north_star) ?? undefined,
    sections: asArray(record.sections).map((item) => {
      const section = asRecord(item);
      return {
        name: pickString(section, ["name", "title"], "Métricas"),
        metrics: stringList(section.metrics),
      };
    }),
  };
}

function normalizeVerticalHardeningModel(raw: unknown): VerticalHardeningModelContract {
  const record = asRecord(raw);
  return {
    goal: stringOrNull(record.goal) ?? undefined,
    wave: stringOrNull(record.wave) ?? undefined,
    entity_queen: stringOrNull(record.entity_queen) ?? undefined,
    reusable_modules: stringList(record.reusable_modules),
    minimum_viable_hardening: stringList(record.minimum_viable_hardening),
    hard_checklist: stringList(record.hard_checklist),
  };
}

function normalizeVerticalSpecialistLayers(raw: unknown): VerticalSpecialistLayersContract {
  const record = asRecord(raw);
  return {
    persistent_entities: stringList(record.persistent_entities),
    business_pipeline: asRecord(record.business_pipeline),
    pricing_and_quotes: stringList(record.pricing_and_quotes),
    agenda_and_resources: stringList(record.agenda_and_resources),
    post_sale_and_recurrence: stringList(record.post_sale_and_recurrence),
    documents_compliance: stringList(record.documents_compliance),
    kpis_that_matter: stringList(record.kpis_that_matter),
    money_automations: stringList(record.money_automations),
  };
}

function normalizeVerticalDomainContract(raw: unknown): VerticalDomainContractContract {
  const record = asRecord(raw);
  return {
    vertical_entity_types: stringList(record.vertical_entity_types),
    vertical_pipeline_stages: asRecord(record.vertical_pipeline_stages),
    vertical_quote_types: stringList(record.vertical_quote_types),
    vertical_resource_types: stringList(record.vertical_resource_types),
    vertical_followup_policies: stringList(record.vertical_followup_policies),
    vertical_kpi_definitions: stringList(record.vertical_kpi_definitions),
    vertical_playbooks: stringList(record.vertical_playbooks),
    vertical_document_types: stringList(record.vertical_document_types),
  };
}

function normalizeVerticalRuntime(raw: unknown): VerticalRuntimeContract {
  const record = asRecord(raw);
  return {
    pipeline_machine: asRecord(record.pipeline_machine),
    pricing_engine: asRecord(record.pricing_engine),
    resource_capacity: asRecord(record.resource_capacity),
    recurrence_engine: asRecord(record.recurrence_engine),
    kpi_engine: asRecord(record.kpi_engine),
    automation_engine: asRecord(record.automation_engine),
    document_flow: asRecord(record.document_flow),
    matching_engine: asRecord(record.matching_engine),
  };
}

function normalizeVerticalTransactionalMotorV12(raw: unknown): VerticalTransactionalMotorV12Contract {
  const record = asRecord(raw);
  return {
    version: stringOrNull(record.version) ?? undefined,
    aggregate_root: stringOrNull(record.aggregate_root) ?? undefined,
    main_business_entity: stringOrNull(record.main_business_entity) ?? undefined,
    transaction_unit: stringOrNull(record.transaction_unit) ?? undefined,
    system_of_record: asRecord(record.system_of_record),
    transaction_primitives: asRecord(record.transaction_primitives),
    aggregates: asRecord(record.aggregates),
    orchestration: asRecord(record.orchestration),
    finance: asRecord(record.finance),
    operations: asRecord(record.operations),
    audit_compliance: asRecord(record.audit_compliance),
    transaction_views: asRecord(record.transaction_views),
    command_catalog: asArray(record.command_catalog).map((item) => asRecord(item)),
    event_catalog: asArray(record.event_catalog).map((item) => asRecord(item)),
  };
}



function normalizeVerticalSubverticalProfile(raw: unknown): VerticalSubverticalProfileContract {
  const record = asRecord(raw);
  return {
    id: pickString(record, ["id", "slug", "name"], "subvertical"),
    name: pickString(record, ["name", "title"], "Subvertical"),
    strength_score: numberOrNull(record.strength_score) ?? undefined,
    promise: stringOrNull(record.promise) ?? undefined,
    growth_motion: stringOrNull(record.growth_motion) ?? undefined,
    buyer: stringOrNull(record.buyer) ?? undefined,
    monetizes: stringList(record.monetizes),
    service_bundle: stringList(record.service_bundle),
    qualification_questions: stringList(record.qualification_questions),
    objections: stringList(record.objections),
    automation_priorities: stringList(record.automation_priorities),
    kpi_pack: stringList(record.kpi_pack),
    recommended_commands: stringList(record.recommended_commands),
    launch_assets: stringList(record.launch_assets),
    templates: asArray(record.templates).map((item) => asRecord(item)),
  };
}

function normalizeVerticalNamedFocus(raw: unknown): VerticalNamedFocusContract {
  const record = asRecord(raw);
  return {
    name: pickString(record, ["name", "title"], "Elemento"),
    focus: stringOrNull(record.focus) ?? undefined,
    status: stringOrNull(record.status) ?? undefined,
  };
}

export function normalizeVerticalProfile(raw: unknown): VerticalProfileContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    name: pickString(record, ["name", "title"], "Vertical"),
    short_name: stringOrNull(record.short_name) ?? undefined,
    description: stringOrNull(record.description) ?? undefined,
    problem: stringOrNull(record.problem) ?? undefined,
    portfolio_tier: stringOrNull(record.portfolio_tier) ?? undefined,
    master_thesis: stringOrNull(record.master_thesis) ?? undefined,
    subverticals: stringList(record.subverticals),
    objects: stringList(record.objects),
    flows: stringList(record.flows),
    kpis: stringList(record.kpis),
    recommended_integrations: stringList(record.recommended_integrations),
    buyer: normalizeVerticalBuyer(record.buyer),
    one_pager: normalizeVerticalOnePager(record.one_pager),
    demo_flow: stringList(record.demo_flow),
    native_objects: normalizeVerticalNativeObjects(record.native_objects),
    pipeline: normalizeVerticalPipeline(record.pipeline),
    bot_playbook: normalizeVerticalBotPlaybook(record.bot_playbook),
    automation_sequences: asArray(record.automation_sequences).map(normalizeVerticalAutomationSequence),
    dashboard: normalizeVerticalDashboard(record.dashboard),
    hardening_model: normalizeVerticalHardeningModel(record.hardening_model),
    specialist_layers: normalizeVerticalSpecialistLayers(record.specialist_layers),
    domain_contract: normalizeVerticalDomainContract(record.domain_contract),
    vertical_runtime: normalizeVerticalRuntime(record.vertical_runtime),
    transactional_motor_v12: normalizeVerticalTransactionalMotorV12(record.transactional_motor_v12),
    subvertical_playbooks: asArray(record.subvertical_playbooks).map(normalizeVerticalNamedFocus),
    business_e2e_tests: asArray(record.business_e2e_tests).map(normalizeVerticalNamedFocus),
    is_strongest_vertical: booleanOrNull(record.is_strongest_vertical) ?? undefined,
    strongest_rank: numberOrNull(record.strongest_rank) ?? undefined,
    ten_x_score: numberOrNull(record.ten_x_score) ?? undefined,
    ten_x_narrative: stringOrNull(record.ten_x_narrative) ?? undefined,
    ten_x_growth_loops: stringList(record.ten_x_growth_loops),
    recommended_subverticals: stringList(record.recommended_subverticals),
    ten_x_operational_pack: asRecord(record.ten_x_operational_pack),
    subvertical_profiles: asArray(record.subvertical_profiles).map(normalizeVerticalSubverticalProfile),
    selected_subvertical: Object.keys(asRecord(record.selected_subvertical)).length ? normalizeVerticalSubverticalProfile(record.selected_subvertical) : undefined,
    runtime_connection: Object.keys(asRecord(record.runtime_connection)).length ? {
      active_vertical: stringOrNull(asRecord(record.runtime_connection).active_vertical) ?? undefined,
      active_subvertical: stringOrNull(asRecord(record.runtime_connection).active_subvertical) ?? undefined,
      pack_status: asRecord(asRecord(record.runtime_connection).pack_status),
      surface_focus: asRecord(asRecord(record.runtime_connection).surface_focus),
    } : undefined,
  };
}
