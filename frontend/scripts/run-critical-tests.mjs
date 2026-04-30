import { spawnSync } from 'node:child_process';
const steps = [['npm', ['run', 'smoke']], ['npm', ['run', 'test:node']], ['npm', ['run', 'test:e2e:real:critical']]];
for (const [command, args] of steps) {
  const result = spawnSync(command, args, { stdio: 'inherit', shell: process.platform === 'win32' });
  if (result.status !== 0) process.exit(result.status || 1);
}
console.log('Critical frontend suite passed: smoke + node + real browser e2e.');

if (!process.exitCode) process.exit(0);
