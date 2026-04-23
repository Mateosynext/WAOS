import test from 'node:test';
import assert from 'node:assert/strict';
import { canAdvanceAfterCreateSave, getCreateClientIncompleteMessage, isCreateStepClientReady, isSnapshotApplyReady, resolveCreateBlockingRoute } from '../app/bot-studio/wizardProgressGuards';

test('create client readiness enforces the required fields for identity, offer, knowledge and integrations', () => {
  assert.equal(isCreateStepClientReady('identity', { businessName: 'Clínica Norte', botName: 'Bot Norte', tone: 'amable', language: 'es', timezone: 'America/Mexico_City' }), true);
  assert.equal(isCreateStepClientReady('identity', { businessName: 'Clínica Norte', botName: 'Bot Norte', tone: '', language: 'es', timezone: 'America/Mexico_City' }), false);
  assert.equal(isCreateStepClientReady('offer', { servicesText: 'Consulta inicial', primaryCtasText: 'Agendar valoración' }), true);
  assert.equal(isCreateStepClientReady('offer', { servicesText: 'Consulta inicial', primaryCtasText: '' }), false);
  assert.equal(isCreateStepClientReady('knowledge', { faqText: '¿Atienden sábados? | Sí', policiesText: 'No prometer diagnóstico', knowledgeSourcesText: 'Drive operativa' }), true);
  assert.equal(isCreateStepClientReady('knowledge', { faqText: 'FAQ inválida sin separador', policiesText: 'No prometer diagnóstico', knowledgeSourcesText: 'Drive operativa' }), false);
  assert.equal(isCreateStepClientReady('integrations', { selectedIntegrationKeys: ['whatsapp'], escalateWhenText: 'Urgencia' }), true);
  assert.equal(isCreateStepClientReady('integrations', { selectedIntegrationKeys: [], escalateWhenText: 'Urgencia' }), false);
});

test('create save stays on the same route when the backend keeps the wizard in the same required step', () => {
  assert.equal(resolveCreateBlockingRoute({ current_step: 'business_basics' } as never), 'identity');
  assert.deepEqual(canAdvanceAfterCreateSave('identity', { current_step: 'business_basics' } as never), { ok: false, blockingRoute: 'identity' });
  assert.deepEqual(canAdvanceAfterCreateSave('offer', { current_step: 'knowledge_seed' } as never), { ok: true, blockingRoute: null });
  assert.deepEqual(canAdvanceAfterCreateSave('review', { current_step: 'launch_review' } as never), { ok: true, blockingRoute: null });
});

test('snapshot apply readiness only opens apply for green or explicitly ready validation', () => {
  assert.equal(isSnapshotApplyReady(null), false);
  assert.equal(isSnapshotApplyReady({ gate: { status: 'yellow' } } as never), false);
  assert.equal(isSnapshotApplyReady({ gate: { status: 'green' } } as never), true);
  assert.equal(isSnapshotApplyReady({ apply_ready: true, gate: { status: 'red' } } as never), true);
});

test('frontend copy for partial saves stays explicit', () => {
  const message = getCreateClientIncompleteMessage('offer');
  assert.match(message.title, /Oferta guardada parcialmente/i);
  assert.match(message.detail, /CTA principal/i);
});
