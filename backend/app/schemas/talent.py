from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TalentPolicyRequest(BaseModel):
    enabled: bool = True
    vacancies_enabled: bool = True
    worker_recognition_enabled: bool = True
    never_silent: bool = True
    default_handoff_on_unknown: bool = False
    no_schedule_message: str = "Por ahora no cuento con horarios definidos para entrevista. En cuanto estén disponibles te lo confirmaremos."
    worker_keywords: list[str] = Field(default_factory=list)
    worker_fallback_message: str = "Gracias por escribir. Ya detecté que hablas como parte del equipo. Te ayudaremos a canalizar esto con RH o con la persona responsable."
    route_worker_to_human: bool = True
    salary_hide_message: str = "El sueldo se comparte durante el proceso de selección."


class TalentVacancyRequest(BaseModel):
    title: str
    status: str = "draft"
    summary: str = ""
    description: str = ""
    requirements: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    location_label: str = ""
    address: str = ""
    modality: str = "presencial"
    work_days: str = ""
    work_hours: str = ""
    salary_visible: bool = False
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str = "MXN"
    interview_slots_enabled: bool = False
    interview_schedule: str = ""
    interview_location: str = ""
    interview_notes: str = ""
    documents_required: list[str] = Field(default_factory=list)
    faqs: list[dict[str, Any]] = Field(default_factory=list)


class TalentCandidateConfirmRequest(BaseModel):
    contact_id: str
    conversation_id: str | None = None
    vacancy_id: str | None = None
    vacancy_title: str | None = None
    notes: str = ""
