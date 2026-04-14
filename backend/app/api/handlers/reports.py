from __future__ import annotations

from .common import *
from .common import _require_permission

def list_executive_report_jobs(organization_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> dict[str, Any]:
    if organization_id:
        ensure_org_access(user, organization_id)
    with get_connection() as conn:
        return ok(list_report_generation_jobs(conn, organization_id=organization_id), meta={"organization_id": organization_id})

def queue_executive_report(payload: ExecutiveReportRequest, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "insights.read")
    with get_connection() as conn:
        job = queue_executive_report_generation(
            conn,
            organization_id=payload.organization_id,
            period_start=payload.period_start,
            period_end=payload.period_end,
            bot_id=payload.bot_id,
            delivery_channels=payload.delivery_channels,
            requested_by_user_id=user.get("id"),
        )
        return ok(job, meta={"queued": True})

def create_executive_report(payload: ExecutiveReportRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "insights.read")
    with get_connection() as conn:
        return generate_executive_report(conn, **payload.model_dump())

def list_executive_reports(
    organization_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        rows = fetch_all(conn, f"SELECT * FROM executive_reports {where_sql} ORDER BY generated_at DESC LIMIT 50", params)
        return [{**row, "summary": from_json(row.get("summary_json"), {}), "delivery_channels": from_json(row.get("delivery_channels_json"), [])} for row in rows]

def download_executive_report_pdf(report_id: str, user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        report = fetch_one(conn, "SELECT * FROM executive_reports WHERE id = ?", (report_id,))
        if not report:
            raise HTTPException(status_code=404, detail="report_not_found")
        ensure_org_access(user, report["organization_id"])
        pdf_path = report.get("pdf_path")
        if not pdf_path or not Path(pdf_path).exists():
            report = ensure_executive_report_pdf(conn, report)
            pdf_path = report.get("pdf_path")
        return FileResponse(pdf_path, media_type="application/pdf", filename=report.get("pdf_filename") or f"waos-report-{report_id}.pdf")

def report_schedules_list(organization_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        rows = fetch_all(conn, f"SELECT * FROM report_schedules {where_sql} ORDER BY next_run_at ASC", params)
        return [{**row, "delivery_channels": from_json(row.get("delivery_channels_json"), []), "config": from_json(row.get("config_json"), {})} for row in rows]

def report_schedules_create(payload: ReportScheduleRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    with get_connection() as conn:
        row_id = new_id("rsch")
        now = utcnow_iso()
        execute(conn, "INSERT INTO report_schedules (id, organization_id, bot_id, name, frequency, next_run_at, delivery_channels_json, status, config_json, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (row_id, payload.organization_id, payload.bot_id, payload.name, payload.frequency, payload.next_run_at, to_json(payload.delivery_channels), payload.status, to_json(payload.config), user["id"], now, now))
        return fetch_one(conn, "SELECT * FROM report_schedules WHERE id = ?", (row_id,))

def report_schedule_runs_all(organization_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        rows = fetch_all(conn, f"SELECT * FROM report_schedule_runs {where_sql} ORDER BY created_at DESC LIMIT 100", params)
        return [{**row, "metadata": from_json(row.get("metadata_json"), {})} for row in rows]

def report_schedule_runs_list(schedule_id: str, user: dict = Depends(get_current_user)) -> list[dict]:
    with get_connection() as conn:
        schedule = fetch_one(conn, "SELECT * FROM report_schedules WHERE id = ?", (schedule_id,))
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        ensure_org_access(user, schedule["organization_id"])
        rows = fetch_all(conn, "SELECT * FROM report_schedule_runs WHERE schedule_id = ? ORDER BY created_at DESC", (schedule_id,))
        return [{**row, "metadata": from_json(row.get("metadata_json"), {})} for row in rows]
