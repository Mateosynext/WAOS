const state = {
  token: localStorage.getItem('waos_token') || '',
  user: null,
  organizations: [],
  currentOrgId: '',
  bots: [],
  conversations: [],
  selectedConversationId: '',
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
};

const $ = (selector) => document.querySelector(selector);

function setStatus(el, text, type = 'muted') {
  el.textContent = text;
  el.className = type;
}

function moneyBadge(value) {
  return `<span class="badge">${value}</span>`;
}

function showSection(name) {
  document.querySelectorAll('.section').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  $(`#section-${name}`).classList.add('active');
  document.querySelector(`.nav-item[data-section="${name}"]`).classList.add('active');
  $('#section-title').textContent = document.querySelector(`.nav-item[data-section="${name}"]`).textContent;
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
    $('#login-error').textContent = '';
    await bootstrap();
  } catch (err) {
    $('#login-error').textContent = err.message;
  }
}

async function bootstrap() {
  if (!state.token) return;
  try {
    state.user = await api.request('/api/v1/auth/me');
    state.organizations = state.user.organizations || [];
    state.currentOrgId = state.organizations[0]?.id || '';
    $('#current-user').textContent = `${state.user.full_name} · ${state.user.global_role}`;
    $('#login-screen').classList.add('hidden');
    $('#app-shell').classList.remove('hidden');
    renderOrgSelectors();
    await refreshAll();
  } catch (err) {
    console.error(err);
    localStorage.removeItem('waos_token');
    state.token = '';
    $('#login-screen').classList.remove('hidden');
    $('#app-shell').classList.add('hidden');
  }
}

function renderOrgSelectors() {
  const selects = ['#org-filter', '#bot-org-id', '#rule-org-id'];
  selects.forEach(selector => {
    const el = $(selector);
    if (!el) return;
    el.innerHTML = '';
    state.organizations.forEach(org => {
      const option = document.createElement('option');
      option.value = org.id;
      option.textContent = org.name;
      if (org.id === state.currentOrgId) option.selected = true;
      el.appendChild(option);
    });
  });
}

async function refreshAll() {
  await Promise.all([
    loadDashboard(),
    loadBots(),
    loadConversations(),
    loadLeads(),
    loadRulesAndJobs(),
    loadAudit(),
    loadSettings(),
  ]);
}

