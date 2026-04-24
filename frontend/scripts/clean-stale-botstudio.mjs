import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const stalePaths = [
  'app/bot-studio/BotStudioFlowClient.tsx',
  'app/bot-studio/BotStudioFlow.tsx',
  'app/bot-studio/createScreens.tsx',
  'app/bot-studio/reconfigureScreens.tsx',
  'app/bot-studio/useBotStudioWizardState.ts',
  'app/bot-studio/wizardReviewSections.tsx',
];

for (const relativePath of stalePaths) {
  const absolutePath = path.join(root, relativePath);
  if (!fs.existsSync(absolutePath)) continue;
  fs.rmSync(absolutePath, { force: true, recursive: true });
  console.log(`[cleanup] removed stale Bot Studio file: ${relativePath}`);
}

console.log('[cleanup:ok] stale Bot Studio files are absent');
