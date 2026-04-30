const state = {
  token: localStorage.getItem('waos_token') || '',
  user: null,
  organizations: [],
  currentOrgId: '',
  currentSection: 'dashboard',
  bots: [],
  dashboard: null,
  director: null,
  funnel: null,
  operatorPerformance: [],
  businessHub: null,
  commerceInsights: null,
  conversations: [],
  inboxRisk: [],
  leads: [],
  crmLeads: [],
  reactivation: [],
  voiceNotes: [],
  appointments: [],
  agendaOverview: null,
  reminderPrefs: { tone: 'amable', hoursBefore: 24, lastHours: 2, count: 2 },
  blockedSlots: [],
  payments: [],
  promotions: [],
  services: [],
  products: [],
  reports: [],
  reportSchedules: [],
  rules: [],
  jobs: [],
  alertsRules: [],
  auditLogs: [],
  selectedConversationId: '',
  selectedConversation: null,
  selectedConversationSeller: null,
  selectedConversationSummary: null,
  selectedConversationHistory: [],
  conversationCache: {},
  inboxFilter: 'all',
  inboxQuery: '',
  globalSearchQuery: '',
};

const sectionMeta = {
  dashboard: {
    title: 'Inicio',
    subtitle: 'Resumen más claro del día, prioridades y salud del negocio.',
  },
  inbox: {
    title: 'Conversaciones',
    subtitle: 'Bandeja priorizada con siguiente mejor paso, resumen y acciones rápidas.',
  },
  clients: {
    title: 'Clientes',
    subtitle: 'Ficha completa, segmentos, reactivación y clientes en riesgo de enfriarse.',
  },
  agenda: {
    title: 'Agenda',
    subtitle: 'Citas, confirmaciones, no-shows, seguimiento y horarios bloqueados.',
  },
  payments: {
    title: 'Pagos y ventas',
    subtitle: 'Cobros, pendientes, promociones y qué sí se está vendiendo.',
  },
  reports: {
    title: 'Reportes',
    subtitle: 'Resumen simple para dueño o gerente y reportes descargables.',
  },
  bots: {
    title: 'Bots',
    subtitle: 'Control rápido de bots y publicación.',
  },
  automations: {
    title: 'Automatizaciones',
    subtitle: 'Reglas, jobs y seguimiento automatizado.',
  },
  audit: {
    title: 'Auditoría',
    subtitle: 'Historial de acciones y trazabilidad.',
  },
  settings: {
    title: 'Settings',
    subtitle: 'Configuración global y alta de organizaciones.',
  },
};

const api = {
  async request(path, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    };
    if (state.token) headers.Authorization = `Bearer ${state.token}`;
    const res = await fetch(path, { ...options, headers });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || 'Request failed');
    }
    const text = await res.text();
    return text ? JSON.parse(text) : null;
  },
  async safeRequest(path, fallback = null, options = {}) {
    try {
      const data = await this.request(path, options);
      return data == null ? fallback : data;
    } catch (err) {
      console.warn(path, err.message);
      return fallback;
    }
  },
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function setHtml(selector, html) {
  const el = typeof selector === 'string' ? $(selector) : selector;
  if (el) el.innerHTML = html;
}

function setText(selector, text) {
  const el = typeof selector === 'string' ? $(selector) : selector;
  if (el) el.textContent = text;
}

function setStatus(el, text, type = 'muted') {
  if (!el) return;
  el.textContent = text;
  el.className = type;
}

function showToast(message, type = 'success') {
  const toast = $('#toast');
  if (!toast) return;
  toast.textContent = message;
  toast.className = `toast ${type}`;
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => {
    toast.className = 'toast hidden';
  }, 2800);
}

function currency(value) {
  const number = Number(value || 0);
  return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN', maximumFractionDigits: 0 }).format(number);
}

function number(value) {
  return new Intl.NumberFormat('es-MX').format(Number(value || 0));
}

function pct(value) {
  return `${Number(value || 0).toFixed(0)}%`;
}

function dateValue(value) {
  if (!value) return null;
  const dt = new Date(value);
  return Number.isNaN(dt.getTime()) ? null : dt;
}

function formatDate(value, options = { dateStyle: 'medium', timeStyle: 'short' }) {
  const dt = dateValue(value);
  if (!dt) return '—';
  return new Intl.DateTimeFormat('es-MX', options).format(dt);
}

function formatDateOnly(value) {
  return formatDate(value, { dateStyle: 'medium' });
}

function formatTime(value) {
  return formatDate(value, { hour: '2-digit', minute: '2-digit' });
}

function formatRelative(value) {
  const dt = dateValue(value);
  if (!dt) return 'sin fecha';
  const diffMs = dt.getTime() - Date.now();
  const diffHours = Math.round(diffMs / 3600000);
  if (Math.abs(diffHours) < 24) {
    if (diffHours === 0) return 'hoy';
    return diffHours > 0 ? `en ${diffHours} h` : `hace ${Math.abs(diffHours)} h`;
  }
  const diffDays = Math.round(diffHours / 24);
  return diffDays > 0 ? `en ${diffDays} d` : `hace ${Math.abs(diffDays)} d`;
}

function sameDay(a, b = new Date()) {
  const da = dateValue(a);
  if (!da) return false;
  return da.toDateString() === b.toDateString();
}

function startOfDay(date = new Date()) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function daysAgo(days) {
  const dt = new Date();
  dt.setDate(dt.getDate() - days);
  return startOfDay(dt);
}

function isWithinLastDays(value, days) {
  const dt = dateValue(value);
  if (!dt) return false;
  return dt >= daysAgo(days);
}

function toInputDate(daysOffset = 0) {
  const dt = new Date();
  dt.setDate(dt.getDate() + daysOffset);
  return dt.toISOString().slice(0, 10);
}

function greetingForHour() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Buenos días';
  if (hour < 19) return 'Buenas tardes';
  return 'Buenas noches';
}

function toneLabel(value) {
  const map = {
    amable: 'Amable',
    formal: 'Formal',
    cercano: 'Cercano',
  };
  return map[value] || value || 'Amable';
}

function badge(text, cls = '') {
  return `<span class="badge ${cls}">${escapeHtml(text)}</span>`;
}

function whatsappNumberText(bot) {
  const wa = bot.whatsapp_number || {};
  return bot.phone_number || wa.phone_number || wa.number || 'sin número';
}

function whatsappStatusText(bot) {
  const wa = bot.whatsapp_number || {};
  const status = String(bot.whatsapp_ui_status || wa.ui_status || wa.connection_status || bot.connection_status || '').toLowerCase();
  if (bot.whatsapp_send_ready === true || wa.send_ready === true || status === 'send_ready') {
    return 'WhatsApp listo para enviar';
  }
  if (whatsappNumberText(bot) !== 'sin número') {
    return 'WhatsApp pendiente de conexión';
  }
  return 'WhatsApp no configurado';
}

function whatsappStatusBadge(bot) {
  const ready = bot.whatsapp_send_ready === true || (bot.whatsapp_number || {}).send_ready === true;
  return badge(whatsappStatusText(bot), ready ? 'success' : 'warning');
}

function emptyState(title, body) {
  return `
    <div class="empty-state">
      <strong>${escapeHtml(title)}</strong>
      <div>${escapeHtml(body)}</div>
    </div>
  `;
}

function deltaHtml(current, previous, formatter = (value) => number(value)) {
  const currentNumber = Number(current || 0);
  const previousNumber = Number(previous || 0);
  const delta = currentNumber - previousNumber;
  const direction = delta > 0 ? 'up' : delta < 0 ? 'down' : '';
  const prefix = delta > 0 ? '+' : '';
  return `
    <div class="delta ${direction}">
      <span>${prefix}${formatter(delta)}</span>
      <span>vs semana pasada</span>
    </div>
  `;
}

function comparePeriods(items, dateGetter, valueGetter = () => 1) {
  const now = new Date();
  const currentStart = daysAgo(7);
  const previousStart = daysAgo(14);
  let current = 0;
  let previous = 0;
  items.forEach((item) => {
    const dt = dateValue(dateGetter(item));
    if (!dt) return;
    const value = Number(valueGetter(item) || 0);
    if (dt >= currentStart && dt <= now) current += value;
    if (dt >= previousStart && dt < currentStart) previous += value;
  });
  return { current, previous, delta: current - previous };
}

function orgName() {
  return state.organizations.find((org) => org.id === state.currentOrgId)?.name || 'tu negocio';
}

function getReminderPrefs() {
  return state.reminderPrefs || { tone: 'amable', hoursBefore: 24, lastHours: 2, count: 2 };
}

function getBlockedSlots() {
  return state.blockedSlots || [];
}

function parseNoteReason(note) {
  const text = String(note || '');
  const marker = 'Cancelación:';
  if (!text.includes(marker)) return '';
  return text.split(marker).pop().trim();
}

function leadMemoryByConversation(conversation) {
  return state.leads.find((item) => item.contact_id === conversation.contact_id && item.bot_id === conversation.bot_id) || null;
}

function crmLeadByConversation(conversation) {
  const matches = state.crmLeads.filter((item) => item.contact_id === conversation.contact_id && item.bot_id === conversation.bot_id);
  if (!matches.length) return null;
  return matches.sort((a, b) => String(b.updated_at || '').localeCompare(String(a.updated_at || '')))[0];
}

function paymentsForConversation(conversation) {
  return state.payments.filter((item) => item.conversation_id === conversation.id || item.contact_id === conversation.contact_id);
}

function appointmentsForConversation(conversation) {
  return state.appointments.filter((item) => item.conversation_id === conversation.id || item.contact_id === conversation.contact_id);
}

function riskByConversationId(id) {
  return state.inboxRisk.find((item) => item.conversation_id === id) || null;
}

function humanTags(baseTags = [], crmLead = null, memory = null, risk = null) {
  const tags = new Set((baseTags || []).map((tag) => String(tag).toLowerCase()));
  const stage = String(memory?.lead_stage || crmLead?.stage || '').toLowerCase();
  if (!stage) tags.add('nuevo');
  if (stage.includes('pago')) tags.add('pendiente de pago');
  if (stage.includes('agend')) tags.add('listo para cita');
  if (crmLead?.temperature_status === 'frío') tags.add('se enfrio');
  if ((crmLead?.close_probability || 0) >= 70) tags.add('alto potencial');
  if (risk?.stale_hours >= 24) tags.add('sin respuesta');
  return Array.from(tags).slice(0, 6);
}

function inferShortSummary(conversation, crmLead, risk) {
  const source = `${conversation.summary || ''} ${(crmLead?.notes || '')} ${(crmLead?.best_next_action || '')}`.toLowerCase();
  if (source.includes('precio') || source.includes('cotiz')) return 'Preguntó precio';
  if (source.includes('agend') || source.includes('cita')) return 'Quiere cita esta semana';
  if (source.includes('compar')) return 'Está comparando opciones';
  if (source.includes('pago')) return 'Quedó pendiente de pago';
  if (risk?.cancel_flags?.includes('timing_objection')) return 'Se enfrió por tiempo';
  return conversation.summary || crmLead?.best_next_action || 'Conversación activa';
}

function inferNextStep(conversation, crmLead, risk) {
  if (crmLead?.best_next_action) return crmLead.best_next_action;
  const source = `${conversation.summary || ''} ${crmLead?.next_action || ''}`.toLowerCase();
  if (source.includes('pago')) return 'Conviene mandar cobro';
  if (source.includes('agend') || source.includes('cita')) return 'Conviene ofrecer cita';
  if (risk?.cancel_flags?.includes('cancel_intent')) return 'Conviene pasar a humano';
  if ((risk?.stale_hours || 0) >= 4) return 'Conviene mandar recordatorio';
  return 'Conviene dar seguimiento';
}

