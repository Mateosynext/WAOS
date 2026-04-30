import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const load = (relativePath) => import(pathToFileURL(path.join(root, relativePath)).href);

const [authContracts, inboxContracts, onboardingContracts, verticalContracts, portalContracts, portalViewModel, reactiveVerticalViewModel, routePolicy, cachePolicy] = await Promise.all([
  load("app/lib/contracts/auth.ts"),
  load("app/lib/contracts/inbox.ts"),
  load("app/lib/contracts/onboarding.ts"),
  load("app/lib/contracts/verticals.ts"),
  load("app/lib/contracts/portal.ts"),
  load("app/client/clientPortalViewModel.ts"),
  load("app/components/reactiveVerticalViewModel.ts"),
  load("app/lib/auth/route-policy.ts"),
  load("app/lib/http/cache-policy.ts"),
]);

const user = authContracts.normalizeSessionUser({ ok: true, data: { id: "user_1", email: "mateo@waos.mx", organizations: [{ id: "org_1", organization_name: "Org demo", settings_json: { active_subvertical: "Ortodoncia" } }] } });
assert.equal(user.organizations[0]?.subvertical, "Ortodoncia");

const conversation = inboxContracts.normalizeConversation({ id: "conv_1", name: "Paciente demo", preview: "Necesito reagendar", last_message_at: "2026-04-20T10:00:00Z" });
assert.equal(conversation.latest_message_preview, "Necesito reagendar");
assert.equal(conversation.updated_at, "2026-04-20T10:00:00Z");

const agenda = onboardingContracts.normalizeAgendaOverview({ summary: { pending: 1 }, upcoming: [{ id: "apt_1", customer_name: "Ana", service: "Valoración", scheduled_for: "2026-04-21T09:00:00Z" }] });
assert.equal(agenda.upcoming[0]?.contact_name, "Ana");

const verticalProfile = verticalContracts.normalizeVerticalProfile({ id: "vertical_dental", name: "Dental", problem: "Falta seguimiento", selected_subvertical: { name: "Ortodoncia", promise: "Más valoraciones convertidas" }, runtime_connection: { active_subvertical: "Ortodoncia", pack_status: { coverage_score: 91 }, surface_focus: { portal: "agenda" } } });
assert.equal(verticalProfile.selected_subvertical?.name, "Ortodoncia");


const operationsSummary = portalContracts.normalizeClientOperationsSummary({ bot: { operational_state: "paused" }, counts: { recent_commands: 4, authorized_numbers: 2 }, recent_commands: [{ id: "cmd_1", result: { reply_text: "Bot pausado" } }] });
assert.equal(operationsSummary.bot.operational_state, "paused");
assert.equal(operationsSummary.recent_commands[0]?.result_summary, "Bot pausado");

const portalData = { context: { organizationId: "org_1", botId: "bot_1", vertical: "dental" }, conversations: { ok: true, error: null, endpoint: "/api/v1/conversations", data: [conversation] }, appointments: { ok: true, error: null, endpoint: "/api/v1/appointments", data: agenda.upcoming }, agendaOverview: { ok: true, error: null, endpoint: "/api/v1/agenda/overview", data: agenda }, feedback: { ok: true, error: null, endpoint: "/api/v1/feedback", data: [{ id: "f1", comment: "Todo bien", created_at: "2026-04-19T08:00:00Z" }] }, requests: { ok: true, error: null, endpoint: "/api/v1/portal/requests", data: [{ id: "r1", kind: "pricing_change", detail: "Cambiar precio", status: "pending_review", created_at: "2026-04-20T11:00:00Z" }] }, promotions: { ok: true, error: null, endpoint: "/api/v1/promotions", data: [{ id: "p1", name: "Promo mayo", message_long: "2x1", status: "active", cta_label: "Reservar" }] }, behavior: { ok: true, error: null, endpoint: "/api/v1/bot-studio/behavior", data: { bot_mode: "hybrid", tone: "warm", response_length: "medium", sales_intensity: "moderate", can_mention_stock: true } }, verticalProfile: { ok: true, error: null, endpoint: "/api/v1/verticals/profile", data: verticalProfile } };
const timeline = portalViewModel.buildClientPortalTimeline(portalData);
const summary = portalViewModel.buildClientPortalSummaryViewModel(portalData, timeline);
assert.equal(timeline[0]?.id, "r1");
assert.equal(summary.businessContext.packCoverage, "91%");
assert.equal(portalViewModel.hasPendingTimelineEntries(timeline), true);

const preview = reactiveVerticalViewModel.buildReactiveVerticalPreviewModel({ selectedSubvertical: "Ortodoncia", verticalProfile, blueprint: { profile: { name: "Dental premium", problem: "Recuperación baja", recommended_subverticals: ["Ortodoncia"] }, setup: { personality: { tone: "cálido" }, wizard: { selected_subvertical: "Ortodoncia", recommended_integrations: [{ name: "WhatsApp" }], recommended_playbooks: [{ label: "Reactivación" }] } } }, activeCatalogVertical: verticalProfile });
assert.equal(preview.previewVerticalName, "Dental premium");
assert.equal(reactiveVerticalViewModel.isSelectedSubverticalValid("ortodoncia", preview.subverticalOptions), true);

assert.equal(routePolicy.isPublicRoute("/login"), true);
assert.equal(routePolicy.requiresOrganization("/client/resumen"), true);
assert.deepEqual(routePolicy.getAllowedRoles("/security"), ["super_admin", "admin", "security_admin", "ops_admin"]);

const headers = cachePolicy.buildScopedHeaders();
assert.equal(headers.some((item) => item.source === "/:path*"), false);
assert.equal(headers.some((item) => item.source === "/_next/static/:path*" && item.headers.some((header) => header.key === "Cache-Control" && /immutable/.test(header.value))), true);
assert.equal(headers.some((item) => item.source === "/api/:path*" && item.headers.some((header) => header.key === "Cache-Control" && /no-store/.test(header.value))), true);
assert.equal(headers.some((item) => item.source === "/legal" && item.headers.some((header) => header.key === "Cache-Control" && /stale-while-revalidate/.test(header.value))), true);

console.log("Smoke OK: contracts, operations typing, wizard data gateways, view models, auth routing, and cache policies verified.");

if (!process.exitCode) process.exit(0);
