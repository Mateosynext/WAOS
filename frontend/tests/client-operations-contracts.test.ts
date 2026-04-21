import test from "node:test";
import assert from "node:assert/strict";
import {
  normalizeAuthorizedOperationalNumber,
  normalizeClientOperationsAlert,
  normalizeClientOperationsAvailability,
  normalizeClientOperationsMetrics,
  normalizeClientOperationsSummary,
  normalizeOperationalCommand,
} from "../app/lib/contracts/portal";

test("client operations summary normalizer produces stable bot, counts and command detail", () => {
  const summary = normalizeClientOperationsSummary({
    bot: { operational_state: "paused", temp_unavailability_message: "Volvemos a las 4pm" },
    counts: { authorized_numbers: 2, recent_commands: 5, alerts_open: 1 },
    authorized_numbers: [{ id: "auth_1", phone_e164: "+5215550001111", role: "owner", status: "verified" }],
    recent_commands: [{ id: "cmd_1", detected_intent: "bot.pause", status: "awaiting_confirmation", requires_confirmation: true, result: { reply_text: "Bot pausado hasta nuevo aviso" } }],
  });

  assert.equal(summary.bot.operational_state, "paused");
  assert.equal(summary.counts.recent_commands, 5);
  assert.equal(summary.authorized_numbers[0]?.phone_e164, "+5215550001111");
  assert.equal(summary.recent_commands[0]?.result_summary, "Bot pausado hasta nuevo aviso");
});

test("client operations availability and metrics normalizers preserve numeric shape", () => {
  const availability = normalizeClientOperationsAvailability({
    summary: { appointments: "3", blocked_ranges: 1, open_exceptions: "2" },
    appointments: [{ id: "apt_1", status: "scheduled", scheduled_for: "2026-04-20T14:00:00Z" }],
  });
  const metrics = normalizeClientOperationsMetrics({
    summary: { total: "9", high_risk: 2, alerts_open: "4" },
    intents: [{ key: "appointment.notify_affected", total: 3 }],
  });

  assert.equal(availability.summary.appointments, 3);
  assert.equal(availability.appointments[0]?.scheduled_for, "2026-04-20T14:00:00Z");
  assert.equal(metrics.summary.total, 9);
  assert.equal(metrics.summary.alerts_open, 4);
});

test("client operations leaf normalizers avoid loose any-shaped reads", () => {
  const authorized = normalizeAuthorizedOperationalNumber({ phone: "+5215550001111", allowed_intents: ["bot.pause"] });
  const alert = normalizeClientOperationsAlert({ alert_type: "rate_limit", severity: "critical", body: "Se alcanzó el límite" });
  const command = normalizeOperationalCommand({ id: "cmd_2", status: "executed", result: { preview: { impact: { appointments_affected: 6 } } } });

  assert.equal(authorized.id, "+5215550001111");
  assert.equal(alert.alert_type, "rate_limit");
  assert.equal(command.result_summary, "6 citas afectadas");
});