function enrichConversation(conversation) {
  const crmLead = crmLeadByConversation(conversation);
  const memory = leadMemoryByConversation(conversation) || conversation;
  const risk = riskByConversationId(conversation.id);
  const priorityScore = Math.min(100,
    Number(risk?.risk_score || 0) +
    Number(conversation.lead_score || memory?.lead_score || 0) +
    ((crmLead?.stage || '').includes('pago') ? 18 : 0) +
    ((crmLead?.stage || '').includes('agend') ? 12 : 0)
  );
  let priority = 'low';
  if (priorityScore >= 70) priority = 'high';
  else if (priorityScore >= 40) priority = 'medium';
  return {
    ...conversation,
    crmLead,
    memory,
    risk,
    priorityScore,
    priority,
    shortSummary: inferShortSummary(conversation, crmLead, risk),
    nextStep: inferNextStep(conversation, crmLead, risk),
    displayTags: humanTags(conversation.tags || [], crmLead, memory, risk),
  };
}

function filteredConversations() {
  const query = (state.inboxQuery || state.globalSearchQuery || '').trim().toLowerCase();
  return state.conversations
    .map(enrichConversation)
    .filter((item) => {
      const stage = String(item.crmLead?.stage || item.lead_stage || '').toLowerCase();
      const summary = `${item.contact_name || ''} ${item.contact_phone || ''} ${item.bot_name || ''} ${item.summary || ''} ${item.shortSummary || ''} ${item.nextStep || ''} ${(item.displayTags || []).join(' ')}`.toLowerCase();
      if (state.inboxFilter === 'sin_respuesta' && !((item.risk?.at_risk) || (item.risk?.stale_hours || 0) >= 4)) return false;
      if (state.inboxFilter === 'quiere_cita' && !(stage.includes('agend') || summary.includes('cita'))) return false;
      if (state.inboxFilter === 'quiere_pagar' && !(stage.includes('pago') || summary.includes('pago') || summary.includes('cobro'))) return false;
      if (state.inboxFilter === 'seguimiento' && !((item.risk?.stale_hours || 0) >= 4 || summary.includes('seguimiento') || stage.includes('propuesta'))) return false;
      if (state.inboxFilter === 'humano' && !(item.human_takeover || summary.includes('humano') || (item.risk?.cancel_flags || []).includes('cancel_intent'))) return false;
      if (query && !summary.includes(query)) return false;
      return true;
    })
    .sort((a, b) => b.priorityScore - a.priorityScore || String(b.updated_at || '').localeCompare(String(a.updated_at || '')));
}

function computeDashboardModel() {
  const directorSummary = state.director?.summary || {};
  const dashboardSummary = state.dashboard?.summary || {};
  const todayConversations = state.conversations.filter((item) => sameDay(item.updated_at || item.created_at)).length;
  const appointmentsToday = state.appointments.filter((item) => sameDay(item.scheduled_for)).length;
  const paidToday = state.payments
    .filter((item) => String(item.status || '').toLowerCase() === 'paid' && sameDay(item.paid_at || item.confirmed_at || item.updated_at || item.created_at))
    .reduce((acc, item) => acc + Number(item.amount || 0), 0);
  const pendingAttention = state.inboxRisk.filter((item) => item.at_risk).length;

  const conversationsWoW = comparePeriods(state.conversations, (item) => item.updated_at || item.created_at);
  const appointmentsWoW = comparePeriods(state.appointments, (item) => item.created_at || item.scheduled_for);
  const paymentsWoW = comparePeriods(
    state.payments.filter((item) => String(item.status || '').toLowerCase() === 'paid'),
    (item) => item.paid_at || item.confirmed_at || item.created_at,
    (item) => Number(item.amount || 0),
  );
  const reactivationWoW = comparePeriods(state.reactivation, (item) => item.updated_at || item.created_at);

  const attentionHealth = Math.max(0, 100 - (pendingAttention * 12));
  const citasHealth = Math.min(100, Math.round((Number(state.agendaOverview?.summary?.show_rate || 0) + 10)));
  const cobranzaHealth = Math.min(100, Math.round((Number(directorSummary.conversion_rate || 0) * 1.2) + 20));
  const seguimientoHealth = Math.max(0, 100 - (state.reactivation.length * 4));

  const goals = [
    { key: 'citas', label: 'Citas', current: Number(directorSummary.appointments_scheduled || dashboardSummary.appointments_today || 0), goal: 40 },
    { key: 'ventas', label: 'Ventas', current: Number(directorSummary.sales_generated || 0), goal: 20 },
    { key: 'pagos', label: 'Pagos', current: Number(directorSummary.attributed_revenue || state.businessHub?.summary?.payments_attributed || 0), goal: 60000, money: true },
    { key: 'reactivaciones', label: 'Reactivaciones', current: state.reactivation.length, goal: 15 },
    { key: 'recuperados', label: 'Clientes recuperados', current: state.reactivation.filter((item) => Number(item.priority || 0) >= 80).length, goal: 8 },
  ];

  const alerts = [];
  if ((directorSummary.response_rate || 0) < 80) alerts.push({ tone: 'warning', title: 'Hoy bajó la velocidad de respuesta', body: 'Hay más conversaciones esperando respuesta de lo ideal.' });
  if (pendingAttention > 0) alerts.push({ tone: 'danger', title: `Hay ${pendingAttention} conversaciones sin seguimiento`, body: 'Conviene responder o mandar recordatorio antes de perderlas.' });
  if (state.payments.some((item) => String(item.status || '').toLowerCase() === 'pending')) alerts.push({ tone: 'warning', title: 'Hay pagos pendientes por recuperar', body: 'El portal ya los está concentrando para cobrar más fácil.' });
  if (!alerts.length) alerts.push({ tone: 'success', title: 'La operación va estable', body: 'No hay alertas críticas en este momento.' });

  const priorities = [
    {
      label: 'Clientes sin respuesta',
      value: pendingAttention,
      action: 'Revisar conversaciones',
      section: 'inbox',
      emphasis: pendingAttention > 0 ? 'danger' : 'success',
      helper: pendingAttention > 0 ? 'Conviene responder primero aquí.' : 'No hay urgencias abiertas.',
    },
    {
      label: 'Citas próximas',
      value: state.appointments.filter((item) => {
        const dt = dateValue(item.scheduled_for);
        return dt && dt >= new Date() && dt <= new Date(Date.now() + (48 * 3600000));
      }).length,
      action: 'Ver agenda',
      section: 'agenda',
      emphasis: 'warning',
      helper: 'Revisa confirmaciones y posibles no-shows.',
    },
    {
      label: 'Pagos pendientes',
      value: state.payments.filter((item) => String(item.status || '').toLowerCase() !== 'paid').length,
      action: 'Cobrar ahora',
      section: 'payments',
      emphasis: 'warning',
      helper: 'Una recuperación rápida suele mover ventas del día.',
    },
    {
      label: 'Conversaciones detenidas',
      value: state.reactivation.length,
      action: 'Reactivar clientes',
      section: 'clients',
      emphasis: 'purple',
      helper: 'Estas oportunidades todavía se pueden recuperar.',
    },
  ];

  const cards = [
    {
      label: 'Clientes escribieron hoy',
      value: todayConversations,
      delta: conversationsWoW,
      formatter: (v) => number(v),
      subvalue: `${number(dashboardSummary.active_conversations || state.businessHub?.summary?.conversations_active || 0)} conversaciones activas`,
    },
    {
      label: 'Citas agendadas hoy',
      value: appointmentsToday,
      delta: appointmentsWoW,
      formatter: (v) => number(v),
      subvalue: `${number(state.agendaOverview?.summary?.pending || 0)} por confirmar`,
    },
    {
      label: 'Pagos entraron hoy',
      value: currency(paidToday),
      delta: paymentsWoW,
      formatter: (v) => currency(v),
      subvalue: `${number(state.payments.filter((item) => String(item.status || '').toLowerCase() === 'paid').length)} pagos confirmados`,
    },
    {
      label: 'Necesitan atención',
      value: pendingAttention,
      delta: reactivationWoW,
      formatter: (v) => number(v),
      subvalue: `${number(state.reactivation.length)} clientes listos para reactivar`,
    },
  ];

  const health = [
    { label: 'Atención', value: attentionHealth, helper: pendingAttention ? 'Hay conversaciones atoradas.' : 'Tiempo de respuesta sano.' },
    { label: 'Citas', value: citasHealth, helper: `${pct(state.agendaOverview?.summary?.show_rate || 0)} de show rate` },
    { label: 'Cobros', value: cobranzaHealth, helper: `${pct(state.director?.summary?.conversion_rate || 0)} de conversión` },
    { label: 'Seguimiento', value: seguimientoHealth, helper: `${number(state.reactivation.length)} por retomar` },
  ];

  return { cards, priorities, goals, alerts, health };
}

function renderTopbar() {
  const meta = sectionMeta[state.currentSection] || sectionMeta.dashboard;
  setText('#section-title', meta.title);
  setText('#section-subtitle', meta.subtitle);
}

function renderOrgSelectors() {
  ['#org-filter', '#bot-org-id', '#rule-org-id'].forEach((selector) => {
    const el = $(selector);
    if (!el) return;
    el.innerHTML = state.organizations.map((org) => `
      <option value="${escapeHtml(org.id)}" ${org.id === state.currentOrgId ? 'selected' : ''}>${escapeHtml(org.name)}</option>
    `).join('');
  });
}

function fillBotSelectors() {
  ['#simulate-bot-id', '#rule-bot-id'].forEach((selector) => {
    const el = $(selector);
    if (!el) return;
    el.innerHTML = state.bots.map((bot) => `
      <option value="${escapeHtml(bot.id)}">${escapeHtml(bot.name)} · ${escapeHtml(bot.business_name || 'Negocio')}</option>
    `).join('');
  });
}

function showSection(name) {
  state.currentSection = name;
  $$('.section').forEach((el) => el.classList.remove('active'));
  $$('.nav-item').forEach((el) => el.classList.remove('active'));
  $(`#section-${name}`)?.classList.add('active');
  document.querySelector(`.nav-item[data-section="${name}"]`)?.classList.add('active');
  renderTopbar();
}

async function login() {
  try {
    const data = await api.request('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        email: $('#login-email').value,
        password: $('#login-password').value,
      }),
    });
    state.token = data.access_token;
    localStorage.setItem('waos_token', state.token);
    setText('#login-error', '');
    await bootstrap();
  } catch (err) {
    setText('#login-error', err.message);
  }
}

async function bootstrap() {
  if (!state.token) return;
  try {
    state.user = await api.request('/api/v1/auth/me');
    state.organizations = state.user.organizations || [];
    state.currentOrgId = state.currentOrgId || state.organizations[0]?.id || '';
    setText('#current-user', `${state.user.full_name} · ${state.user.global_role}`);
    $('#login-screen').classList.add('hidden');
    $('#app-shell').classList.remove('hidden');
    renderOrgSelectors();
    fillReminderPrefsForm();
    $('#report-start').value = toInputDate(-7);
    $('#report-end').value = toInputDate(0);
    await refreshAll();
  } catch (err) {
    console.error(err);
    localStorage.removeItem('waos_token');
    state.token = '';
    $('#login-screen').classList.remove('hidden');
    $('#app-shell').classList.add('hidden');
  }
}

async function refreshAll() {
  await Promise.all([
    loadOverviewData(),
    loadBots(),
    loadConversationData(),
    loadClientData(),
    loadAgendaData(),
    loadRevenueData(),
    loadAutomationData(),
    loadReportsData(),
    loadAudit(),
    loadSettings(),
  ]);
  renderAll();
  const currentVisible = filteredConversations();
  if (!state.selectedConversationId && currentVisible[0]) {
    await selectConversation(currentVisible[0].id);
  } else if (state.selectedConversationId) {
    const stillExists = state.conversations.some((item) => item.id === state.selectedConversationId);
    if (stillExists) {
      await selectConversation(state.selectedConversationId, { silent: true });
    } else {
      state.selectedConversationId = '';
      state.selectedConversation = null;
      renderInboxDetail();
    }
  }
}

async function loadOverviewData() {
  const query = state.currentOrgId ? `?organization_id=${state.currentOrgId}` : '';
  state.dashboard = await api.safeRequest(`/api/v1/analytics/dashboard${query}`, { summary: {}, bots: [] });
  state.director = await api.safeRequest(`/api/v1/analytics/director-mode${query}`, { summary: {} });
  state.funnel = await api.safeRequest(`/api/v1/analytics/funnel${query}`, { funnel: [] });
  state.operatorPerformance = await api.safeRequest(`/api/v1/analytics/operator-performance${query}`, []);
  state.businessHub = await api.safeRequest(`/api/v1/business-hub/overview${query}`, { summary: {}, attention: [], top_products: [] });
  state.commerceInsights = await api.safeRequest(`/api/v1/commerce/insights${query}`, { summary: {}, top_products: [], top_promotions: [], recommendations: [] });
}

