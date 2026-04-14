import http from 'node:http';
import { URL } from 'node:url';

const port = Number(process.env.PLAYWRIGHT_API_PORT || 4100);

const users = {
  'admin@acme.test': { email: 'admin@acme.test', password: 'Passw0rd!', global_role: 'super_admin', organizations: [{ id: 'org_1', name: 'Acme North', role: 'owner' }, { id: 'org_2', name: 'Acme South', role: 'owner' }], access_token: 'access-admin', refresh_token: 'refresh-admin' },
  'client@acme.test': { email: 'client@acme.test', password: 'Passw0rd!', global_role: 'client', organizations: [{ id: 'org_1', name: 'Acme North', role: 'client' }], access_token: 'access-client', refresh_token: 'refresh-client' },
  'mfa@acme.test': { email: 'mfa@acme.test', password: 'Passw0rd!', global_role: 'super_admin', organizations: [{ id: 'org_1', name: 'Acme North', role: 'owner' }], access_token: 'access-mfa', refresh_token: 'refresh-mfa' },
  'setup@acme.test': { email: 'setup@acme.test', password: 'Passw0rd!', global_role: 'super_admin', organizations: [{ id: 'org_1', name: 'Acme North', role: 'owner' }], access_token: 'access-setup', refresh_token: 'refresh-setup' },
};

const orgData = {
  org_1: {
    appointments: [{ id: 'apt_1', contact_name: 'María', service_name: 'Demo comercial', starts_at: '2026-04-14 10:00', status: 'confirmed', payment_status: 'paid' }, { id: 'apt_2', contact_name: 'Luis', service_name: 'Diagnóstico', starts_at: '2026-04-15 15:00', status: 'pending', payment_status: 'pending' }],
    agenda: { summary: { pending: 1, confirmed: 1 }, upcoming: [{ id: 'apt_1' }, { id: 'apt_2' }] },
    conversations: [{ id: 'conv_1', contact_name: 'María', status: 'ai_active', summary: 'Pide confirmación de cita.' }, { id: 'conv_2', contact_name: 'Luis', status: 'human_takeover', summary: 'Necesita aclaración de precio.' }],
    portalRequests: [{ id: 'req_1', kind: 'cambio', detail: 'Actualizar copy de bienvenida', message: 'Actualizar copy de bienvenida' }],
    feedback: [{ id: 'fb_1', kind: 'feedback', comment: 'Todo claro en portal', message: 'Todo claro en portal' }],
    promotions: [{ id: 'pro_1', name: 'Promo abril', message_short: '10% off en onboarding', starts_at: '2026-04-01', ends_at: '2026-04-30' }],
    bots: [{ id: 'bot_1', name: 'Acme Concierge' }],
    behavior: { bot_mode: 'ventas', tone: 'claro', response_length: 'media', sales_intensity: 'media' },
    directorMode: { summary: { total_conversations: 42, human_handoffs: 3 }, narrative: [{ title: 'Embudo sano', body: 'Las conversaciones llegan a agenda y pago sin fricción visible.' }] },
    reviews: [{ conversation_id: 'conv_1', result: 'ok', comment: 'Respuesta útil' }],
    reports: [{ id: 'rep_existing', period_start: '2026-04-01', period_end: '2026-04-07' }],
  },
  org_2: {
    appointments: [{ id: 'apt_3', contact_name: 'Sofía', service_name: 'Seguimiento premium', starts_at: '2026-04-16 11:00', status: 'confirmed', payment_status: 'paid' }],
    agenda: { summary: { pending: 0, confirmed: 1 }, upcoming: [{ id: 'apt_3' }] },
    conversations: [{ id: 'conv_3', contact_name: 'Sofía', status: 'ai_active', summary: 'Confirma agenda enterprise.' }],
    portalRequests: [], feedback: [], promotions: [], bots: [{ id: 'bot_2', name: 'South Sales Bot' }],
    behavior: { bot_mode: 'soporte', tone: 'formal', response_length: 'corta', sales_intensity: 'baja' },
    directorMode: { summary: { total_conversations: 7, human_handoffs: 1 }, narrative: [{ title: 'Operación chica', body: 'Org 2 queda aislada y visible como tenant separado.' }] },
    reviews: [{ conversation_id: 'conv_3', result: 'ok', comment: 'Buen aislamiento por tenant' }],
    reports: [],
  },
};

const authMeFailures = new Map();
const authMap = { 'access-admin': users['admin@acme.test'], 'access-client': users['client@acme.test'], 'access-mfa': users['mfa@acme.test'], 'access-setup': users['setup@acme.test'], 'access-refreshed-admin': users['admin@acme.test'], 'access-refreshed-client': users['client@acme.test'] };

