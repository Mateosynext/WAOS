from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ALLOW_SQLITE_FOR_TESTS", "true")

from backend.app.db import SCHEMA_PATH
from backend.app.talent_runtime import (
    confirm_candidate,
    detect_talent_intent,
    ensure_talent_schema,
    generate_talent_reply,
    normalize_talent_config,
)


def _conn():
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    conn = sqlite3.connect(tmp.name)
    conn.row_factory = sqlite3.Row
    conn.executescript(Path(SCHEMA_PATH).read_text())
    ensure_talent_schema(conn)
    return conn, tmp.name


def _bot_config():
    return {
        "talent": normalize_talent_config(
            {
                "enabled": True,
                "vacancies": [
                    {
                        "id": "vac_cashier",
                        "title": "Cajero",
                        "status": "active",
                        "summary": "atender caja y clientes",
                        "requirements": ["secundaria", "experiencia en caja"],
                        "location_label": "Sucursal Centro",
                        "work_days": "Lun a Vie",
                        "work_hours": "9:00 a 18:00",
                        "salary_visible": True,
                        "salary_min": 8000,
                        "salary_max": 10000,
                        "currency": "MXN",
                        "interview_schedule": "Miércoles 10:30 am",
                        "interview_location": "Sucursal Centro",
                    }
                ],
            }
        )
    }


def test_detects_candidate_and_worker_intents() -> None:
    bot_config = _bot_config()
    classification = detect_talent_intent("Me interesa la vacante de cajero, cuanto pagan?", {}, bot_config)
    assert classification is not None
    assert classification["intent"] == "job_salary"
    assert classification["vacancy_id"] == "vac_cashier"

    worker = detect_talent_intent("Hola, soy empleado y necesito ver mi turno", {}, bot_config)
    assert worker is not None
    assert worker["intent"] == "worker_schedule"
    assert worker["profile_type"] == "worker"


def test_generates_interview_and_salary_replies() -> None:
    bot_config = _bot_config()
    reply = generate_talent_reply("", {"intent": "job_interview_details", "vacancy_id": "vac_cashier"}, bot_config, {})
    assert "Miércoles 10:30 am" in reply
    salary = generate_talent_reply("", {"intent": "job_salary", "vacancy_id": "vac_cashier"}, bot_config, {})
    assert "8000" in salary and "10000" in salary


def test_registers_confirmed_candidate() -> None:
    conn, name = _conn()
    try:
        created = confirm_candidate(
            conn,
            organization_id="org_1",
            bot_id="bot_1",
            conversation_id="conv_1",
            contact_id="contact_1",
            vacancy_id="vac_cashier",
            vacancy_title="Cajero",
            profile={"source": "test"},
        )
        assert created["contact_id"] == "contact_1"
        same = confirm_candidate(
            conn,
            organization_id="org_1",
            bot_id="bot_1",
            conversation_id="conv_1",
            contact_id="contact_1",
            vacancy_id="vac_cashier",
            vacancy_title="Cajero",
            profile={"source": "test-2"},
        )
        rows = conn.execute("SELECT COUNT(*) AS total FROM talent_candidates").fetchone()
        assert rows["total"] == 1
        assert same["id"] == created["id"]
    finally:
        conn.close()
        Path(name).unlink(missing_ok=True)