async function loadBots() {
  const query = state.currentOrgId ? `?organization_id=${state.currentOrgId}` : '';
  state.bots = await api.safeRequest(`/api/v1/bots${query}`, []);
  fillBotSelectors();
}

async function loadConversationData() {
  const query = state.currentOrgId ? `?organization_id=${state.currentOrgId}` : '';
  state.conversations = await api.safeRequest(`/api/v1/conversations${query}`, []);
  state.inboxRisk = await api.safeRequest(`/api/v1/inbox/risk${query}`, []);
}

async function loadClientData() {
  const query = state.currentOrgId ? `?organization_id=${state.currentOrgId}` : '';
  state.leads = await api.safeRequest(`/api/v1/leads${query}`, []);
  state.crmLeads = await api.safeRequest(`/api/v1/crm/leads${query}`, []);
  state.reactivation = await api.safeRequest(`/api/v1/reactivation/recommendations${query}`, []);
  state.voiceNotes = await api.safeRequest(`/api/v1/voice/notes${query}`, []);
}

async function loadAgendaData() {
  const query = state.currentOrgId ? `?organization_id=${state.currentOrgId}` : '';
  state.appointments = await api.safeRequest(`/api/v1/appointments${query}`, []);
  state.agendaOverview = await api.safeRequest(`/api/v1/agenda/overview${query}`, { summary: {}, upcoming: [] });
  const prefs = await api.safeRequest(`/api/v1/agenda/reminder-preferences${query}`, null);
  state.reminderPrefs = {
    tone: prefs?.tone || 'amable',
    hoursBefore: Number(prefs?.hours_before || 24),
    lastHours: Number(prefs?.last_hours || 2),
    count: Number(prefs?.count || 2),
  };
  state.blockedSlots = await api.safeRequest(`/api/v1/agenda/blocked-slots${query}`, []);
}

async function loadRevenueData() {
  const query = state.currentOrgId ? `?organization_id=${state.currentOrgId}` : '';
  state.payments = await api.safeRequest(`/api/v1/sales/payments${query}`, []);
  state.promotions = await api.safeRequest(`/api/v1/promotions${query}`, []);
  state.services = await api.safeRequest(`/api/v1/catalog/services${query}`, []);
  state.products = await api.safeRequest(`/api/v1/catalog/products${query}`, []);
}

async function loadAutomationData() {
  const query = state.currentOrgId ? `?organization_id=${state.currentOrgId}` : '';
  state.rules = await api.safeRequest(`/api/v1/automations/rules${query}`, []);
  state.jobs = await api.safeRequest(`/api/v1/automations/jobs${query}`, []);
  state.alertsRules = await api.safeRequest(`/api/v1/alerts/rules${query}`, []);
}

async function loadReportsData() {
  const query = state.currentOrgId ? `?organization_id=${state.currentOrgId}` : '';
  state.reports = await api.safeRequest(`/api/v1/reports/executive${query}`, []);
  state.reportSchedules = await api.safeRequest(`/api/v1/reports/schedules${query}`, []);
}

async function loadAudit() {
  const query = state.currentOrgId ? `?organization_id=${state.currentOrgId}` : '';
  state.auditLogs = await api.safeRequest(`/api/v1/audit/logs${query}`, []);
}

async function loadSettings() {
  const section = $('#section-settings');
  try {
    const data = await api.request('/api/v1/settings/global');
    $('#global-policy').value = data.global_policy || '';
    $('#global-model').value = data.default_model || '';
    $('#global-freeze').value = data.freeze_minutes_after_takeover || 30;
    $('#ai-optimization-json').value = JSON.stringify(data.ai_optimization || {}, null, 2);
    $('#memory-runtime-json').value = JSON.stringify(data.memory_runtime || {}, null, 2);
    section.classList.remove('hidden');
  } catch (err) {
    setHtml('#section-settings', '<div class="panel"><div class="muted">Solo Super Admin puede ver settings globales.</div></div>');
  }
}

function renderAll() {
  renderTopbar();
  renderDashboard();
  renderBots();
  renderInboxList();
  renderClients();
  renderAgenda();
  renderPayments();
  renderAutomations();
  renderReports();
  renderAudit();
  fillBotSelectors();
}

