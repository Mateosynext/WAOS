import { readFileSync, existsSync } from 'node:fs';
const read = (p) => readFileSync(p, 'utf8');
const checks = [];
function check(name, ok) { checks.push([name, !!ok]); if (!ok) console.error('FAIL', name); }
const api = read('backend/app/api/routers/ai_workflows.py');
const service = read('backend/app/ai_workflows/bot_autopilot/service.py');
const persistence = read('backend/app/ai_workflows/persistence.py');
const center = read('frontend/features/ai-command-center/AiCommandCenter.tsx');
const stream = read('frontend/features/ai-command-center/useAiWorkflowStream.ts');
const assistant = read('frontend/features/bot-studio/create/AiSetupAssistant.tsx');
check('async endpoint uses BackgroundTasks', api.includes('BackgroundTasks') && api.includes('async_mode: bool = Query(True)'));
check('workflow background runner exists', service.includes('run_bot_autopilot_background') && service.includes('execute_bot_autopilot_run'));
check('SSE polls until terminal', api.includes('time.sleep(0.25)') && api.includes('TERMINAL'));
check('artifacts persist', ['save_json_artifact','save_simulation_report','save_go_live_readiness','upsert_human_confirmation','record_cost'].every((s)=>persistence.includes(`def ${s}`)));
check('apply requires explicit confirmation', api.includes('explicit_confirmation_required') && api.includes('payload.get("confirm") is not True'));
check('frontend consumes streamed final payload', center.includes('streamedResult') && stream.includes('workflow.completed_partial'));
check('manual create copy hidden', !/Crear desde cero|Rutas canónicas|Create y reconfigure|flujo de creación modular/.test(read('frontend/app/bot-studio/page.tsx')));
check('no fake setup timers', !assistant.includes('setTimeout'));
check('human confirmation frontend route exists', existsSync('frontend/app/api/ai/workflows/[runId]/human-confirmations/route.ts'));
const failed = checks.filter(([, ok]) => !ok);
console.log(`${checks.length - failed.length}/${checks.length} checks passed`);
if (failed.length) process.exit(1);

process.exit(0);
