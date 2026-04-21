import test from "node:test";
import assert from "node:assert/strict";
import { normalizeSessionUser } from "../app/lib/contracts/auth";
import { normalizeConversation } from "../app/lib/contracts/inbox";
import { normalizeAgendaOverview } from "../app/lib/contracts/onboarding";
import { normalizeVerticalProfile } from "../app/lib/contracts/verticals";

test("auth normalizer unwraps envelope and organization settings", () => {
  const user = normalizeSessionUser({ ok: true, data: { id: "user_1", email: "ops@waos.mx", organizations: [{ id: "org_1", organization_name: "Clínica Uno", settings_json: { active_subvertical: "Ortodoncia" }, vertical: "dental" }] } });
  assert.equal(user.id, "user_1");
  assert.equal(user.organizations[0]?.name, "Clínica Uno");
  assert.equal(user.organizations[0]?.subvertical, "Ortodoncia");
});

test("conversation normalizer tolerates alternate preview fields and timestamps", () => {
  const conversation = normalizeConversation({ id: "conv_1", name: "Paciente demo", preview: "Necesito reprogramar", last_message_at: "2026-04-20T09:30:00Z", requires_human: 1 });
  assert.equal(conversation.contact_name, "Paciente demo");
  assert.equal(conversation.latest_message_preview, "Necesito reprogramar");
  assert.equal(conversation.updated_at, "2026-04-20T09:30:00Z");
  assert.equal(conversation.requires_human, true);
});

test("agenda overview normalizer keeps summary and upcoming appointments in stable shape", () => {
  const agenda = normalizeAgendaOverview({ summary: { pending: 2, confirmed: 3 }, upcoming: [{ id: "apt_1", customer_name: "Ana", service: "Valoración", scheduled_for: "2026-04-23T11:00:00Z" }] });
  assert.equal(agenda.summary.pending, 2);
  assert.equal(agenda.upcoming[0]?.contact_name, "Ana");
  assert.equal(agenda.upcoming[0]?.starts_at, "2026-04-23T11:00:00Z");
});

test("vertical profile normalizer preserves runtime connection and selected subvertical", () => {
  const profile = normalizeVerticalProfile({ id: "vertical_dental", name: "Dental", selected_subvertical: { name: "Ortodoncia", promise: "Más tratamientos" }, runtime_connection: { active_subvertical: "Ortodoncia", pack_status: { coverage_score: 91 }, surface_focus: { portal: "agenda" } } });
  assert.equal(profile.selected_subvertical?.name, "Ortodoncia");
  assert.equal(profile.runtime_connection?.active_subvertical, "Ortodoncia");
  assert.equal(Number(profile.runtime_connection?.pack_status?.coverage_score || 0), 91);
});