function json(res, status, body, headers = {}) { res.writeHead(status, { 'Content-Type': 'application/json', ...headers }); res.end(JSON.stringify(body)); }
function text(res, status, body, headers = {}) { res.writeHead(status, { 'Content-Type': 'text/plain; charset=utf-8', ...headers }); res.end(body); }
function pdf(res, reportId) { const body = Buffer.from(`%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF\n${reportId}`); res.writeHead(200, { 'Content-Type': 'application/pdf', 'Content-Disposition': `attachment; filename="waos-${reportId}.pdf"`, 'Content-Length': body.length }); res.end(body); }
async function readBody(req) { const chunks = []; for await (const chunk of req) chunks.push(chunk); const raw = Buffer.concat(chunks).toString('utf8'); if (!raw) return {}; try { return JSON.parse(raw); } catch { return {}; } }
function authFromRequest(req) { const auth = req.headers.authorization || ''; const token = auth.startsWith('Bearer ') ? auth.slice(7) : ''; return { token, user: authMap[token] || null }; }
function orgIdFromUrl(url) { return url.searchParams.get('organization_id') || 'org_1'; }

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url || '/', `http://127.0.0.1:${port}`);
  if (req.method === 'GET' && url.pathname === '/api/public/sso/providers') {
    return json(res, 200, (url.searchParams.get('email') || '') === 'sso@enterprise.test' ? [{ id: 'okta_acme', provider: 'okta', organization_name: 'Acme Enterprise', button_label: 'Entrar con SSO Acme' }] : []);
  }
  if (req.method === 'POST' && url.pathname === '/api/v1/auth/login') {
    const body = await readBody(req); const user = users[body.email || ''];
    if (!user || user.password !== body.password) return json(res, 401, { detail: 'Invalid credentials' });
    if (body.email === 'mfa@acme.test' && (!body.otp_code || body.challenge_id !== 'chal_1')) return json(res, 200, { mfa_required: true, challenge_id: 'chal_1' });
    if (body.email === 'setup@acme.test' && body.mfa_setup_code !== '123456') return json(res, 200, { mfa_setup_required: true, mfa_setup: { provisioning_uri: 'otpauth://totp/WAOS:setup%40acme.test?secret=ABCDEF123456&issuer=WAOS', recovery_codes: ['rc-1', 'rc-2'], qr_svg_data_url: 'data:image/svg+xml;base64,PHN2Zy8+' } });
    return json(res, 200, { access_token: user.access_token, refresh_token: user.refresh_token, user: { id: user.email, email: user.email, global_role: user.global_role, organizations: user.organizations } });
  }
  if (req.method === 'POST' && url.pathname === '/api/v1/auth/refresh') {
    const body = await readBody(req);
    if (body.refresh_token === 'refresh-admin' || body.refresh_token === 'refresh-admin-2') return json(res, 200, { access_token: 'access-refreshed-admin', refresh_token: 'refresh-admin-2' });
    if (body.refresh_token === 'refresh-client') return json(res, 200, { access_token: 'access-refreshed-client', refresh_token: 'refresh-client' });
    return json(res, 401, { detail: 'invalid_refresh' });
  }
  if (req.method === 'POST' && url.pathname === '/api/v1/auth/logout') return json(res, 200, { ok: true });
  if (req.method === 'GET' && url.pathname === '/api/v1/auth/me') {
    const { token, user } = authFromRequest(req);
    if (token === 'expired-once') { const count = authMeFailures.get(token) || 0; if (count < 1) { authMeFailures.set(token, count + 1); return json(res, 401, { detail: 'expired' }); } }
    if (!user) return json(res, 401, { detail: 'unauthorized' });
    return json(res, 200, { id: user.email, email: user.email, global_role: user.global_role, organizations: user.organizations });
  }
  const { user } = authFromRequest(req); if (!user) return json(res, 401, { detail: 'unauthorized' });
  const orgId = orgIdFromUrl(url); const data = orgData[orgId] || orgData.org_1;
  if (req.method === 'GET' && url.pathname === '/api/v1/appointments') return json(res, 200, data.appointments);
  if (req.method === 'GET' && url.pathname === '/api/v1/agenda/overview') return json(res, 200, data.agenda);
  if (req.method === 'GET' && url.pathname === '/api/v1/conversations') return json(res, 200, data.conversations);
  if (req.method === 'GET' && url.pathname === '/api/v1/feedback') return json(res, 200, data.feedback);
  if (req.method === 'GET' && url.pathname === '/api/v1/portal/requests') return json(res, 200, data.portalRequests);
  if (req.method === 'GET' && url.pathname === '/api/v1/promotions') return json(res, 200, data.promotions);
  if (req.method === 'GET' && url.pathname === '/api/v1/bots') return json(res, 200, data.bots);
  if (req.method === 'GET' && url.pathname === '/api/v1/bot-studio/behavior') return json(res, 200, data.behavior);
  if (req.method === 'GET' && url.pathname === '/api/v1/analytics/director-mode') return json(res, 200, data.directorMode);
  if (req.method === 'GET' && url.pathname === '/api/v1/conversations/reviews') return json(res, 200, data.reviews);
  if (req.method === 'GET' && url.pathname === '/api/v1/reports/executive') return json(res, 200, data.reports);
  if (req.method === 'POST' && url.pathname === '/api/v1/reports/executive/generate') { const body = await readBody(req); const report = { id: `rep_${orgId}_${data.reports.length + 1}`, period_start: body.period_start, period_end: body.period_end }; data.reports.unshift(report); return json(res, 200, report); }
  if (req.method === 'GET' && /^\/api\/v1\/reports\/executive\/[^/]+\/pdf$/.test(url.pathname)) return pdf(res, url.pathname.split('/')[5]);
  return text(res, 404, `Not found: ${url.pathname}`);
});
server.listen(port, '127.0.0.1', () => console.log(`Mock API listening on http://127.0.0.1:${port}`));
