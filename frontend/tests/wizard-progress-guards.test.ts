import test from 'node:test';
import assert from 'node:assert/strict';
import {
  canAdvanceAfterCreateSave,
  canEnterWizardRoute,
  getCreateClientIncompleteMessage,
  isCreateStepClientReady,
  isSnapshotApplyReady,
  isWizardValidationFresh,
  resolveCreateBlockingRoute,
} from '../features/bot-studio/domain/wizardProgressGuards';

test('create client readiness enforces the required fields for identity, offer, knowledge and integrations', () => {
  assert.equal(isCreateStepClientReady('identity', { businessName: 'Clínica Norte', botName: 'Bot Norte', tone: 'amable', language: 'es', timezone: 'America/Mexico_City' }), true);
  assert.equal(isCreateStepClientReady('identity', { businessName: 'Clínica Norte', botName: 'Bot Norte', tone: '', language: 'es', timezone: 'America/Mexico_City' }), false);
  assert.equal(isCreateStepClientReady('offer', { servicesText: 'Consulta inicial', primaryCtasText: 'Agendar valoración' }), true);
  assert.equal(isCreateStepClientReady('offer', { servicesText: 'Consulta inicial', primaryCtasText: '' }), false);
  assert.equal(isCreateStepClientReady('knowledge', { faqText: '¿Atienden sábados? | Sí', policiesText: 'No prometer diagnóstico', knowledgeSourcesText: 'Drive operativa' }), true);
  assert.equal(isCreateStepClientReady('knowledge', { faqText: '¿Atienden sábados? | Sí, con cita previa', policiesText: 'No prometer diagnóstico', knowledgeSourcesText: 'Drive operativo' }), true);
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

test('snapshot apply readiness also requires the validated wizard revision when provided', () => {
  const greenSnapshot = { gate: { status: 'green' } } as never;
  assert.equal(isWizardValidationFresh({ wizardRevision: 7, validatedWizardRevision: 7 }), true);
  assert.equal(isWizardValidationFresh({ wizardRevision: 7, validatedWizardRevision: 6 }), false);
  assert.equal(isSnapshotApplyReady(greenSnapshot, { wizardRevision: 7, validatedWizardRevision: 6 }), false);
  assert.equal(isSnapshotApplyReady(greenSnapshot, { wizardRevision: 7, validatedWizardRevision: 7 }), true);
});

test('wizard route guards block direct create apply when the dry run belongs to an old revision', () => {
  const guard = canEnterWizardRoute({
    mode: 'create',
    routeStep: 'apply',
    state: {
      selectedOrganizationId: 'org_1',
      selectedVerticalId: 'clinicas',
      selectedSubvertical: 'dental',
      businessName: 'Clínica Norte',
      botName: 'Bot Norte',
      tone: 'amable',
      language: 'es',
      timezone: 'America/Mexico_City',
      servicesText: 'Consulta inicial',
      primaryCtasText: 'Agendar valoración',
      faqText: '¿Atienden sábados? | Sí',
      policiesText: 'No prometer diagnóstico',
      knowledgeSourcesText: 'Drive operativa',
      selectedIntegrationKeys: ['whatsapp'],
      escalateWhenText: 'Urgencia',
    },
    wizard: { id: 'wiz_1', organization_id: 'org_1', status: 'draft', wizard_revision: 3 } as never,
    snapshot: { gate: { status: 'green' } } as never,
    validatedWizardRevision: 2,
  });
  assert.equal(guard.ok, false);
  if (!guard.ok) {
    assert.equal(guard.blockingRoute, 'validate');
    assert.equal(guard.reason, 'missing_fresh_validation');
  }
});

test('wizard route guards block direct reconfigure confirm without a fresh dry run', () => {
  const guard = canEnterWizardRoute({
    mode: 'reconfigure',
    routeStep: 'confirm',
    selectedBotId: 'bot_1',
    wizard: { id: 'wiz_2', organization_id: 'org_1', bot_id: 'bot_1', status: 'draft', wizard_revision: 9 } as never,
    snapshot: { apply_ready: true, gate: { status: 'green' } } as never,
    validatedWizardRevision: 8,
  });
  assert.equal(guard.ok, false);
  if (!guard.ok) {
    assert.equal(guard.blockingRoute, 'dry-run');
    assert.equal(guard.reason, 'missing_fresh_validation');
  }
});

test('frontend copy for partial saves stays explicit', () => {
  const message = getCreateClientIncompleteMessage('offer');
  assert.match(message.title, /Oferta guardada parcialmente/i);
  assert.match(message.detail, /CTA principal/i);
});
