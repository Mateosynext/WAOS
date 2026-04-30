from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_automation_jobs_link_to_outbox_and_do_not_complete_on_dispatch():
    worker = read("backend/worker.py")
    assert "outbox_message_id" in worker
    assert '"automation_job_id": job["id"]' in worker
    assert 'status="dispatch_queued"' in worker
    assert "Automation job dispatch queued" in worker
    assert "mark_job_completed(conn, dedupe_key=dedupe_key, result={\"message_id\"" not in worker
    assert "callback_type=\"job.executed\"" not in worker


def test_provider_truth_drives_final_job_lifecycle():
    worker = read("backend/worker.py")
    assert "def _sync_automation_job_from_outbox" in worker
    assert "SET status = 'provider_sending'" in worker
    assert "SET status = 'provider_sent'" in worker
    assert "SET status = 'provider_failed'" in worker
    assert "SET status = 'dead_letter'" in worker
    assert "callback_type=\"job.provider_sent\"" in worker
    assert "callback_type=\"job.provider_failed\"" in worker


def test_schema_migrates_automation_job_outbox_pointer():
    runtime_schema = read("backend/app/runtime_schema_migration.py")
    migrations = read("backend/app/migrations.py")
    assert "('automation_jobs', 'outbox_message_id', 'TEXT')" in runtime_schema
    assert "_migration_phase34_automation_job_outbox_lifecycle" in migrations
    assert "idx_automation_jobs_outbox_message" in migrations


def test_manual_api_process_uses_worker_lifecycle():
    handler = read("backend/app/api/handlers/automations.py")
    assert "from worker import process_due_jobs as worker_process_due_jobs" in handler
    assert "worker_process_due_jobs()" in handler
    assert "status=\"simulated\"" not in handler
    assert "UPDATE automation_jobs SET status = 'executed'" not in handler
