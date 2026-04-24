import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const stalePaths = [
  'app/bot-studio/BotStudioFlowClient.tsx',
  'app/bot-studio/BotStudioWizardClient.tsx',
  'app/bot-studio/BotStudioFlow.tsx',
  'app/bot-studio/createScreens.tsx',
  'app/bot-studio/reconfigureScreens.tsx',
  'app/bot-studio/useBotStudioWizardState.ts',
  'app/bot-studio/wizardReviewSections.tsx',
  'features/bot-studio/services/wizardClient.ts',
  'features/bot-studio/ui/WizardErrorPanel.tsx',
];

function removeIfPresent(relativePath) {
  const absolutePath = path.join(root, relativePath);
  if (!fs.existsSync(absolutePath)) return;
  fs.rmSync(absolutePath, { force: true, recursive: true });
  console.log(`[cleanup] removed stale Bot Studio file: ${relativePath}`);
}

for (const relativePath of stalePaths) removeIfPresent(relativePath);

const appBotStudioRoot = path.join(root, 'app/bot-studio');
const allowedRootFiles = new Set(['page.tsx', 'loading.tsx']);
if (fs.existsSync(appBotStudioRoot)) {
  for (const entry of fs.readdirSync(appBotStudioRoot, { withFileTypes: true })) {
    if (!entry.isFile()) continue;
    if (!/\.(ts|tsx)$/.test(entry.name)) continue;
    if (allowedRootFiles.has(entry.name)) continue;
    removeIfPresent(path.posix.join('app/bot-studio', entry.name));
  }
}

console.log('[cleanup:ok] stale Bot Studio files are absent');