async function loadDashboard() {
  const query = state.currentOrgId ? `?organization_id=${state.currentOrgId}` : '';
  const data = await api.request(`/api/v1/analytics/dashboard${query}`);
  const cards = data.summary;
  $('#dashboard-cards').innerHTML = Object.entries(cards).map(([key, value]) => `
    <div class="card">
      <div class="card-label">${key.replaceAll('_', ' ')}</div>
      <div class="card-value">${value ?? '—'}</div>
    </div>
  `).join('');
  $('#dashboard-bots').innerHTML = `
    <table class="table">
      <thead>
        <tr><th>Bot</th><th>Estado</th><th>IA</th><th>Conv. activas</th></tr>
      </thead>
      <tbody>
        ${data.bots.map(bot => `
          <tr>
            <td>${bot.name}</td>
            <td>${moneyBadge(bot.status)}</td>
            <td>${bot.ai_paused ? 'Pausada' : 'Activa'}</td>
            <td>${bot.conversations_active}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

async function loadBots() {
  const query = state.currentOrgId ? `?organization_id=${state.currentOrgId}` : '';
  state.bots = await api.request(`/api/v1/bots${query}`);
  const html = `
    <div class="list">
      ${state.bots.map(bot => `
        <div class="list-item">
          <div class="list-item-title">${bot.name}</div>
          <div class="list-item-meta">${bot.business_name} · ${bot.phone_number || 'sin número'} · ${bot.status}</div>
          <div class="list-item-actions">
            <button class="small secondary" onclick="actionPauseResume('${bot.id}', ${bot.ai_paused ? "'resume'" : "'pause'"})">${bot.ai_paused ? 'Reanudar IA' : 'Pausar IA'}</button>
            <button class="small secondary" onclick="actionCloneBot('${bot.id}')">Clonar</button>
            <button class="small secondary" onclick="actionPublish('${bot.id}')">Publicar versión</button>
          </div>
        </div>
      `).join('')}
    </div>
  `;
  $('#bots-list').innerHTML = html;
  fillBotSelectors();
}

function fillBotSelectors() {
  ['#simulate-bot-id', '#rule-bot-id'].forEach(selector => {
    const el = $(selector);
    if (!el) return;
    el.innerHTML = '';
    state.bots.forEach(bot => {
      const option = document.createElement('option');
      option.value = bot.id;
      option.textContent = `${bot.name} · ${bot.business_name}`;
      el.appendChild(option);
    });
  });
}

async function loadConversations() {
  const query = state.currentOrgId ? `?organization_id=${state.currentOrgId}` : '';
  state.conversations = await api.request(`/api/v1/conversations${query}`);
  $('#conversation-list').innerHTML = `
    <div class="list">
      ${state.conversations.map(conv => `
        <div class="list-item" onclick="selectConversation('${conv.id}')">
          <div class="list-item-title">${conv.contact_name || conv.contact_phone}</div>
          <div class="list-item-meta">${conv.bot_name} · ${conv.status} · score ${conv.lead_score ?? 0}</div>
          <div class="muted">${conv.summary || ''}</div>
        </div>
      `).join('')}
    </div>
  `;
  if (!state.selectedConversationId && state.conversations[0]) {
    await selectConversation(state.conversations[0].id);
  }
}

async function selectConversation(id) {
  state.selectedConversationId = id;
  const data = await api.request(`/api/v1/conversations/${id}`);
  $('#conversation-detail').innerHTML = `
    <div class="chat-thread">
      ${data.messages.map(msg => `
        <div class="message ${msg.direction === 'internal' ? 'internal' : msg.direction}">
          <div class="muted">${msg.source} · ${msg.created_at}</div>
          <div>${msg.body}</div>
        </div>
      `).join('')}
    </div>
    <form onsubmit="event.preventDefault(); sendConversationMessage('text');" class="form-grid">
      <div class="form-group full"><textarea id="chat-message-body" placeholder="Escribe un mensaje..."></textarea></div>
      <div class="form-group"><button type="submit">Enviar manual</button></div>
      <div class="form-group"><button type="button" class="secondary" onclick="sendConversationMessage('note')">Nota interna</button></div>
    </form>
    <div class="inline-actions top-space">
      <button class="secondary" onclick="takeoverConversation()">Tomar</button>
      <button class="secondary" onclick="reactivateConversation()">Reactivar IA</button>
    </div>
  `;
  const lead = data.memory || {};
  $('#lead-context').innerHTML = `
    <div class="kv">
      <div>Nombre</div><div>${data.contact?.name || '—'}</div>
      <div>Teléfono</div><div>${data.contact?.phone || '—'}</div>
      <div>Etapa</div><div>${lead.lead_stage || '—'}</div>
      <div>Score</div><div>${lead.lead_score ?? '—'}</div>
      <div>Interés</div><div>${lead.interest || '—'}</div>
      <div>Objeciones</div><div>${lead.objections || '—'}</div>
      <div>Resumen</div><div>${lead.summary || '—'}</div>
      <div>Próxima acción</div><div>${lead.next_action || '—'}</div>
      <div>Follow-up</div><div>${lead.followup_at || '—'}</div>
    </div>
  `;
}

async function sendConversationMessage(kind) {
  const body = $('#chat-message-body').value;
  if (!body) return;
  await api.request(`/api/v1/conversations/${state.selectedConversationId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ body, kind }),
  });
  $('#chat-message-body').value = '';
  await loadConversations();
  await selectConversation(state.selectedConversationId);
  await loadAudit();
}

async function takeoverConversation() {
  await api.request(`/api/v1/conversations/${state.selectedConversationId}/takeover`, {
    method: 'POST',
    body: JSON.stringify({ freeze_minutes: 30 }),
  });
  await loadConversations();
  await selectConversation(state.selectedConversationId);
}

async function reactivateConversation() {
  await api.request(`/api/v1/conversations/${state.selectedConversationId}/reactivate-ai`, {
    method: 'POST',
  });
  await loadConversations();
  await selectConversation(state.selectedConversationId);
}

async function loadLeads() {
  const query = state.currentOrgId ? `?organization_id=${state.currentOrgId}` : '';
  const leads = await api.request(`/api/v1/leads${query}`);
  $('#leads-table').innerHTML = `
    <table class="table">
      <thead>
        <tr>
          <th>Nombre</th><th>Teléfono</th><th>Bot</th><th>Etapa</th><th>Score</th><th>Interés</th><th>Objeciones</th><th>Próxima acción</th>
        </tr>
      </thead>
      <tbody>
        ${leads.map(lead => `
          <tr>
            <td>${lead.contact_name || '—'}</td>
            <td>${lead.contact_phone}</td>
            <td>${lead.bot_name}</td>
            <td>${lead.lead_stage}</td>
            <td>${lead.lead_score}</td>
            <td>${lead.interest || '—'}</td>
            <td>${lead.objections || '—'}</td>
            <td>${lead.next_action || '—'}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

async function loadRulesAndJobs() {
  const orgQuery = state.currentOrgId ? `?organization_id=${state.currentOrgId}` : '';
  const rules = await api.request(`/api/v1/automations/rules${orgQuery}`);
  const jobs = await api.request(`/api/v1/automations/jobs${orgQuery}`);
  $('#rules-list').innerHTML = `
    <div class="list">
      ${rules.map(rule => `
        <div class="list-item">
          <div class="list-item-title">${rule.name}</div>
          <div class="list-item-meta">${rule.rule_type} · ${rule.status}</div>
          <div class="muted">Delay: ${rule.config.delay_minutes} min · Max: ${rule.config.max_attempts}</div>
        </div>
      `).join('')}
    </div>
  `;
  $('#jobs-list').innerHTML = `
    <table class="table">
      <thead>
        <tr><th>Tipo</th><th>Programado</th><th>Status</th><th>Dedupe</th></tr>
      </thead>
      <tbody>
        ${jobs.map(job => `
          <tr>
            <td>${job.job_type}</td>
            <td>${job.scheduled_for}</td>
            <td>${job.status}</td>
            <td>${job.dedupe_key || '—'}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

async function loadAudit() {
  const query = state.currentOrgId ? `?organization_id=${state.currentOrgId}` : '';
  const logs = await api.request(`/api/v1/audit/logs${query}`);
  $('#audit-list').innerHTML = `
    <table class="table">
      <thead>
        <tr><th>Fecha</th><th>Acción</th><th>Entidad</th><th>Actor</th><th>Metadata</th></tr>
      </thead>
      <tbody>
        ${logs.map(log => `
          <tr>
            <td>${log.created_at}</td>
            <td>${log.action}</td>
            <td>${log.entity_type}</td>
            <td>${log.actor_type}</td>
            <td><code>${JSON.stringify(log.metadata).slice(0, 140)}</code></td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

async function loadSettings() {
  try {
    const data = await api.request('/api/v1/settings/global');
    $('#global-policy').value = data.global_policy || '';
    $('#global-model').value = data.default_model || '';
    $('#global-freeze').value = data.freeze_minutes_after_takeover || 30;
  } catch (err) {
    $('#section-settings').innerHTML = '<div class="panel"><div class="muted">Solo Super Admin puede ver settings globales.</div></div>';
  }
}

async function actionPauseResume(botId, action) {
  await api.request(`/api/v1/bots/${botId}/${action}`, { method: 'POST' });
  await loadBots();
  await loadDashboard();
}

async function actionCloneBot(botId) {
  await api.request(`/api/v1/bots/${botId}/clone`, {
    method: 'POST',
    body: JSON.stringify({ target_organization_id: state.currentOrgId }),
  });
  await loadBots();
}

async function actionPublish(botId) {
  await api.request(`/api/v1/bots/${botId}/publish`, {
    method: 'POST',
    body: JSON.stringify({ notes: 'Publish desde consola WAOS' }),
  });
  await loadBots();
  await loadAudit();
}

document.addEventListener('click', (event) => {
  const button = event.target.closest('.nav-item');
  if (button) showSection(button.dataset.section);
});

$('#login-btn').addEventListener('click', login);
$('#logout-btn').addEventListener('click', () => {
  localStorage.removeItem('waos_token');
  location.reload();
});
$('#refresh-btn').addEventListener('click', refreshAll);
$('#org-filter').addEventListener('change', async (e) => {
  state.currentOrgId = e.target.value;
  renderOrgSelectors();
  await refreshAll();
});

$('#bot-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const faqs = $('#bot-faqs').value.split(';').map(item => item.trim()).filter(Boolean).map(item => {
    const [q, a] = item.split('|').map(part => part.trim());
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
      services: $('#bot-services').value.split(',').map(v => v.trim()).filter(Boolean),
      hours: $('#bot-hours').value,
      faqs,
      whatsapp_number: $('#bot-whatsapp').value,
      publish_now: $('#bot-publish').value === 'true',
    }),
  });
  setStatus($('#bot-form-result'), 'Bot creado correctamente', 'success');
  await loadBots();
  await loadDashboard();
});

$('#organization-form').addEventListener('submit', async (event) => {
  event.preventDefault();
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
    setStatus($('#org-form-result'), 'Organización creada', 'success');
    await refreshAll();
  } catch (err) {
    setStatus($('#org-form-result'), err.message, 'error');
  }
});

$('#simulate-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  await api.request('/api/v1/simulate/inbound', {
    method: 'POST',
    body: JSON.stringify({
      bot_id: $('#simulate-bot-id').value,
      phone: $('#simulate-phone').value,
      name: $('#simulate-name').value,
      body: $('#simulate-body').value,
    }),
  });
  setStatus($('#simulate-result'), 'Inbound simulado', 'success');
  await loadConversations();
  await loadLeads();
  await loadDashboard();
  await loadAudit();
});

$('#rule-form').addEventListener('submit', async (event) => {
  event.preventDefault();
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
  setStatus($('#rule-form-result'), 'Regla creada', 'success');
  await loadRulesAndJobs();
  await loadAudit();
});

$('#process-jobs-btn').addEventListener('click', async () => {
  await api.request('/api/v1/automations/process-due', { method: 'POST' });
  await loadRulesAndJobs();
  await loadAudit();
});

$('#settings-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  await api.request('/api/v1/settings/global', {
    method: 'POST',
    body: JSON.stringify({
      global_policy: $('#global-policy').value,
      default_model: $('#global-model').value,
      freeze_minutes_after_takeover: Number($('#global-freeze').value),
    }),
  });
  setStatus($('#settings-result'), 'Settings guardados', 'success');
});

bootstrap();
window.selectConversation = selectConversation;
window.sendConversationMessage = sendConversationMessage;
window.takeoverConversation = takeoverConversation;
window.reactivateConversation = reactivateConversation;
window.actionPauseResume = actionPauseResume;
window.actionCloneBot = actionCloneBot;
window.actionPublish = actionPublish;