function renderDashboard() {
  const model = computeDashboardModel();
  const directorSummary = state.director?.summary || {};
  const dashboardSummary = state.dashboard?.summary || {};

  setHtml('#dashboard-hero', `
    <div class="hero">
      <div class="hero-title">${escapeHtml(greetingForHour())}, ${escapeHtml(orgName())}</div>
      <div class="hero-subtitle">
        Hoy puedes ver en segundos cuántos clientes escribieron, cuántas citas se agendaron, cuánto se cobró y qué conversaciones necesitan atención.
      </div>
      <div class="hero-inline">
        ${badge(`${number(directorSummary.leads_attended || state.leads.length)} clientes atendidos`, 'subtle')}
        ${badge(`${number(directorSummary.appointments_scheduled || dashboardSummary.appointments_today || 0)} citas`, 'subtle')}
        ${badge(`${currency(directorSummary.attributed_revenue || state.businessHub?.summary?.payments_attributed || 0)} atribuidos`, 'subtle')}
        ${badge(`${pct(directorSummary.response_rate || 0)} de respuesta`, 'subtle')}
      </div>
    </div>
  `);

  setHtml('#dashboard-actions', `
    <div class="quick-actions">
      <button class="quick-action" data-quick-section="inbox">
        <strong>Enviar mensaje</strong>
        <span>Ve directo a conversaciones pendientes.</span>
      </button>
      <button class="quick-action" data-quick-section="agenda">
        <strong>Agendar cita</strong>
        <span>Revisa huecos, confirmaciones y próximas citas.</span>
      </button>
      <button class="quick-action" data-quick-section="payments">
        <strong>Cobrar</strong>
        <span>Recupera pagos pendientes y crea cobros rápidos.</span>
      </button>
      <button class="quick-action" data-quick-section="bots">
        <strong>Pausar asistente</strong>
        <span>Controla estado de bots y publicación.</span>
      </button>
      <button class="quick-action" data-quick-section="clients">
        <strong>Revisar clientes</strong>
        <span>Detecta enfriamiento, reactivación y segmentos.</span>
      </button>
    </div>
  `);

  setHtml('#dashboard-cards', model.cards.map((card) => `
    <div class="card">
      <div class="card-label">${escapeHtml(card.label)}</div>
      <div class="card-value">${escapeHtml(card.value)}</div>
      <div class="card-subvalue">${escapeHtml(card.subvalue)}</div>
      ${deltaHtml(card.delta.current, card.delta.previous, card.formatter)}
    </div>
  `).join(''));

  setText('#today-focus-count', `${model.priorities.reduce((acc, item) => acc + Number(item.value || 0), 0)} pendientes`);
  setHtml('#dashboard-priority', model.priorities.map((item) => `
    <div class="metric-row">
      <div class="stat-pair">
        <div>
          <div class="list-item-title">${escapeHtml(item.label)}</div>
          <div class="muted">${escapeHtml(item.helper)}</div>
        </div>
        ${badge(number(item.value), item.emphasis)}
      </div>
      <div class="list-item-actions">
        <button class="secondary small" data-quick-section="${escapeHtml(item.section)}">${escapeHtml(item.action)}</button>
      </div>
    </div>
  `).join(''));

  setHtml('#dashboard-health', model.health.map((item) => `
    <div class="health-item">
      <div class="health-header">
        <strong>${escapeHtml(item.label)}</strong>
        <span>${pct(item.value)}</span>
      </div>
      <div class="progress-track"><div class="progress-fill" style="width:${Math.min(100, item.value)}%"></div></div>
      <div class="muted top-space">${escapeHtml(item.helper)}</div>
    </div>
  `).join(''));

  setHtml('#dashboard-goals', model.goals.map((item) => {
    const progress = Math.min(100, Math.round((Number(item.current || 0) / Math.max(1, Number(item.goal || 1))) * 100));
    const currentValue = item.money ? currency(item.current) : number(item.current);
    const goalValue = item.money ? currency(item.goal) : number(item.goal);
    return `
      <div class="goal-item">
        <div class="goal-header">
          <strong>${escapeHtml(item.label)}</strong>
          <span>${escapeHtml(currentValue)} / ${escapeHtml(goalValue)}</span>
        </div>
        <div class="progress-track"><div class="progress-fill" style="width:${progress}%"></div></div>
      </div>
    `;
  }).join(''));

  setHtml('#dashboard-alerts', model.alerts.map((alert) => `
    <div class="alert-item">
      <div class="list-item-title">${escapeHtml(alert.title)}</div>
      <div class="muted">${escapeHtml(alert.body)}</div>
    </div>
  `).join(''));

  const bots = state.dashboard?.bots || [];
  setHtml('#dashboard-bots', bots.length ? `
    <div class="table-wrap">
      <table class="table">
        <thead>
          <tr><th>Bot</th><th>Estado</th><th>IA</th><th>Conv. activas</th></tr>
        </thead>
        <tbody>
          ${bots.map((bot) => `
            <tr>
              <td>${escapeHtml(bot.name)}</td>
              <td>${badge(bot.status || '—')}</td>
              <td>${bot.ai_paused ? badge('Pausada', 'warning') : badge('Activa', 'success')}</td>
              <td>${number(bot.conversations_active)}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  ` : emptyState('Todavía no hay bots', 'Cuando existan bots activos, aquí verás su estado y conversaciones activas.'));
}

function renderBots() {
  setHtml('#bots-list', state.bots.length ? `
    <div class="list">
      ${state.bots.map((bot) => `
        <div class="list-item">
          <div class="list-item-title">${escapeHtml(bot.name)}</div>
          <div class="list-item-meta">${escapeHtml(bot.business_name || 'Negocio')} · ${escapeHtml(whatsappNumberText(bot))} · ${whatsappStatusBadge(bot)} · ${escapeHtml(bot.status || 'draft')}</div>
          <div class="list-item-actions">
            <button class="small secondary" data-bot-action="pause-resume" data-bot-id="${escapeHtml(bot.id)}" data-bot-next="${bot.ai_paused ? 'resume' : 'pause'}">${bot.ai_paused ? 'Reanudar IA' : 'Pausar IA'}</button>
            <button class="small secondary" data-bot-action="clone" data-bot-id="${escapeHtml(bot.id)}">Clonar</button>
            <button class="small secondary" data-bot-action="publish" data-bot-id="${escapeHtml(bot.id)}">Publicar versión</button>
          </div>
        </div>
      `).join('')}
    </div>
  ` : emptyState('Aún no hay bots', 'Crea un bot para empezar a atender conversaciones y agendar citas.'));
}

function renderInboxList() {
  const conversations = filteredConversations();
  setText('#conversation-count-label', `${conversations.length} conversaciones`);
  setHtml('#conversation-list', conversations.length ? `
    <div class="list">
      ${conversations.map((conversation) => `
        <div class="list-item inbox-item priority-${conversation.priority} ${conversation.id === state.selectedConversationId ? 'active' : ''}" data-conversation-id="${escapeHtml(conversation.id)}">
          <div class="inbox-item-head">
            <div>
              <div class="list-item-title">${escapeHtml(conversation.contact_name || conversation.contact_phone || 'Cliente')}</div>
              <div class="list-item-meta">${escapeHtml(conversation.bot_name || 'Bot')} · ${escapeHtml(conversation.status || 'activo')} · score ${number(conversation.lead_score || conversation.memory?.lead_score || 0)}</div>
            </div>
            ${badge(conversation.priority === 'high' ? 'Prioridad alta' : conversation.priority === 'medium' ? 'Prioridad media' : 'En seguimiento', conversation.priority === 'high' ? 'danger' : conversation.priority === 'medium' ? 'warning' : 'success')}
          </div>
          <div class="inbox-preview"><strong>${escapeHtml(conversation.shortSummary)}</strong><br>${escapeHtml(conversation.nextStep)}</div>
          <div class="inbox-tags">
            ${(conversation.displayTags || []).map((tag) => badge(tag, 'subtle')).join('')}
          </div>
        </div>
      `).join('')}
    </div>
  ` : emptyState('No hay conversaciones para este filtro', 'Ajusta los filtros o prueba otra búsqueda para encontrar clientes.'));
}

function buildSelectedTimeline(detail) {
  const conversation = detail.conversation || {};
  const contact = detail.contact || {};
  const lead = crmLeadByConversation(conversation);
  const appointments = appointmentsForConversation(conversation);
  const payments = paymentsForConversation(conversation);
  const history = state.selectedConversationHistory || [];
  const messages = (detail.messages || []).slice(-4).map((item) => ({
    type: item.direction === 'inbound' ? 'Escribió' : item.direction === 'internal' ? 'Nota interna' : 'Respondimos',
    at: item.created_at,
    detail: item.body,
  }));

  const items = [
    { type: 'Cliente creado', at: contact.created_at, detail: contact.phone || contact.name || 'Nuevo cliente' },
    ...messages,
    ...appointments.map((item) => ({ type: 'Cita', at: item.scheduled_for, detail: `${item.status || 'scheduled'} · ${item.notes || 'Sin notas'}` })),
    ...payments.map((item) => ({ type: 'Pago', at: item.paid_at || item.confirmed_at || item.created_at, detail: `${item.status || 'pending'} · ${currency(item.amount)}` })),
    ...history.slice(0, 3).map((item) => ({ type: 'Cambio de seguimiento', at: item.changed_at, detail: `Etapa ${item.after?.lead_stage || '—'} · ${item.after?.next_action || '—'}` })),
    lead ? { type: 'Oportunidad', at: lead.updated_at || lead.created_at, detail: `${lead.stage || 'nuevo'} · ${lead.best_next_action || lead.next_action || ''}` } : null,
  ].filter(Boolean).sort((a, b) => new Date(b.at || 0) - new Date(a.at || 0));

  if (!items.length) return emptyState('Sin historial todavía', 'Cuando haya mensajes, citas o pagos, aquí verás la línea de tiempo del cliente.');
  return `<div class="timeline">${items.map((item) => `
    <div class="timeline-item">
      <div class="timeline-date">${escapeHtml(formatDate(item.at))}</div>
      <div class="list-item-title">${escapeHtml(item.type)}</div>
      <div class="muted">${escapeHtml(String(item.detail || '').slice(0, 180))}</div>
    </div>
  `).join('')}</div>`;
}

function internalNotes(detail) {
  const notes = (detail.messages || []).filter((item) => item.direction === 'internal').slice(-4).reverse();
  if (!notes.length) return emptyState('Sin notas internas', 'Agrega una nota para que el equipo recuerde contexto importante.');
  return `<div class="list">${notes.map((note) => `
    <div class="list-item">
      <div class="list-item-meta">${escapeHtml(formatDate(note.created_at))}</div>
      <div>${escapeHtml(note.body)}</div>
    </div>
  `).join('')}</div>`;
}

function recentVoiceSummaries(detail) {
  const notes = state.voiceNotes.filter((item) => item.conversation_id === detail.conversation?.id).slice(0, 3);
  const latestSummary = detail.latest_summary?.summary || state.selectedConversationSummary?.summary;
  if (!notes.length && !latestSummary) {
    return emptyState('Resumen de voz y mensajes', 'Cuando haya audios o resúmenes generados, aquí verás una versión corta y fácil de leer.');
  }
  return `
    ${latestSummary ? `<div class="kv-block"><div class="kv-block-label">Resumen rápido</div><div class="kv-block-value">${escapeHtml(latestSummary)}</div></div>` : ''}
    ${notes.map((note) => `
      <div class="kv-block top-space">
        <div class="kv-block-label">Audio ${escapeHtml(formatDate(note.created_at))}</div>
        <div class="kv-block-value">${escapeHtml(String(note.transcript || '').slice(0, 180))}</div>
      </div>
    `).join('')}
  `;
}

function fillReminderPrefsForm() {
  const prefs = getReminderPrefs();
  if ($('#reminder-tone')) $('#reminder-tone').value = prefs.tone || 'amable';
  if ($('#reminder-hours-before')) $('#reminder-hours-before').value = prefs.hoursBefore || 24;
  if ($('#reminder-last-hours')) $('#reminder-last-hours').value = prefs.lastHours || 2;
  if ($('#reminder-count')) $('#reminder-count').value = String(prefs.count || 2);
}

function renderInboxDetail() {
  const detail = state.selectedConversation;
  if (!detail) {
    setHtml('#conversation-detail', '<div class="chat-empty">Selecciona una conversación para ver resumen, acciones rápidas y contexto.</div>');
    setHtml('#conversation-toolbar', '');
    setHtml('#lead-context', '<div class="lead-empty">Sin cliente seleccionado.</div>');
    return;
  }
  const conversation = detail.conversation || {};
  const memory = detail.memory || {};
  const contact = detail.contact || {};
  const risk = riskByConversationId(conversation.id) || {};
  const crmLead = crmLeadByConversation(conversation) || {};
  const seller = state.selectedConversationSeller || {};
  const tags = detail.tags || [];
  const appointment = appointmentsForConversation(conversation)[0];
  const pendingPayment = paymentsForConversation(conversation).find((item) => String(item.status || '').toLowerCase() !== 'paid');
  const latestSummary = detail.latest_summary?.summary || state.selectedConversationSummary?.summary || memory.summary;

  setHtml('#conversation-toolbar', `
    <button class="secondary small" data-action="takeover-conversation">Tomar</button>
    <button class="secondary small" data-action="reactivate-conversation">Reactivar IA</button>
    <button class="secondary small" data-action="generate-summary">Resumen</button>
  `);

  setHtml('#conversation-detail', `
    <div class="kv-compact">
      <div class="kv-block">
        <div class="stat-pair">
          <div>
            <div class="list-item-title">${escapeHtml(contact.name || contact.phone || 'Cliente')}</div>
            <div class="muted">${escapeHtml(conversation.bot_name || detail.bot?.name || 'Bot')} · ${escapeHtml(crmLead.stage || memory.lead_stage || 'nuevo')}</div>
          </div>
          ${badge(seller.temperature_status || (risk.risk_score > 60 ? 'prioridad alta' : 'estable'), risk.risk_score > 60 ? 'danger' : 'subtle')}
        </div>
        <div class="inbox-tags top-space">
          ${(humanTags(tags, crmLead, memory, risk)).map((tag) => badge(tag, 'subtle')).join('')}
        </div>
        <div class="top-space muted">${escapeHtml(seller.human_summary || latestSummary || 'Aquí verás un resumen corto antes de abrir cada conversación.')}</div>
      </div>
    </div>

    <div class="inline-actions top-space">
      <button class="secondary small" data-action="open-appointment-form">Agendar</button>
      <button class="secondary small" data-action="open-payment-form">Cobrar</button>
      <button class="secondary small" data-action="send-friendly-reminder">Enviar recordatorio</button>
      <button class="secondary small" data-action="open-lead-form">Marcar seguimiento</button>
      <button class="secondary small" data-action="takeover-conversation">Pasar a persona</button>
    </div>

    <div class="grid two top-space">
      <div class="kv-block">
        <div class="kv-block-label">Siguiente mejor paso</div>
        <div class="kv-block-value">${escapeHtml(seller.best_next_action || crmLead.best_next_action || memory.next_action || inferNextStep(conversation, crmLead, risk))}</div>
      </div>
      <div class="kv-block">
        <div class="kv-block-label">Historial corto</div>
        <div class="kv-block-value">
          ${appointment ? `Última cita: ${escapeHtml(formatDate(appointment.scheduled_for))}. ` : ''}
          ${pendingPayment ? `Pago pendiente: ${escapeHtml(currency(pendingPayment.amount))}. ` : ''}
          ${risk.stale_hours ? `Sin respuesta desde hace ${escapeHtml(String(Math.round(risk.stale_hours)))} h.` : 'Conversación con seguimiento reciente.'}
        </div>
      </div>
    </div>

    <div class="chat-thread top-space">
      ${(detail.messages || []).map((msg) => `
        <div class="message ${msg.direction === 'internal' ? 'internal' : msg.direction}">
          <div class="muted">${escapeHtml(msg.source || msg.direction)} · ${escapeHtml(formatDate(msg.created_at))}</div>
          <div>${escapeHtml(msg.body)}</div>
        </div>
      `).join('')}
    </div>

    <form id="chat-message-form" class="form-grid">
      <div class="form-group full"><textarea id="chat-message-body" placeholder="Escribe un mensaje..."></textarea></div>
      <div class="form-group"><button type="submit">Enviar manual</button></div>
      <div class="form-group"><button type="button" class="secondary" data-action="send-note">Nota interna</button></div>
    </form>
  `);

  setHtml('#lead-context', `
    <div class="kv-compact">
      <div class="kv-block">
        <div class="kv-block-label">Ficha del cliente</div>
        <div class="kv">
          <div>Nombre</div><div>${escapeHtml(contact.name || '—')}</div>
          <div>Teléfono</div><div>${escapeHtml(contact.phone || '—')}</div>
          <div>Etapa</div><div>${escapeHtml(crmLead.stage || memory.lead_stage || '—')}</div>
          <div>Score</div><div>${number(memory.lead_score || conversation.lead_score || crmLead.score_buying_intent || 0)}</div>
          <div>Interés</div><div>${escapeHtml(memory.interest || '—')}</div>
          <div>Objeciones</div><div>${escapeHtml(memory.objections || (seller.detected_objections || []).join(', ') || '—')}</div>
          <div>Próxima acción</div><div>${escapeHtml(crmLead.next_action || memory.next_action || seller.best_next_action || '—')}</div>
          <div>Follow-up</div><div>${escapeHtml(formatDate(crmLead.followup_at || memory.followup_at))}</div>
        </div>
      </div>

      <div class="kv-block">
        <div class="kv-block-label">Etiquetas</div>
        <div class="inbox-tags">
          ${(humanTags(tags, crmLead, memory, risk)).map((tag) => badge(tag, 'subtle')).join('')}
        </div>
        <form id="tag-form" class="top-space">
          <input id="tag-input" placeholder="nuevo, comparando, listo para cita" value="${escapeHtml(humanTags(tags, crmLead, memory, risk).join(', '))}" />
          <div class="inline-actions top-space compact">
            <button type="button" class="secondary small" data-tag-suggest="nuevo">Nuevo</button>
            <button type="button" class="secondary small" data-tag-suggest="comparando">Comparando</button>
            <button type="button" class="secondary small" data-tag-suggest="listo para cita">Listo para cita</button>
            <button type="button" class="secondary small" data-tag-suggest="pendiente de pago">Pendiente de pago</button>
            <button type="button" class="secondary small" data-tag-suggest="se enfrió">Se enfrió</button>
          </div>
          <div class="top-space"><button type="submit">Guardar etiquetas</button></div>
        </form>
      </div>

      <div class="kv-block">
        <div class="kv-block-label">Línea de tiempo</div>
        ${buildSelectedTimeline(detail)}
      </div>

      <div class="kv-block">
        <div class="kv-block-label">Notas internas</div>
        ${internalNotes(detail)}
      </div>

      <div class="kv-block">
        <div class="kv-block-label">Audios y mensajes largos</div>
        ${recentVoiceSummaries(detail)}
      </div>

      <div class="kv-block">
        <div class="kv-block-label">Acciones rápidas</div>
        <form id="quick-appointment-form" class="form-grid compact-form">
          <div class="form-group full"><label>Agendar cita</label></div>
          <div class="form-group"><input id="quick-appointment-datetime" type="datetime-local" /></div>
          <div class="form-group"><input id="quick-appointment-notes" placeholder="Motivo o detalle" value="${escapeHtml(memory.interest || '')}" /></div>
          <div class="form-group full"><button type="submit">Crear cita</button></div>
        </form>

        <form id="quick-payment-form" class="form-grid compact-form top-space">
          <div class="form-group full"><label>Cobro rápido</label></div>
          <div class="form-group"><input id="quick-payment-title" placeholder="Consulta / servicio" value="${escapeHtml(memory.interest || 'Servicio')}" /></div>
          <div class="form-group"><input id="quick-payment-amount" type="number" placeholder="Monto" value="${escapeHtml(String(crmLead.estimated_amount || ''))}" /></div>
          <div class="form-group full"><button type="submit">Mandar cobro</button></div>
        </form>

        <form id="lead-update-form" class="form-grid compact-form top-space">
          <div class="form-group full"><label>Seguimiento del cliente</label></div>
          <div class="form-group">
            <select id="lead-stage-select">
              ${['nuevo', 'calificado', 'cotizado', 'propuesta', 'agendado', 'pago_pendiente', 'cerrado_ganado', 'cerrado_perdido', 'inactivo'].map((stage) => `<option value="${stage}" ${(crmLead.stage || memory.lead_stage) === stage ? 'selected' : ''}>${stage}</option>`).join('')}
            </select>
          </div>
          <div class="form-group"><input id="lead-followup-input" type="datetime-local" /></div>
          <div class="form-group full"><input id="lead-next-action-input" placeholder="Próximo paso" value="${escapeHtml(crmLead.next_action || memory.next_action || seller.best_next_action || '')}" /></div>
          <div class="form-group full"><select id="lead-lost-reason"><option value="">Motivo de pérdida</option><option value="precio">Precio</option><option value="tiempo">Tiempo</option><option value="duda">Duda</option><option value="falta de seguimiento">Falta de seguimiento</option></select></div>
          <div class="form-group full"><button type="submit">Guardar seguimiento</button></div>
        </form>
      </div>
    </div>
  `);

  const appointmentInput = $('#quick-appointment-datetime');
  if (appointmentInput && !appointmentInput.value) {
    const later = new Date(Date.now() + 86400000);
    later.setHours(11, 0, 0, 0);
    appointmentInput.value = later.toISOString().slice(0, 16);
  }
  const followupInput = $('#lead-followup-input');
  if (followupInput && !followupInput.value) {
    const later = new Date(Date.now() + 86400000);
    later.setHours(12, 0, 0, 0);
    followupInput.value = later.toISOString().slice(0, 16);
  }
  const lostReason = $('#lead-lost-reason');
  if (lostReason) lostReason.value = crmLead.lost_reason || '';
}

async function selectConversation(id, options = {}) {
  state.selectedConversationId = id;
  renderInboxList();
  const detail = await api.safeRequest(`/api/v1/conversations/${id}`, null);
  if (!detail) {
    if (!options.silent) showToast('No pude abrir la conversación.', 'error');
    return;
  }
  const seller = await api.safeRequest(`/api/v1/sales/mode/${id}`, null);
  const history = detail.contact?.id && detail.bot?.id
    ? await api.safeRequest(`/api/v1/contacts/${detail.contact.id}/memory/history?bot_id=${detail.bot.id}`, [])
    : [];
  state.selectedConversation = detail;
  state.selectedConversationSeller = seller;
  state.selectedConversationHistory = history;
  state.conversationCache[id] = detail;
  renderInboxList();
  renderInboxDetail();
}

function renderClients() {
  const totalClients = state.leads.length || state.crmLeads.length;
  const cooling = state.inboxRisk.filter((item) => item.at_risk).slice(0, 6);
  const frequentMap = new Map();
  state.payments.filter((item) => String(item.status || '').toLowerCase() === 'paid').forEach((item) => {
    const key = item.contact_id || item.conversation_id;
    if (!key) return;
    const current = frequentMap.get(key) || { total: 0, count: 0, name: item.contact_name || item.contact_id || 'Cliente' };
    current.total += Number(item.amount || 0);
    current.count += 1;
    current.name = item.contact_name || current.name;
    frequentMap.set(key, current);
  });
  const frequent = Array.from(frequentMap.values()).sort((a, b) => b.total - a.total).slice(0, 6);
  const newToday = state.crmLeads.filter((item) => sameDay(item.created_at)).length;
  const newWeek = state.crmLeads.filter((item) => isWithinLastDays(item.created_at, 7)).length;

  const summaryCards = [
    { label: 'Clientes activos', value: totalClients, sub: `${number(state.conversations.length)} conversaciones vivas` },
    { label: 'Se están enfriando', value: cooling.length, sub: 'Recupéralos antes de perderlos' },
    { label: 'Nuevos hoy', value: newToday, sub: `${number(newWeek)} en la semana` },
    { label: 'Listos para compra', value: state.crmLeads.filter((item) => Number(item.close_probability || 0) >= 70).length, sub: 'Con alta probabilidad de cierre' },
  ];

  setHtml('#clients-summary', summaryCards.map((card) => `
    <div class="card">
      <div class="card-label">${escapeHtml(card.label)}</div>
      <div class="card-value">${number(card.value)}</div>
      <div class="card-subvalue">${escapeHtml(card.sub)}</div>
    </div>
  `).join(''));

  setHtml('#clients-cooling', cooling.length ? `<div class="list">${cooling.map((item) => `
    <div class="list-item">
      <div class="list-item-title">${escapeHtml(item.contact?.name || item.contact?.phone || 'Cliente')}</div>
      <div class="list-item-meta">${escapeHtml(item.bot?.name || 'Bot')} · riesgo ${number(item.risk_score || 0)}</div>
      <div class="muted">${escapeHtml(item.last_inbound || 'Sin mensaje reciente')}</div>
      <div class="list-item-actions"><button class="small secondary" data-open-conversation="${escapeHtml(item.conversation_id)}">Abrir conversación</button></div>
    </div>
  `).join('')}</div>` : emptyState('No hay clientes enfriándose', 'Aquí aparecerán quienes necesitan seguimiento antes de perderse.'));

  setHtml('#clients-frequent', frequent.length ? `<div class="list">${frequent.map((item) => `
    <div class="list-item">
      <div class="list-item-title">${escapeHtml(item.name)}</div>
      <div class="list-item-meta">${number(item.count)} compras · ${currency(item.total)}</div>
    </div>
  `).join('')}</div>` : emptyState('Aún no hay clientes frecuentes', 'Cuando empiecen a repetir compra o cita, aquí se verán primero.'));

  setHtml('#clients-new', `
    <div class="goal-list">
      <div class="goal-item"><div class="goal-header"><strong>Nuevos hoy</strong><span>${number(newToday)}</span></div></div>
      <div class="goal-item"><div class="goal-header"><strong>Nuevos esta semana</strong><span>${number(newWeek)}</span></div></div>
      <div class="goal-item"><div class="goal-header"><strong>Con seguimiento programado</strong><span>${number(state.crmLeads.filter((item) => item.followup_at).length)}</span></div></div>
    </div>
  `);

  const segments = [
    { label: 'Nuevo', total: state.crmLeads.filter((item) => String(item.stage || '').toLowerCase() === 'nuevo').length },
    { label: 'Recurrente', total: frequent.length },
    { label: 'Pendiente', total: state.crmLeads.filter((item) => String(item.stage || '').toLowerCase().includes('pago')).length },
    { label: 'Inactivo', total: state.crmLeads.filter((item) => String(item.stage || '').toLowerCase() === 'inactivo').length },
    { label: 'Listo para compra', total: state.crmLeads.filter((item) => Number(item.close_probability || 0) >= 70).length },
  ];
  setHtml('#client-segments', `<div class="segment-list">${segments.map((segment) => `
    <div class="metric-row">
      <div class="stat-pair"><strong>${escapeHtml(segment.label)}</strong><span>${number(segment.total)}</span></div>
    </div>
  `).join('')}</div>`);

  setHtml('#clients-reactivation', state.reactivation.length ? `<div class="list">${state.reactivation.slice(0, 8).map((item) => `
    <div class="list-item">
      <div class="list-item-title">${escapeHtml(item.segment || 'Oportunidad de reactivación')}</div>
      <div class="list-item-meta">Prioridad ${number(item.priority || 0)} · ${escapeHtml(formatRelative(item.updated_at || item.created_at))}</div>
      <div class="muted">${escapeHtml(item.message || item.recommended_message || item.incentive || 'Conviene retomar esta conversación con una acción simple.')}</div>
    </div>
  `).join('')}</div>` : emptyState('Sin recomendaciones todavía', 'Aquí aparecerán clientes que se pueden recuperar con un buen mensaje.'));

  const rows = state.crmLeads.slice().sort((a, b) => Number(b.close_probability || 0) - Number(a.close_probability || 0));
  setHtml('#clients-table', rows.length ? `
    <div class="table-wrap">
      <table class="table">
        <thead>
          <tr><th>Cliente</th><th>Etapa</th><th>Score</th><th>Compra</th><th>Siguiente paso</th><th>Motivo pérdida</th><th>Contacto</th></tr>
        </thead>
        <tbody>
          ${rows.map((row) => `
            <tr>
              <td>${escapeHtml(row.contact_name || row.contact_phone || 'Cliente')}</td>
              <td>${badge(row.stage || 'nuevo', 'subtle')}</td>
              <td>${number(row.score_buying_intent || row.close_probability || 0)}</td>
              <td>${number(row.close_probability || 0)}%</td>
              <td>${escapeHtml(row.best_next_action || row.next_action || 'Dar seguimiento')}</td>
              <td>${escapeHtml(row.lost_reason || '—')}</td>
              <td>${escapeHtml(row.contact_phone || '—')}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  ` : emptyState('Todavía no hay fichas de clientes', 'Cuando los clientes empiecen a escribir y avanzar en el funnel, aquí verás su historia y próximos pasos.'));
}

function renderAgenda() {
  const appointments = state.appointments.slice().sort((a, b) => new Date(a.scheduled_for || 0) - new Date(b.scheduled_for || 0));
  const todayItems = appointments.filter((item) => sameDay(item.scheduled_for));
  const upcoming = appointments.filter((item) => {
    const dt = dateValue(item.scheduled_for);
    return dt && dt >= startOfDay(new Date()) && dt <= new Date(Date.now() + (7 * 86400000));
  });
  const summaryCards = [
    { label: 'Citas hoy', value: todayItems.length, sub: `${number(state.agendaOverview?.summary?.pending || 0)} por confirmar` },
    { label: 'Confirmadas', value: appointments.filter((item) => String(item.status || '').toLowerCase() === 'confirmed').length, sub: 'Visibles y claras' },
    { label: 'No show', value: appointments.filter((item) => String(item.status || '').toLowerCase() === 'no_show').length, sub: 'Lista lista para recontactar' },
    { label: 'Show rate', value: pct(state.agendaOverview?.summary?.show_rate || 0), sub: 'Asistencia acumulada' },
  ];

  setHtml('#agenda-summary', summaryCards.map((card) => `
    <div class="card">
      <div class="card-label">${escapeHtml(card.label)}</div>
      <div class="card-value">${escapeHtml(card.value)}</div>
      <div class="card-subvalue">${escapeHtml(card.sub)}</div>
    </div>
  `).join(''));

  const grouped = new Map();
  upcoming.forEach((item) => {
    const key = formatDateOnly(item.scheduled_for);
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(item);
  });
  setHtml('#agenda-calendar', grouped.size ? `<div class="calendar-list">${Array.from(grouped.entries()).map(([day, items]) => `
    <div class="calendar-day">
      <div class="calendar-header"><strong>${escapeHtml(day)}</strong><span>${number(items.length)} citas</span></div>
      ${items.map((item) => `
        <div class="calendar-slot">
          <div class="calendar-slot-header">
            <div>
              <div class="list-item-title">${escapeHtml(item.contact_name || item.contact_id || 'Cliente')}</div>
              <div class="calendar-slot-meta">${escapeHtml(formatTime(item.scheduled_for))} · ${escapeHtml(item.timezone || 'MX')}</div>
            </div>
            ${badge(item.status || 'scheduled', String(item.status || '').includes('cancel') ? 'danger' : String(item.status || '').includes('confirm') ? 'success' : 'warning')}
          </div>
          <div class="muted">${escapeHtml(item.notes || 'Sin notas')}</div>
          <div class="inline-actions compact">
            <button class="secondary small" data-appointment-action="confirm" data-appointment-id="${escapeHtml(item.id)}">Confirmar</button>
            <button class="secondary small" data-appointment-action="reschedule" data-appointment-id="${escapeHtml(item.id)}">Reagendar</button>
            <button class="secondary small" data-appointment-action="followup" data-appointment-id="${escapeHtml(item.id)}">Seguimiento</button>
          </div>
        </div>
      `).join('')}
    </div>
  `).join('')}</div>` : emptyState('Todavía no hay agenda', 'Cuando se empiecen a crear citas, aquí verás huecos, cancelaciones y confirmaciones de forma visual.'));

  const pendingToday = todayItems.filter((item) => !['confirmed', 'completed'].includes(String(item.status || '').toLowerCase())).length;
  const byTeam = Object.entries(todayItems.reduce((acc, item) => {
    const key = item.bot_name || item.bot_id || 'Equipo';
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {}));
  setHtml('#agenda-daily', `
    <div class="goal-list">
      <div class="goal-item"><div class="goal-header"><strong>Quién viene hoy</strong><span>${number(todayItems.length)}</span></div></div>
      <div class="goal-item"><div class="goal-header"><strong>Falta confirmar</strong><span>${number(pendingToday)}</span></div></div>
      <div class="goal-item"><div class="goal-header"><strong>Vista por equipo</strong><span>${byTeam.length ? byTeam.map(([name, total]) => `${escapeHtml(name)} (${number(total)})`).join(', ') : 'Sin citas hoy'}</span></div></div>
    </div>
  `);

  const noShow = appointments.filter((item) => String(item.status || '').toLowerCase() === 'no_show');
  const cancelled = appointments.filter((item) => String(item.status || '').toLowerCase() === 'cancelled');
  setHtml('#agenda-risks', (noShow.length || cancelled.length) ? `
    <div class="list">
      ${noShow.map((item) => `
        <div class="list-item">
          <div class="list-item-title">No show · ${escapeHtml(item.contact_name || item.contact_id || 'Cliente')}</div>
          <div class="list-item-meta">${escapeHtml(formatDate(item.scheduled_for))}</div>
          <div class="list-item-actions"><button class="small secondary" data-appointment-action="followup" data-appointment-id="${escapeHtml(item.id)}">Recontactar</button></div>
        </div>
      `).join('')}
      ${cancelled.map((item) => `
        <div class="list-item">
          <div class="list-item-title">Cancelada · ${escapeHtml(item.contact_name || item.contact_id || 'Cliente')}</div>
          <div class="muted">Motivo: ${escapeHtml(parseNoteReason(item.notes) || 'Sin motivo capturado')}</div>
          <div class="list-item-actions"><button class="small secondary" data-appointment-action="reschedule" data-appointment-id="${escapeHtml(item.id)}">Reagendar en un clic</button></div>
        </div>
      `).join('')}
    </div>
  ` : emptyState('Sin no-shows ni cancelaciones', 'Cuando haya citas en riesgo, aquí aparecerán para volver a contactarlas fácil.'));

  const blocked = getBlockedSlots();
  setHtml('#blocked-slots-list', blocked.length ? `<div class="list">${blocked.map((item) => `
    <div class="list-item">
      <div class="list-item-title">${escapeHtml(formatDate(item.start_at))} - ${escapeHtml(formatTime(item.end_at))}</div>
      <div class="list-item-meta">${escapeHtml(item.reason || 'Horario bloqueado')}</div>
      <div class="list-item-actions"><button class="small secondary" data-blocked-remove="${escapeHtml(item.id)}">Quitar</button></div>
    </div>
  `).join('')}</div>` : emptyState('Sin horarios bloqueados', 'Bloquea aquí horas para evitar errores y dar más control al negocio.'));
  fillReminderPrefsForm();
}

function renderPayments() {
  const paid = state.payments.filter((item) => String(item.status || '').toLowerCase() === 'paid');
  const pending = state.payments.filter((item) => String(item.status || '').toLowerCase() !== 'paid');
  const cards = [
    { label: 'Cobrado', value: currency(paid.reduce((acc, item) => acc + Number(item.amount || 0), 0)), sub: `${number(paid.length)} pagos` },
    { label: 'Pendiente', value: currency(pending.reduce((acc, item) => acc + Number(item.amount || 0), 0)), sub: `${number(pending.length)} cobros por recuperar` },
    { label: 'Ventas del día', value: number(paid.filter((item) => sameDay(item.paid_at || item.confirmed_at || item.created_at)).length), sub: 'Compras cerradas hoy' },
    { label: 'Promociones activas', value: number(state.promotions.filter((item) => String(item.status || '').toLowerCase() === 'active').length), sub: 'Más visibles para vender' },
  ];
  setHtml('#payments-summary', cards.map((card) => `
    <div class="card">
      <div class="card-label">${escapeHtml(card.label)}</div>
      <div class="card-value">${escapeHtml(card.value)}</div>
      <div class="card-subvalue">${escapeHtml(card.sub)}</div>
    </div>
  `).join(''));

  setHtml('#payments-table', state.payments.length ? `
    <div class="table-wrap">
      <table class="table">
        <thead>
          <tr><th>Cliente</th><th>Título</th><th>Estado</th><th>Monto</th><th>Creado</th><th>Acciones</th></tr>
        </thead>
        <tbody>
          ${state.payments.map((item) => `
            <tr>
              <td>${escapeHtml(item.contact_name || item.contact_id || 'Cliente')}</td>
              <td>${escapeHtml(item.title || 'Cobro')}</td>
              <td>${badge(item.status || 'pending', String(item.status || '').toLowerCase() === 'paid' ? 'success' : 'warning')}</td>
              <td>${escapeHtml(currency(item.amount))}</td>
              <td>${escapeHtml(formatDate(item.created_at))}</td>
              <td>
                <div class="inline-actions compact">
                  <button class="small secondary" data-payment-action="refresh" data-payment-id="${escapeHtml(item.id)}">Actualizar</button>
                  ${String(item.status || '').toLowerCase() !== 'paid' ? `<button class="small secondary" data-payment-action="remind" data-payment-conversation="${escapeHtml(item.conversation_id || '')}" data-payment-title="${escapeHtml(item.title || 'pago')}" data-payment-amount="${escapeHtml(String(item.amount || 0))}">Recordar</button>` : ''}
                </div>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  ` : emptyState('Sin pagos todavía', 'Aquí verás cobrado, pendiente, vencido y confirmado en una sola vista.'));

  setHtml('#payments-recovery', pending.length ? `<div class="list">${pending.slice(0, 8).map((item) => `
    <div class="list-item">
      <div class="list-item-title">${escapeHtml(item.contact_name || item.contact_id || 'Cliente')}</div>
      <div class="list-item-meta">${escapeHtml(item.title || 'Cobro')} · ${escapeHtml(currency(item.amount))}</div>
      <div class="muted">Conviene retomarlo con un mensaje elegante y CTA claro.</div>
      <div class="list-item-actions">
        <button class="small secondary" data-payment-action="remind" data-payment-conversation="${escapeHtml(item.conversation_id || '')}" data-payment-title="${escapeHtml(item.title || 'pago')}" data-payment-amount="${escapeHtml(String(item.amount || 0))}">Enviar recordatorio</button>
      </div>
    </div>
  `).join('')}</div>` : emptyState('No hay pagos pendientes', 'Cuando alguien casi compre pero no termine, aparecerá aquí para recuperarlo.'));

  const lostCounts = state.crmLeads.reduce((acc, item) => {
    const key = item.lost_reason || 'sin motivo';
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  const lostRows = Object.entries(lostCounts).sort((a, b) => b[1] - a[1]);
  setHtml('#lost-reasons', lostRows.length ? `<div class="list">${lostRows.map(([reason, total]) => `
    <div class="list-item">
      <div class="stat-pair"><strong>${escapeHtml(reason)}</strong><span>${number(total)}</span></div>
    </div>
  `).join('')}</div>` : emptyState('Todavía no hay motivos capturados', 'Cuando registres por qué no compró, aquí verás si fue precio, tiempo, duda o falta de seguimiento.'));

  const promotionBlocks = state.promotions.slice(0, 4).map((item) => `
    <div class="list-item">
      <div class="list-item-title">${escapeHtml(item.name || 'Promoción')}</div>
      <div class="list-item-meta">${escapeHtml(item.status || 'draft')} · ${escapeHtml(item.message_short || item.promo_type || '')}</div>
    </div>
  `).join('');
  const serviceBlocks = state.services.slice(0, 3).map((item) => `
    <div class="list-item">
      <div class="list-item-title">${escapeHtml(item.name)}</div>
      <div class="list-item-meta">${escapeHtml(currency(item.price || 0))} · ${number(item.duration_minutes || 0)} min</div>
    </div>
  `).join('');
  setHtml('#promotions-overview', `<div class="list">${promotionBlocks || emptyState('Sin promociones aún', 'Cuando cargues paquetes o promociones, se verán aquí para ayudar a vender más.')}${serviceBlocks}</div>`);

  const topProducts = state.commerceInsights?.top_products || [];
  setHtml('#service-performance', topProducts.length ? `<div class="list">${topProducts.map((item) => `
    <div class="list-item">
      <div class="stat-pair"><strong>${escapeHtml(item.name)}</strong><span>${number(item.questions || 0)} preguntas</span></div>
      <div class="muted">${number(item.conversions || 0)} conversiones · ${number(item.unanswered || 0)} sin responder</div>
    </div>
  `).join('')}</div>` : emptyState('Sin insight de productos todavía', 'Cuando haya preguntas y ventas por producto o servicio, aquí verás qué se mueve más y qué casi no se mueve.'));
}

function renderReports() {
  const latest = state.reports[0];
  const cards = [
    { label: 'Conversaciones', value: number(state.conversations.length), sub: 'Base del reporte simple' },
    { label: 'Citas', value: number(state.appointments.length), sub: 'Agenda completa' },
    { label: 'Pagos', value: number(state.payments.filter((item) => String(item.status || '').toLowerCase() === 'paid').length), sub: 'Cobros confirmados' },
    { label: 'Clientes recuperados', value: number(state.reactivation.filter((item) => Number(item.priority || 0) >= 80).length), sub: 'Oportunidades fuertes' },
  ];
  setHtml('#reports-summary', cards.map((card) => `
    <div class="card">
      <div class="card-label">${escapeHtml(card.label)}</div>
      <div class="card-value">${escapeHtml(card.value)}</div>
      <div class="card-subvalue">${escapeHtml(card.sub)}</div>
    </div>
  `).join(''));

  setHtml('#reports-highlight', latest ? `
    <div class="kv-block">
      <div class="kv-block-label">Último resumen</div>
      <div class="kv-block-value">
        ${escapeHtml(formatDateOnly(latest.period_start))} a ${escapeHtml(formatDateOnly(latest.period_end))}: ${number(latest.summary?.summary?.leads_entered || latest.summary?.leads_entered || 0)} conversaciones/leads, ${number(latest.summary?.summary?.sales_count || latest.summary?.sales_count || 0)} ventas y ${currency(latest.summary?.summary?.sales_amount || latest.summary?.sales_amount || 0)}.
      </div>
    </div>
  ` : emptyState('Sin reportes generados', 'Genera uno aquí para compartir rápidamente conversaciones, citas, pagos y clientes recuperados.'));

  setHtml('#reports-list', state.reports.length ? `
    <div class="list">
      ${state.reports.map((item) => `
        <div class="list-item">
          <div class="list-item-title">${escapeHtml(formatDateOnly(item.period_start))} - ${escapeHtml(formatDateOnly(item.period_end))}</div>
          <div class="list-item-meta">${number(item.summary?.summary?.sales_count || item.summary?.sales_count || 0)} ventas · ${currency(item.summary?.summary?.sales_amount || item.summary?.sales_amount || 0)}</div>
          <div class="list-item-actions">
            <a class="badge subtle" href="/api/v1/reports/executive/${encodeURIComponent(item.id)}/pdf" target="_blank" rel="noopener">Abrir PDF</a>
          </div>
        </div>
      `).join('')}
    </div>
  ` : emptyState('Todavía no hay reportes', 'Cuando los generes, aquí quedarán listos para compartir con dueño o gerente.'));
}

function renderAutomations() {
  setHtml('#rules-list', state.rules.length ? `
    <div class="list">
      ${state.rules.map((rule) => `
        <div class="list-item">
          <div class="list-item-title">${escapeHtml(rule.name)}</div>
          <div class="list-item-meta">${escapeHtml(rule.rule_type)} · ${escapeHtml(rule.status)}</div>
          <div class="muted">Delay: ${number(rule.config?.delay_minutes || rule.delay_minutes || 0)} min · Max: ${number(rule.config?.max_attempts || rule.max_attempts || 0)}</div>
        </div>
      `).join('')}
    </div>
  ` : emptyState('Sin reglas todavía', 'Crea reglas para no_response, no_show o reactivación y las verás aquí.'));

  setHtml('#jobs-list', state.jobs.length ? `
    <div class="table-wrap"><table class="table"><thead><tr><th>Tipo</th><th>Programado</th><th>Status</th><th>Dedupe</th></tr></thead><tbody>
      ${state.jobs.map((job) => `
        <tr>
          <td>${escapeHtml(job.job_type)}</td>
          <td>${escapeHtml(formatDate(job.scheduled_for))}</td>
          <td>${escapeHtml(job.status)}</td>
          <td>${escapeHtml(job.dedupe_key || '—')}</td>
        </tr>
      `).join('')}
    </tbody></table></div>
  ` : emptyState('Sin jobs en cola', 'Cuando existan follow-ups o procesos pendientes, se verán aquí.'));

  setHtml('#automation-extra', `
    <div class="list">
      <div class="list-item">
        <div class="list-item-title">Alertas configuradas</div>
        <div class="list-item-meta">${number(state.alertsRules.length)} activas</div>
      </div>
      <div class="list-item">
        <div class="list-item-title">Clientes por reactivar</div>
        <div class="list-item-meta">${number(state.reactivation.length)} recomendaciones</div>
      </div>
      <div class="list-item">
        <div class="list-item-title">Recordatorios guardados</div>
        <div class="list-item-meta">${escapeHtml(toneLabel(getReminderPrefs().tone))} · ${number(getReminderPrefs().count)} envíos</div>
      </div>
    </div>
  `);
}

function renderAudit() {
  setHtml('#audit-list', state.auditLogs.length ? `
    <div class="table-wrap">
      <table class="table">
        <thead><tr><th>Fecha</th><th>Acción</th><th>Entidad</th><th>Actor</th><th>Metadata</th></tr></thead>
        <tbody>
          ${state.auditLogs.map((log) => `
            <tr>
              <td>${escapeHtml(formatDate(log.created_at))}</td>
              <td>${escapeHtml(log.action)}</td>
              <td>${escapeHtml(log.entity_type)}</td>
              <td>${escapeHtml(log.actor_type)}</td>
              <td><code class="code-lite">${escapeHtml(JSON.stringify(log.metadata || {}).slice(0, 180))}</code></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  ` : emptyState('Sin logs todavía', 'Cuando haya actividad, aquí verás acciones, actor y metadata.'));
}

async function sendConversationMessage(kind) {
  const body = $('#chat-message-body')?.value?.trim();
  if (!body || !state.selectedConversationId) return;
  await api.request(`/api/v1/conversations/${state.selectedConversationId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ body, kind }),
  });
  $('#chat-message-body').value = '';
  showToast(kind === 'note' ? 'Nota interna guardada.' : 'Mensaje enviado.');
  await refreshAll();
}

async function takeoverConversation() {
  if (!state.selectedConversationId) return;
  await api.request(`/api/v1/conversations/${state.selectedConversationId}/takeover`, {
    method: 'POST',
    body: JSON.stringify({ freeze_minutes: 30 }),
  });
  showToast('La conversación quedó tomada por una persona.');
  await refreshAll();
}

async function reactivateConversation() {
  if (!state.selectedConversationId) return;
  await api.request(`/api/v1/conversations/${state.selectedConversationId}/reactivate-ai`, { method: 'POST' });
  showToast('La IA quedó reactivada.');
  await refreshAll();
}

async function createQuickAppointment() {
  const detail = state.selectedConversation;
  if (!detail) return;
  const scheduledLocal = $('#quick-appointment-datetime')?.value;
  if (!scheduledLocal) {
    showToast('Elige fecha y hora para la cita.', 'error');
    return;
  }
  await api.request('/api/v1/appointments', {
    method: 'POST',
    body: JSON.stringify({
      organization_id: state.currentOrgId,
      bot_id: detail.bot.id,
      conversation_id: detail.conversation.id,
      contact_id: detail.contact.id,
      scheduled_for: new Date(scheduledLocal).toISOString(),
      status: 'scheduled',
      duration_minutes: 30,
      timezone: 'America/Mexico_City',
      notes: $('#quick-appointment-notes')?.value || '',
    }),
  });
  showToast('Cita creada correctamente.');
  await refreshAll();
  await selectConversation(detail.conversation.id, { silent: true });
}

async function createQuickPayment() {
  const detail = state.selectedConversation;
  if (!detail) return;
  const amount = Number($('#quick-payment-amount')?.value || 0);
  if (!amount) {
    showToast('Agrega un monto para enviar el cobro.', 'error');
    return;
  }
  await api.request('/api/v1/sales/payments', {
    method: 'POST',
    body: JSON.stringify({
      organization_id: state.currentOrgId,
      bot_id: detail.bot.id,
      conversation_id: detail.conversation.id,
      contact_id: detail.contact.id,
      title: $('#quick-payment-title')?.value || 'Servicio',
      amount,
      currency: 'MXN',
      reminder_minutes: 60,
      send_receipt_on_confirm: true,
    }),
  });
  showToast('Cobro creado y listo para enviar.');
  await refreshAll();
  await selectConversation(detail.conversation.id, { silent: true });
}

async function saveLeadUpdate() {
  const detail = state.selectedConversation;
  if (!detail) return;
  const nextAction = $('#lead-next-action-input')?.value || '';
  const followupInput = $('#lead-followup-input')?.value;
  const followupAt = followupInput ? new Date(followupInput).toISOString() : null;
  const stage = $('#lead-stage-select')?.value || 'nuevo';
  const lostReason = $('#lead-lost-reason')?.value || null;
  const score = Number(detail.memory?.lead_score || detail.conversation?.lead_score || 0);

  await api.request(`/api/v1/leads/${detail.contact.id}/memory`, {
    method: 'PATCH',
    body: JSON.stringify({
      lead_stage: stage,
      lead_score: score,
      interest: detail.memory?.interest || '',
      objections: detail.memory?.objections || '',
      summary: detail.memory?.summary || state.selectedConversationSummary?.summary || '',
      next_action: nextAction,
      followup_at: followupAt,
    }),
  });

  await api.safeRequest('/api/v1/crm/leads', null, {
    method: 'POST',
    body: JSON.stringify({
      organization_id: state.currentOrgId,
      bot_id: detail.bot.id,
      conversation_id: detail.conversation.id,
      contact_id: detail.contact.id,
      stage,
      estimated_amount: Number($('#quick-payment-amount')?.value || 0) || Number(crmLeadByConversation(detail.conversation)?.estimated_amount || 0) || 0,
      owner_user_id: null,
      next_action: nextAction,
      followup_at: followupAt,
      tags: ($('#tag-input')?.value || '').split(',').map((item) => item.trim()).filter(Boolean),
      notes: detail.memory?.summary || '',
      lost_reason: lostReason,
      language: 'es',
      source_channel: 'whatsapp',
      source_campaign: 'orgánico',
    }),
  });
  showToast('Seguimiento guardado.');
  await refreshAll();
  await selectConversation(detail.conversation.id, { silent: true });
}

async function saveTags() {
  if (!state.selectedConversationId) return;
  const tags = ($('#tag-input')?.value || '').split(',').map((tag) => tag.trim()).filter(Boolean);
  await api.request(`/api/v1/conversations/${state.selectedConversationId}/tags`, {
    method: 'POST',
    body: JSON.stringify({ tags }),
  });
  showToast('Etiquetas actualizadas.');
  await refreshAll();
  await selectConversation(state.selectedConversationId, { silent: true });
}

async function generateConversationSummary() {
  if (!state.selectedConversationId) return;
  const summary = await api.request(`/api/v1/conversations/${state.selectedConversationId}/summary-on-demand`, {
    method: 'POST',
  });
  state.selectedConversationSummary = summary;
  showToast('Resumen generado.');
  renderInboxDetail();
}

async function sendFriendlyReminder() {
  const detail = state.selectedConversation;
  if (!detail) return;
  const name = detail.contact?.name ? `${detail.contact.name}, ` : '';
  const body = `Hola ${name}solo retomo tu consulta para ayudarte a avanzar. Si quieres, hoy mismo te ayudo con cita, propuesta o pago en un solo mensaje.`.trim();
  await api.request(`/api/v1/conversations/${detail.conversation.id}/messages`, {
    method: 'POST',
    body: JSON.stringify({ body, kind: 'text' }),
  });
  showToast('Recordatorio enviado.');
  await refreshAll();
}

async function paymentReminderFromRow(conversationId, title, amount) {
  if (!conversationId) {
    showToast('Este cobro no tiene conversación ligada.', 'error');
    return;
  }
  const body = `Hola, te comparto un recordatorio amable sobre ${title || 'tu pago'} por ${currency(amount || 0)}. Si quieres, te ayudo a completarlo hoy mismo.`;
  await api.request(`/api/v1/conversations/${conversationId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ body, kind: 'text' }),
  });
  showToast('Recordatorio de pago enviado.');
  await refreshAll();
}

async function refreshPaymentStatus(paymentId) {
  await api.request(`/api/v1/sales/payments/${paymentId}/refresh`, { method: 'POST' });
  showToast('Estado de pago actualizado.');
  await refreshAll();
}

async function appointmentAction(action, appointmentId) {
  if (!appointmentId) return;
  if (action === 'reschedule') {
    const when = prompt('Nueva fecha/hora (YYYY-MM-DDTHH:MM):');
    if (!when) return;
    await api.request(`/api/v1/appointments/${appointmentId}/reschedule`, {
      method: 'POST',
      body: JSON.stringify({ scheduled_for: new Date(when).toISOString() }),
    });
  } else if (action === 'confirm') {
    await api.request(`/api/v1/appointments/${appointmentId}/confirm`, {
      method: 'POST',
      body: JSON.stringify({ reason: '' }),
    });
  } else if (action === 'followup') {
    await api.request(`/api/v1/appointments/${appointmentId}/follow-up`, {
      method: 'POST',
      body: JSON.stringify({ reason: '' }),
    });
  } else if (action === 'no-show') {
    await api.request(`/api/v1/appointments/${appointmentId}/no-show`, {
      method: 'POST',
      body: JSON.stringify({ reason: '' }),
    });
  }
  showToast('Acción de cita aplicada.');
  await refreshAll();
}

async function actionPauseResume(botId, action) {
  await api.request(`/api/v1/bots/${botId}/${action}`, { method: 'POST' });
  showToast(action === 'pause' ? 'IA pausada.' : 'IA reanudada.');
  await refreshAll();
}

async function actionCloneBot(botId) {
  await api.request(`/api/v1/bots/${botId}/clone`, {
    method: 'POST',
    body: JSON.stringify({ target_organization_id: state.currentOrgId }),
  });
  showToast('Bot clonado.');
  await refreshAll();
}

async function actionPublish(botId) {
  await api.request(`/api/v1/bots/${botId}/publish`, {
    method: 'POST',
    body: JSON.stringify({ notes: 'Publish desde consola WAOS premium' }),
  });
  showToast('Versión publicada.');
  await refreshAll();
}

function appendSuggestedTag(tag) {
  const input = $('#tag-input');
  if (!input) return;
  const values = input.value.split(',').map((item) => item.trim()).filter(Boolean);
  if (!values.includes(tag)) values.push(tag);
  input.value = values.join(', ');
}

async function saveReminderPrefs() {
  try {
    if (!state.currentOrgId) {
      showToast('Primero elige una organización.', 'error');
      return;
    }
    const prefs = {
      organization_id: state.currentOrgId,
      tone: $('#reminder-tone')?.value || 'amable',
      hours_before: Number($('#reminder-hours-before')?.value || 24),
      last_hours: Number($('#reminder-last-hours')?.value || 2),
      count: Number($('#reminder-count')?.value || 2),
    };
    await api.request('/api/v1/agenda/reminder-preferences', {
      method: 'POST',
      body: JSON.stringify(prefs),
    });
    state.reminderPrefs = {
      tone: prefs.tone,
      hoursBefore: prefs.hours_before,
      lastHours: prefs.last_hours,
      count: prefs.count,
    };
    setStatus($('#reminder-pref-result'), 'Preferencias guardadas en backend.', 'success');
    showToast('Preferencias de recordatorios guardadas.');
    renderAgenda();
  } catch (err) {
    setStatus($('#reminder-pref-result'), err.message || 'No se pudieron guardar las preferencias.', 'danger');
    showToast(err.message || 'No se pudieron guardar las preferencias.', 'error');
  }
}

async function addBlockedSlot() {
  try {
    if (!state.currentOrgId) {
      showToast('Primero elige una organización.', 'error');
      return;
    }
    const start = $('#blocked-start')?.value;
    const end = $('#blocked-end')?.value;
    const reason = $('#blocked-reason')?.value || '';
    if (!start || !end) {
      showToast('Agrega inicio y fin para bloquear horario.', 'error');
      return;
    }
    if (new Date(end) <= new Date(start)) {
      showToast('El fin debe ser después del inicio.', 'error');
      return;
    }
    const created = await api.request('/api/v1/agenda/blocked-slots', {
      method: 'POST',
      body: JSON.stringify({
        organization_id: state.currentOrgId,
        start_at: new Date(start).toISOString(),
        end_at: new Date(end).toISOString(),
        reason,
      }),
    });
    state.blockedSlots = [created, ...state.blockedSlots]
      .sort((a, b) => new Date(a.start_at || 0) - new Date(b.start_at || 0))
      .slice(0, 50);
    showToast('Horario bloqueado.');
    $('#blocked-slot-form').reset();
    renderAgenda();
  } catch (err) {
    showToast(err.message || 'No se pudo bloquear el horario.', 'error');
  }
}

async function removeBlockedSlot(slotId) {
  try {
    await api.request(`/api/v1/agenda/blocked-slots/${slotId}`, { method: 'DELETE' });
    state.blockedSlots = state.blockedSlots.filter((item) => item.id !== slotId);
    showToast('Horario desbloqueado.');
    renderAgenda();
  } catch (err) {
    showToast(err.message || 'No se pudo quitar el bloqueo.', 'error');
  }
}

async function generateReport() {
  const period_start = $('#report-start')?.value;
  const period_end = $('#report-end')?.value;
  if (!period_start || !period_end) {
    showToast('Elige inicio y fin del reporte.', 'error');
    return;
  }
  await api.request('/api/v1/reports/executive/generate', {
    method: 'POST',
    body: JSON.stringify({
      organization_id: state.currentOrgId,
      bot_id: null,
      period_start,
      period_end,
      delivery_channels: ['pdf'],
    }),
  });
  setStatus($('#report-form-result'), 'Reporte generado correctamente.', 'success');
  showToast('Reporte generado.');
  await refreshAll();
}

async function createBotFromForm() {
  const faqs = $('#bot-faqs').value.split(';').map((item) => item.trim()).filter(Boolean).map((item) => {
    const [q, a] = item.split('|').map((part) => part.trim());
    return { q, a };
  });
  await api.request('/api/v1/bots', {
    method: 'POST',
    body: JSON.stringify({
      organization_id: $('#bot-org-id').value,
      business_name: $('#bot-business-name').value,
      vertical: $('#bot-vertical').value,
      bot_name: $('#bot-name').value,
      primary_objective: $('#bot-objective').value,
      tone: $('#bot-tone').value,
      language: $('#bot-language').value,
      timezone: $('#bot-timezone').value,
      services: $('#bot-services').value.split(',').map((v) => v.trim()).filter(Boolean),
      hours: $('#bot-hours').value,
      faqs,
      whatsapp_number: $('#bot-whatsapp').value,
      publish_now: $('#bot-publish').value === 'true',
    }),
  });
  setStatus($('#bot-form-result'), 'Bot creado. WhatsApp queda pendiente de conexión hasta validar Meta y webhook.', 'success');
  showToast('Bot creado. WhatsApp pendiente de conexión.');
  await refreshAll();
}

async function createOrganizationFromForm() {
  try {
    await api.request('/api/v1/organizations', {
      method: 'POST',
      body: JSON.stringify({
        name: $('#org-name').value,
        vertical: $('#org-vertical').value,
        timezone: $('#org-timezone').value,
      }),
    });
    state.user = await api.request('/api/v1/auth/me');
    state.organizations = state.user.organizations || [];
    state.currentOrgId = state.organizations[state.organizations.length - 1]?.id || state.currentOrgId;
    renderOrgSelectors();
    setStatus($('#org-form-result'), 'Organización creada.', 'success');
    showToast('Organización creada.');
    await refreshAll();
  } catch (err) {
    setStatus($('#org-form-result'), err.message, 'error');
  }
}

async function createRuleFromForm() {
  await api.request('/api/v1/automations/rules', {
    method: 'POST',
    body: JSON.stringify({
      organization_id: $('#rule-org-id').value,
      bot_id: $('#rule-bot-id').value,
      rule_type: $('#rule-type').value,
      name: $('#rule-name').value,
      status: 'active',
      delay_minutes: Number($('#rule-delay').value),
      max_attempts: Number($('#rule-attempts').value),
      message_template: $('#rule-message').value,
    }),
  });
  setStatus($('#rule-form-result'), 'Regla creada.', 'success');
  showToast('Regla creada.');
  await refreshAll();
}

async function processJobs() {
  await api.request('/api/v1/automations/process-due', { method: 'POST' });
  showToast('Jobs procesados.');
  await refreshAll();
}

async function saveSettingsForm() {
  await api.request('/api/v1/settings/global', {
    method: 'POST',
    body: JSON.stringify({
      global_policy: $('#global-policy').value,
      default_model: $('#global-model').value,
      freeze_minutes_after_takeover: Number($('#global-freeze').value),
      ai_optimization: JSON.parse($('#ai-optimization-json').value || '{}'),
      memory_runtime: JSON.parse($('#memory-runtime-json').value || '{}'),
    }),
  });
  setStatus($('#settings-result'), 'Settings guardados.', 'success');
  showToast('Settings guardados.');
}

async function simulateInbound() {
  await api.request('/api/v1/simulate/inbound', {
    method: 'POST',
    body: JSON.stringify({
      bot_id: $('#simulate-bot-id').value,
      phone: $('#simulate-phone').value,
      name: $('#simulate-name').value,
      body: $('#simulate-body').value,
    }),
  });
  setStatus($('#simulate-result'), 'Inbound simulado.', 'success');
  showToast('Mensaje simulado.');
  await refreshAll();
}

function bindEvents() {
  $('#login-btn')?.addEventListener('click', login);
  $('#logout-btn')?.addEventListener('click', () => {
    localStorage.removeItem('waos_token');
    location.reload();
  });
  $('#refresh-btn')?.addEventListener('click', refreshAll);
  $('#org-filter')?.addEventListener('change', async (e) => {
    state.currentOrgId = e.target.value;
    renderOrgSelectors();
    await refreshAll();
  });
  $('#global-search')?.addEventListener('input', (e) => {
    state.globalSearchQuery = e.target.value || '';
    renderInboxList();
  });
  $('#inbox-search')?.addEventListener('input', (e) => {
    state.inboxQuery = e.target.value || '';
    renderInboxList();
  });

  document.addEventListener('click', async (event) => {
    const nav = event.target.closest('.nav-item');
    if (nav) {
      showSection(nav.dataset.section);
      return;
    }
    const conversationCard = event.target.closest('[data-conversation-id]');
    if (conversationCard) {
      await selectConversation(conversationCard.dataset.conversationId);
      return;
    }
    const filter = event.target.closest('[data-inbox-filter]');
    if (filter) {
      state.inboxFilter = filter.dataset.inboxFilter;
      $$('#inbox-filter-chips .chip').forEach((el) => el.classList.toggle('active', el.dataset.inboxFilter === state.inboxFilter));
      renderInboxList();
      return;
    }
    const quickSection = event.target.closest('[data-quick-section]');
    if (quickSection) {
      showSection(quickSection.dataset.quickSection);
      return;
    }
    const openConversation = event.target.closest('[data-open-conversation]');
    if (openConversation) {
      showSection('inbox');
      await selectConversation(openConversation.dataset.openConversation);
      return;
    }
    const botAction = event.target.closest('[data-bot-action]');
    if (botAction) {
      const botId = botAction.dataset.botId;
      if (botAction.dataset.botAction === 'pause-resume') await actionPauseResume(botId, botAction.dataset.botNext);
      if (botAction.dataset.botAction === 'clone') await actionCloneBot(botId);
      if (botAction.dataset.botAction === 'publish') await actionPublish(botId);
      return;
    }
    const paymentAction = event.target.closest('[data-payment-action]');
    if (paymentAction) {
      if (paymentAction.dataset.paymentAction === 'refresh') await refreshPaymentStatus(paymentAction.dataset.paymentId);
      if (paymentAction.dataset.paymentAction === 'remind') await paymentReminderFromRow(paymentAction.dataset.paymentConversation, paymentAction.dataset.paymentTitle, paymentAction.dataset.paymentAmount);
      return;
    }
    const appointmentActionBtn = event.target.closest('[data-appointment-action]');
    if (appointmentActionBtn) {
      await appointmentAction(appointmentActionBtn.dataset.appointmentAction, appointmentActionBtn.dataset.appointmentId);
      return;
    }
    const blockedRemove = event.target.closest('[data-blocked-remove]');
    if (blockedRemove) {
      await removeBlockedSlot(blockedRemove.dataset.blockedRemove);
      return;
    }
    const tagSuggest = event.target.closest('[data-tag-suggest]');
    if (tagSuggest) {
      appendSuggestedTag(tagSuggest.dataset.tagSuggest);
      return;
    }
    const action = event.target.closest('[data-action]');
    if (action) {
      if (action.dataset.action === 'takeover-conversation') await takeoverConversation();
      if (action.dataset.action === 'reactivate-conversation') await reactivateConversation();
      if (action.dataset.action === 'generate-summary') await generateConversationSummary();
      if (action.dataset.action === 'send-friendly-reminder') await sendFriendlyReminder();
      if (action.dataset.action === 'send-note') await sendConversationMessage('note');
      if (action.dataset.action === 'open-appointment-form') document.querySelector('#quick-appointment-form')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      if (action.dataset.action === 'open-payment-form') document.querySelector('#quick-payment-form')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      if (action.dataset.action === 'open-lead-form') document.querySelector('#lead-update-form')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }
  });

  document.addEventListener('submit', async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    event.preventDefault();
    if (form.id === 'bot-form') await createBotFromForm();
    if (form.id === 'organization-form') await createOrganizationFromForm();
    if (form.id === 'simulate-form') await simulateInbound();
    if (form.id === 'rule-form') await createRuleFromForm();
    if (form.id === 'settings-form') await saveSettingsForm();
    if (form.id === 'report-form') await generateReport();
    if (form.id === 'chat-message-form') await sendConversationMessage('text');
    if (form.id === 'quick-appointment-form') await createQuickAppointment();
    if (form.id === 'quick-payment-form') await createQuickPayment();
    if (form.id === 'lead-update-form') await saveLeadUpdate();
    if (form.id === 'tag-form') await saveTags();
    if (form.id === 'reminder-pref-form') await saveReminderPrefs();
    if (form.id === 'blocked-slot-form') await addBlockedSlot();
  });

  $('#process-jobs-btn')?.addEventListener('click', processJobs);
}

bindEvents();
bootstrap();

window.selectConversation = selectConversation;
window.sendConversationMessage = sendConversationMessage;
window.takeoverConversation = takeoverConversation;
window.reactivateConversation = reactivateConversation;
