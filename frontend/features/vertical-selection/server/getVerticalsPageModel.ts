import { getStrongestVerticals, getVerticalCatalog, getVerticalProfile } from "@/app/lib/data/verticals";
import { safeText } from "@/app/lib/ui";
import type { VerticalProfileContract } from "@/app/lib/contracts/verticals";

export type VerticalsSearchParams = Record<string, string | string[] | undefined>;

export type SegmentedItem = { href: string; label: string; active: boolean };

export type VerticalsPageModel = {
  verticals: VerticalProfileContract[];
  strongestVerticals: VerticalProfileContract[];
  selected: VerticalProfileContract | null;
  profile: VerticalProfileContract | null;
  selectedSubvertical?: string;
  segmented: SegmentedItem[];
  subverticalSegmented: SegmentedItem[];
  rows: {
    pipelineRows: string[][];
    automationRows: string[][];
    dashboardRows: string[][];
    playbookRows: string[][];
    e2eRows: string[][];
    runtimeTransitionRows: string[][];
    pricingRuleRows: string[][];
    recurrenceRows: string[][];
    kpiFormulaRows: string[][];
    automationPolicyRows: string[][];
    v12CommandRows: string[][];
    v12EventRows: string[][];
    v12ViewRows: string[][];
  };
};

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function stringRows(items: unknown[][]): string[][] {
  return items.map((row) => row.map((cell) => safeText(String(cell ?? ""))));
}

export function tierLabel(value?: string) {
  switch (value) {
    case "tier_1": return "Tier 1";
    case "tier_2": return "Tier 2";
    case "tier_3_guarded": return "Tier 3 controlado";
    default: return safeText(value, "Sin tier");
  }
}

export function toneForTier(value?: string): "green" | "blue" | "gold" | "slate" {
  switch (value) {
    case "tier_1": return "green";
    case "tier_2": return "blue";
    case "tier_3_guarded": return "gold";
    default: return "slate";
  }
}

export function waveLabel(value?: string) {
  switch (value) {
    case "ola_1": return "Ola 1";
    case "ola_2": return "Ola 2";
    case "ola_3": return "Ola 3";
    default: return safeText(value, "Sin ola");
  }
}

export async function getVerticalsPageModel(searchParams?: VerticalsSearchParams): Promise<VerticalsPageModel> {
  const params = searchParams || {};
  const selectedVerticalId = first(params.vertical);
  const selectedSubvertical = first(params.subvertical);
  const [verticals, strongestVerticals] = await Promise.all([getVerticalCatalog(), getStrongestVerticals()]);
  const selected = verticals.find((item) => item.id === selectedVerticalId) || (verticals.length === 1 ? verticals[0] : null);

  if (!selected) {
    return {
      verticals,
      strongestVerticals,
      selected: null,
      profile: null,
      selectedSubvertical,
      segmented: [],
      subverticalSegmented: [],
      rows: {
        pipelineRows: [], automationRows: [], dashboardRows: [], playbookRows: [], e2eRows: [],
        runtimeTransitionRows: [], pricingRuleRows: [], recurrenceRows: [], kpiFormulaRows: [], automationPolicyRows: [],
        v12CommandRows: [], v12EventRows: [], v12ViewRows: [],
      },
    };
  }

  const profile = await getVerticalProfile(selected.id, undefined, selectedSubvertical);
  const segmented = verticals.map((item) => ({
    href: `/verticals?vertical=${encodeURIComponent(item.id)}`,
    label: safeText(item.name).replace(/^WAOS\s+/i, ""),
    active: item.id === selected.id,
  }));

  const subverticalSegmented = (profile.subvertical_profiles.length ? profile.subvertical_profiles : profile.subverticals.map((item) => ({ id: item.toLowerCase().replace(/[^a-z0-9]+/g, "-"), name: item }))).map((item) => ({
    href: `/verticals?vertical=${encodeURIComponent(profile.id)}&subvertical=${encodeURIComponent(item.name)}`,
    label: safeText(item.name),
    active: safeText(item.name).toLowerCase() === safeText(profile.selected_subvertical?.name).toLowerCase(),
  }));

  const pipelineRows = stringRows([
    ...(profile.pipeline.primary ? [[profile.pipeline.primary.name, profile.pipeline.primary.states.join(" • ") || "Sin estados"]] : []),
    ...profile.pipeline.secondary.map((item) => [item.name, item.states.join(" • ") || "Sin estados"]),
  ]);
  const automationRows = stringRows(profile.automation_sequences.map((item) => [item.name, item.trigger || "Sin trigger", item.goal || "Sin objetivo", item.steps.join(" • ") || "Sin pasos"]));
  const dashboardRows = stringRows(profile.dashboard.sections.map((section) => [section.name, section.metrics.join(" • ") || "Sin métricas"]));
  const playbookRows = stringRows(profile.subvertical_playbooks.map((item) => [item.name, item.focus || "Sin foco"]));
  const e2eRows = stringRows(profile.business_e2e_tests.map((item, index) => [`${index + 1}`, item.name, item.status || "Sin estado"]));
  const runtimeTransitionRows = stringRows(((profile.vertical_runtime.pipeline_machine.transitions as Array<Record<string, unknown>>) || []).map((item) => [item.from, item.to, item.trigger, item.business_effect]));
  const pricingRuleRows = stringRows(((profile.vertical_runtime.pricing_engine.rules as Array<Record<string, unknown>>) || []).map((item, index) => [`${index + 1}`, item.rule, item.effect]));
  const recurrenceRows = stringRows(((profile.vertical_runtime.recurrence_engine.policies as Array<Record<string, unknown>>) || []).map((item) => [item.type, item.interval_days, item.anchor]));
  const kpiFormulaRows = stringRows(((profile.vertical_runtime.kpi_engine.definitions as Array<Record<string, unknown>>) || []).map((item) => [item.name, item.formula]));
  const automationPolicyRows = stringRows(((profile.vertical_runtime.automation_engine.money_automation_policies as Array<Record<string, unknown>>) || []).map((item) => [item.trigger, ((item.actions as string[]) || []).join(" • "), item.goal]));
  const v12CommandRows = stringRows((profile.transactional_motor_v12.command_catalog || []).map((item, index) => [`${index + 1}`, item.command, item.writes, item.guard]));
  const v12EventRows = stringRows((profile.transactional_motor_v12.event_catalog || []).map((item, index) => [`${index + 1}`, item.event, ((item.updates as string[]) || []).join(" • "), item.next_action]));
  const v12ViewsRecord = profile.transactional_motor_v12.transaction_views as Record<string, unknown> || {};
  const v12ViewRows = stringRows(Object.entries(v12ViewsRecord).map(([name, value]) => [name, ((Array.isArray(value) ? value : []) as string[]).join(" • ")]));

  return {
    verticals,
    strongestVerticals,
    selected,
    profile,
    selectedSubvertical,
    segmented,
    subverticalSegmented,
    rows: { pipelineRows, automationRows, dashboardRows, playbookRows, e2eRows, runtimeTransitionRows, pricingRuleRows, recurrenceRows, kpiFormulaRows, automationPolicyRows, v12CommandRows, v12EventRows, v12ViewRows },
  };
}
