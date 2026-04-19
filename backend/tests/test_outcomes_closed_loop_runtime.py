from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.tests.test_activation_foundations import _auth_headers


client = TestClient(app)


def _seed_headers() -> dict[str, str]:
    return _auth_headers()


def test_outcomes_closed_loop_records_exposures_attributes_real_outcomes_and_builds_scorecards() -> None:
    headers = _seed_headers()

    exposure_v1 = client.post(
        "/api/v1/outcomes/exposures",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "conversation_id": "conv_activation",
            "contact_id": "ct_activation",
            "lead_id": "lead_activation",
            "appointment_id": "apt_activation",
            "payment_id": "pay_activation",
            "source_type": "assistant_message",
            "prompt_run_id": "prun_v1",
            "prompt_version_id": "prompt_v1",
            "flow_id": "flow_booking",
            "flow_version_id": "flow_booking_v1",
            "template_id": "tpl_booking",
            "template_version_id": "tpl_booking_v1",
            "routing_rule_id": None,
            "decision_path_id": "decision_sales_v1",
            "handoff_id": "handoff_sales_v1",
            "handoff_kind": "human_assist",
            "vertical": "fitness",
            "funnel_stage": "booking",
            "metadata": {"template_name": "appointment_reminder"},
            "sent_at": "2026-04-02T09:00:00Z",
        },
    )
    assert exposure_v1.status_code == 200
    assert exposure_v1.json()["data"]["prompt_run_id"] == "prun_v1"

    no_show_event = client.post(
        "/api/v1/outcomes/events",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "conversation_id": "conv_activation",
            "contact_id": "ct_activation",
            "lead_id": "lead_activation",
            "appointment_id": "apt_activation",
            "event_name": "appointment_no_show",
            "event_category": "attendance",
            "event_timestamp": "2026-04-02T12:00:00Z",
            "source_system": "appointments",
            "vertical": "fitness",
            "funnel_stage": "attendance",
        },
    )
    assert no_show_event.status_code == 200
    assert no_show_event.json()["data"]["attribution"]["facts_created"] >= 1

    exposure_v2 = client.post(
        "/api/v1/outcomes/exposures",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "conversation_id": "conv_activation",
            "contact_id": "ct_activation",
            "lead_id": "lead_activation",
            "appointment_id": "apt_activation",
            "payment_id": "pay_activation",
            "source_type": "assistant_message",
            "prompt_run_id": "prun_v2",
            "prompt_version_id": "prompt_v2",
            "flow_id": "flow_reactivation",
            "flow_version_id": "flow_reactivation_v2",
            "template_id": "tpl_reactivation",
            "template_version_id": "tpl_reactivation_v2",
            "decision_path_id": "decision_sales_v2",
            "handoff_id": "handoff_sales_v2",
            "handoff_kind": "resolved_by_ai",
            "vertical": "fitness",
            "funnel_stage": "reactivation",
            "metadata": {"variant": "B"},
            "sent_at": "2026-04-03T09:00:00Z",
        },
    )
    assert exposure_v2.status_code == 200
    assert exposure_v2.json()["data"]["prompt_version_id"] == "prompt_v2"

    attended_event = client.post(
        "/api/v1/outcomes/events",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "conversation_id": "conv_activation",
            "contact_id": "ct_activation",
            "lead_id": "lead_activation",
            "appointment_id": "apt_activation",
            "event_name": "appointment_attended",
            "event_category": "attendance",
            "event_timestamp": "2026-04-03T12:00:00Z",
            "source_system": "appointments",
            "vertical": "fitness",
            "funnel_stage": "attendance",
        },
    )
    assert attended_event.status_code == 200
    attended_payload = attended_event.json()["data"]
    assert attended_payload["attribution"]["winning_exposure_id"] == exposure_v2.json()["data"]["id"]

    payment_event = client.post(
        "/api/v1/outcomes/events",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "conversation_id": "conv_activation",
            "contact_id": "ct_activation",
            "lead_id": "lead_activation",
            "payment_id": "pay_activation",
            "event_name": "payment_completed",
            "event_category": "payment",
            "event_timestamp": "2026-04-03T14:00:00Z",
            "source_system": "payments",
            "value_number": 500.0,
            "vertical": "fitness",
            "funnel_stage": "payment",
        },
    )
    assert payment_event.status_code == 200
    payment_payload = payment_event.json()["data"]
    assert payment_payload["event"]["event_name"] == "payment_completed"
    assert payment_payload["attribution"]["facts_created"] >= 3

    attribution = client.get(
        "/api/v1/outcomes/attribution",
        headers=headers,
        params={
            "organization_id": "org_activation",
            "entity_type": "prompt_version",
            "entity_id": "prompt_v2",
            "limit": 20,
        },
    )
    assert attribution.status_code == 200
    attribution_items = attribution.json()["data"]["items"]
    assert any(item["event_name"] == "payment_completed" for item in attribution_items)
    assert all(item["entity_id"] == "prompt_v2" for item in attribution_items)

    scorecards = client.post(
        "/api/v1/outcomes/recompute",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "windows": ["28d"],
            "attribution_window_hours": 168,
        },
    )
    assert scorecards.status_code == 200
    assert scorecards.json()["data"]["scorecards_created"] >= 1

    prompt_scorecards = client.get(
        "/api/v1/outcomes/scorecards",
        headers=headers,
        params={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "entity_type": "prompt_version",
            "scorecard_window": "28d",
        },
    )
    assert prompt_scorecards.status_code == 200
    items = prompt_scorecards.json()["data"]["items"]
    by_prompt = {item["entity_id"]: item for item in items}
    assert by_prompt["prompt_v2"]["outcome_score"] > by_prompt["prompt_v1"]["outcome_score"]
    assert by_prompt["prompt_v2"]["metrics"]["revenue_sum"] >= 500.0
    assert by_prompt["prompt_v1"]["metrics"]["negative_outcomes"] >= 1

    vertical_scorecards = client.get(
        "/api/v1/outcomes/scorecards",
        headers=headers,
        params={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "entity_type": "vertical",
            "scorecard_window": "28d",
        },
    )
    assert vertical_scorecards.status_code == 200
    assert any(item["entity_id"] == "fitness" for item in vertical_scorecards.json()["data"]["items"])

    entity_detail = client.get(
        "/api/v1/outcomes/entities/prompt_version/prompt_v2",
        headers=headers,
        params={"organization_id": "org_activation"},
    )
    assert entity_detail.status_code == 200
    detail_payload = entity_detail.json()["data"]
    assert detail_payload["latest_scorecard"]["entity_id"] == "prompt_v2"
    assert any(item["event_name"] == "payment_completed" for item in detail_payload["recent_attribution"])

    duplicate_payment = client.post(
        "/api/v1/outcomes/events",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "conversation_id": "conv_activation",
            "contact_id": "ct_activation",
            "lead_id": "lead_activation",
            "payment_id": "pay_activation",
            "event_name": "payment_completed",
            "event_category": "payment",
            "event_timestamp": "2026-04-03T14:00:00Z",
            "source_system": "payments",
            "value_number": 500.0,
            "vertical": "fitness",
            "funnel_stage": "payment",
        },
    )
    assert duplicate_payment.status_code == 200
    assert duplicate_payment.json()["data"]["deduped"] is True

    decision = client.post(
        "/api/v1/outcomes/decisions/apply",
        headers=headers,
        json={
            "organization_id": "org_activation",
            "bot_id": "bot_activation",
            "entity_type": "prompt_version",
            "entity_id": "prompt_v2",
            "action": "scale",
            "reason_code": "positive_outcome_score",
            "previous_state": {"rollout": 50},
            "new_state": {"rollout": 100},
            "evidence_snapshot": {"outcome_score": by_prompt["prompt_v2"]["outcome_score"]},
        },
    )
    assert decision.status_code == 200
    decision_id = decision.json()["data"]["id"]

    rollback = client.post(
        f"/api/v1/outcomes/decisions/{decision_id}/rollback",
        headers=headers,
        json={"organization_id": "org_activation", "note": "manual rollback for validation"},
    )
    assert rollback.status_code == 200
    assert rollback.json()["data"]["rollback_of_decision_id"] == decision_id
