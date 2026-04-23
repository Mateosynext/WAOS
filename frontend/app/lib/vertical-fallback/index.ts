import "server-only";
import indexData from "./index.json";
import { normalizeVerticalProfile, type VerticalProfileContract } from "../contracts/verticals";

type VerticalFallbackIndexEntry = {
  id: string;
  name?: string;
  short_name?: string;
  aliases: string[];
  is_strongest_vertical?: boolean;
  strongest_rank?: number;
  file: string;
};

const FALLBACK_INDEX = indexData as VerticalFallbackIndexEntry[];
const profileCache = new Map<string, VerticalProfileContract>();

const profileLoaders: Record<string, () => Promise<unknown>> = {
  fitness: () => import("./profiles/fitness.json").then((module) => module.default),
  dental: () => import("./profiles/dental.json").then((module) => module.default),
  aesthetic: () => import("./profiles/aesthetic.json").then((module) => module.default),
  vet: () => import("./profiles/vet.json").then((module) => module.default),
  "real-estate": () => import("./profiles/real-estate.json").then((module) => module.default),
  "auto-service": () => import("./profiles/auto-service.json").then((module) => module.default),
  education: () => import("./profiles/education.json").then((module) => module.default),
  beauty: () => import("./profiles/beauty.json").then((module) => module.default),
  "field-services": () => import("./profiles/field-services.json").then((module) => module.default),
  "professional-intake": () => import("./profiles/professional-intake.json").then((module) => module.default),
  commerce: () => import("./profiles/commerce.json").then((module) => module.default),
  "waos-bot": () => import("./profiles/waos-bot.json").then((module) => module.default),
};

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function normalizeName(value: string | null | undefined): string {
  return String(value || "").trim().toLowerCase();
}

function validateIndex(): void {
  const seen = new Set<string>();
  for (const entry of FALLBACK_INDEX) {
    if (!entry.id) {
      throw new Error("Fallback vertical index contains an entry without id");
    }
    if (seen.has(entry.id)) {
      throw new Error(`Fallback vertical index contains duplicate id: ${entry.id}`);
    }
    if (!profileLoaders[entry.id]) {
      throw new Error(`Fallback vertical index points to a missing loader: ${entry.id}`);
    }
    seen.add(entry.id);
  }
}

validateIndex();

async function loadProfileById(id: string): Promise<VerticalProfileContract> {
  const cached = profileCache.get(id);
  if (cached) return cached;
  const loader = profileLoaders[id];
  if (!loader) {
    throw new Error(`Unknown fallback vertical profile: ${id}`);
  }
  const normalized = normalizeVerticalProfile(await loader());
  if (!normalized.id) {
    throw new Error(`Fallback vertical profile ${id} did not normalize into a valid profile`);
  }
  profileCache.set(id, normalized);
  return normalized;
}

function findIndexEntry(vertical?: string): VerticalFallbackIndexEntry {
  const key = normalizeName(vertical);
  return FALLBACK_INDEX.find((entry) => {
    return !key || entry.aliases.some((candidate) => normalizeName(candidate) === key);
  }) || FALLBACK_INDEX[0];
}

function applySubverticalSelection(profile: VerticalProfileContract, subvertical?: string): VerticalProfileContract {
  const selected = clone(profile);
  const subKey = normalizeName(subvertical);
  if (!subKey) return selected;
  const selectedSubvertical = selected.subvertical_profiles.find((item) => normalizeName(item.name) === subKey)
    || selected.selected_subvertical
    || selected.subvertical_profiles[0]
    || (selected.subverticals.find((item) => normalizeName(item) === subKey)
      ? {
          id: subvertical || "subvertical",
          name: subvertical || "Subvertical",
          templates: [],
          monetizes: [],
          service_bundle: [],
          qualification_questions: [],
          objections: [],
          automation_priorities: [],
          kpi_pack: [],
          recommended_commands: [],
          launch_assets: [],
        }
      : undefined);
  if (selectedSubvertical) {
    selected.selected_subvertical = clone(selectedSubvertical as typeof selected.selected_subvertical);
  }
  return selected;
}

export async function getFallbackVerticalCatalog(topOnly = false): Promise<VerticalProfileContract[]> {
  const targetEntries = topOnly
    ? (() => {
        const strongest = FALLBACK_INDEX
          .filter((entry) => entry.is_strongest_vertical)
          .sort((a, b) => (a.strongest_rank || 999) - (b.strongest_rank || 999));
        return strongest.length ? strongest : FALLBACK_INDEX.slice(0, 5);
      })()
    : FALLBACK_INDEX;
  const loaded = await Promise.all(targetEntries.map((entry) => loadProfileById(entry.id)));
  return loaded.map((item) => clone(item));
}

export async function getFallbackVerticalProfile(vertical?: string, subvertical?: string): Promise<VerticalProfileContract> {
  const entry = findIndexEntry(vertical);
  const profile = await loadProfileById(entry.id);
  return applySubverticalSelection(profile, subvertical);
}
