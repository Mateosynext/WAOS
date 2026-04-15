"use server";

import { redirect } from "next/navigation";
import { patchJson, postJson, readString, runAndRefresh } from "./shared";

function readBoolean(formData: FormData, key: string) {
  const value = String(formData.get(key) || "").toLowerCase();
  return ["on", "true", "1", "yes"].includes(value);
}

function splitList(value: string) {
  return value
    .split(/\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function readOptionalNumber(formData: FormData, key: string): number | null {
  const raw = readString(formData, key);
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

export async function updateTalentPolicyAction(formData: FormData) {
  const botId = readString(formData, "bot_id");
  const redirectTo = readString(formData, "redirect_to") || "/vacantes";
  await runAndRefresh(redirectTo, () => patchJson(`/api/v1/bots/${botId}/talent/policy`, {
    enabled: readBoolean(formData, "enabled"),
    vacancies_enabled: readBoolean(formData, "vacancies_enabled"),
    worker_recognition_enabled: readBoolean(formData, "worker_recognition_enabled"),
    never_silent: readBoolean(formData, "never_silent"),
    default_handoff_on_unknown: readBoolean(formData, "default_handoff_on_unknown"),
    no_schedule_message: readString(formData, "no_schedule_message"),
    worker_keywords: splitList(readString(formData, "worker_keywords")),
    worker_fallback_message: readString(formData, "worker_fallback_message"),
    route_worker_to_human: readBoolean(formData, "route_worker_to_human"),
    salary_hide_message: readString(formData, "salary_hide_message"),
  }));
  redirect(redirectTo);
}

export async function createTalentVacancyAction(formData: FormData) {
  const botId = readString(formData, "bot_id");
  const redirectTo = readString(formData, "redirect_to") || "/vacantes";
  await runAndRefresh(redirectTo, () => postJson(`/api/v1/bots/${botId}/talent/vacancies`, {
    title: readString(formData, "title"),
    status: readString(formData, "status") || "draft",
    summary: readString(formData, "summary"),
    description: readString(formData, "description"),
    requirements: splitList(readString(formData, "requirements")),
    benefits: splitList(readString(formData, "benefits")),
    location_label: readString(formData, "location_label"),
    address: readString(formData, "address"),
    modality: readString(formData, "modality") || "presencial",
    work_days: readString(formData, "work_days"),
    work_hours: readString(formData, "work_hours"),
    salary_visible: readBoolean(formData, "salary_visible"),
    salary_min: readOptionalNumber(formData, "salary_min"),
    salary_max: readOptionalNumber(formData, "salary_max"),
    currency: readString(formData, "currency") || "MXN",
    interview_slots_enabled: readBoolean(formData, "interview_slots_enabled"),
    interview_schedule: readString(formData, "interview_schedule"),
    interview_location: readString(formData, "interview_location"),
    interview_notes: readString(formData, "interview_notes"),
    documents_required: splitList(readString(formData, "documents_required")),
    faqs: [],
  }));
  redirect(redirectTo);
}

export async function confirmTalentCandidateAction(formData: FormData) {
  const botId = readString(formData, "bot_id");
  const redirectTo = readString(formData, "redirect_to") || "/vacantes";
  await runAndRefresh(redirectTo, () => postJson(`/api/v1/bots/${botId}/talent/candidates/confirm`, {
    contact_id: readString(formData, "contact_id"),
    conversation_id: readString(formData, "conversation_id") || null,
    vacancy_id: readString(formData, "vacancy_id") || null,
    vacancy_title: readString(formData, "vacancy_title") || null,
    notes: readString(formData, "notes"),
  }));
  redirect(redirectTo);
}
