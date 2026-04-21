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

export type TalentVacancyContract = {
  id: string;
  title: string;
  status?: string;
  summary?: string;
  description?: string;
  requirements: string[];
  benefits: string[];
  location_label?: string;
  address?: string;
  modality?: string;
  work_days?: string;
  work_hours?: string;
  salary_visible: boolean;
  salary_min?: number | null;
  salary_max?: number | null;
  currency?: string;
  interview_schedule?: string;
  interview_location?: string;
  interview_notes?: string;
  documents_required: string[];
};

export type TalentCandidateContract = {
  id: string;
  contact_id: string;
  conversation_id?: string | null;
  vacancy_id?: string | null;
  vacancy_title?: string | null;
  status?: string;
  interview_confirmed_at?: string | null;
  updated_at?: string | null;
};

export type TalentOverviewContract = {
  bot_id: string;
  bot_name?: string;
  config: JsonMap;
  vacancies: TalentVacancyContract[];
  candidates: TalentCandidateContract[];
  summary: Record<string, unknown>;
};

export function normalizeTalentVacancy(raw: unknown): TalentVacancyContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    title: stringValue(record.title, 'Vacante'),
    status: stringOrNull(record.status) ?? undefined,
    summary: stringOrNull(record.summary) ?? undefined,
    description: stringOrNull(record.description) ?? undefined,
    requirements: stringList(record.requirements),
    benefits: stringList(record.benefits),
    location_label: stringOrNull(record.location_label) ?? undefined,
    address: stringOrNull(record.address) ?? undefined,
    modality: stringOrNull(record.modality) ?? undefined,
    work_days: stringOrNull(record.work_days) ?? undefined,
    work_hours: stringOrNull(record.work_hours) ?? undefined,
    salary_visible: booleanValue(record.salary_visible),
    salary_min: nullableNumber(record.salary_min),
    salary_max: nullableNumber(record.salary_max),
    currency: stringOrNull(record.currency) ?? undefined,
    interview_schedule: stringOrNull(record.interview_schedule) ?? undefined,
    interview_location: stringOrNull(record.interview_location) ?? undefined,
    interview_notes: stringOrNull(record.interview_notes) ?? undefined,
    documents_required: stringList(record.documents_required),
  };
}

export function normalizeTalentCandidate(raw: unknown): TalentCandidateContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    contact_id: stringValue(record.contact_id),
    conversation_id: stringOrNull(record.conversation_id),
    vacancy_id: stringOrNull(record.vacancy_id),
    vacancy_title: stringOrNull(record.vacancy_title),
    status: stringOrNull(record.status) ?? undefined,
    interview_confirmed_at: stringOrNull(record.interview_confirmed_at),
    updated_at: stringOrNull(record.updated_at),
  };
}

export function normalizeTalentOverview(raw: unknown): TalentOverviewContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    bot_id: stringValue(record.bot_id),
    bot_name: stringOrNull(record.bot_name) ?? undefined,
    config: asRecord(record.config),
    vacancies: asArray(record.vacancies).map(normalizeTalentVacancy).filter((item) => Boolean(item.id)),
    candidates: asArray(record.candidates).map(normalizeTalentCandidate).filter((item) => Boolean(item.id)),
    summary: asRecord(record.summary),
  };
}
