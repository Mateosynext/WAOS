import fs from "node:fs";
import path from "node:path";

const root = process.cwd();

const staleFiles = [
  "app/bot-studio/BotStudioFlowClient.tsx",
  "app/bot-studio/BotStudioFlow.tsx",
  "app/bot-studio/BotStudioWizardClient.tsx",
  "app/bot-studio/createScreens.tsx",
  "app/bot-studio/reconfigureScreens.tsx",
  "app/bot-studio/useBotStudioWizardState.ts",
  "app/bot-studio/wizardReviewSections.tsx",
  "features/bot-studio/services/wizardClient.ts",
  "features/bot-studio/ui/WizardErrorPanel.tsx",
];

const importMigrations = [
  {
    file: "features/bot-studio/server/loadBotStudioRoute.ts",
    replacements: [
      [
        'import { getBots, getStrongestVerticals, getVerticalCatalog } from "@/app/lib/waos";',
        'import { getBots } from "@/app/lib/data/bots";\nimport { getStrongestVerticals, getVerticalCatalog } from "@/app/lib/data/verticals";',
      ],
      [
        'import type { BotContract, SessionOrganization, VerticalProfileContract } from "@/app/lib/contracts";',
        'import type { SessionOrganization } from "@/app/lib/contracts/auth";\nimport type { BotContract } from "@/app/lib/contracts/bots";\nimport type { VerticalProfileContract } from "@/app/lib/contracts/verticals";',
      ],
    ],
  },
  {
    file: "features/bot-studio/services/wizardPayloadBuilders.ts",
    replacements: [
      [
        'import type { SessionOrganization } from "@/app/lib/contracts";',
        'import type { SessionOrganization } from "@/app/lib/contracts/auth";',
      ],
    ],
  },
  {
    file: "features/bot-studio/services/wizardReactiveData.ts",
    replacements: [
      [
        'import type { VerticalProfileContract } from "@/app/lib/contracts";',
        'import type { VerticalProfileContract } from "@/app/lib/contracts/verticals";',
      ],
    ],
  },
  {
    file: "features/bot-studio/ui/VerticalPicker.tsx",
    replacements: [
      [
        'import type { VerticalProfileContract } from "@/app/lib/contracts";',
        'import type { VerticalProfileContract } from "@/app/lib/contracts/verticals";',
      ],
    ],
  },
];

let removed = 0;
for (const relativePath of staleFiles) {
  const absolutePath = path.join(root, relativePath);
  if (fs.existsSync(absolutePath)) {
    fs.rmSync(absolutePath, { force: true });
    removed += 1;
  }
}

let migrated = 0;
const remainingLegacyImports = [];
for (const migration of importMigrations) {
  const absolutePath = path.join(root, migration.file);
  if (!fs.existsSync(absolutePath)) continue;
  let source = fs.readFileSync(absolutePath, "utf8");
  const before = source;
  for (const [from, to] of migration.replacements) {
    source = source.split(from).join(to);
  }
  if (source !== before) {
    fs.writeFileSync(absolutePath, source);
    migrated += 1;
  }
  if (source.includes('from "@/app/lib/contracts"') || source.includes('from "@/app/lib/waos"')) {
    remainingLegacyImports.push(migration.file);
  }
}

if (remainingLegacyImports.length) {
  console.error(`[cleanup:error] legacy Bot Studio imports remain: ${remainingLegacyImports.join(", ")}`);
  process.exit(1);
}

const details = [];
if (removed) details.push(`removed ${removed} stale file${removed === 1 ? "" : "s"}`);
if (migrated) details.push(`migrated ${migrated} legacy import file${migrated === 1 ? "" : "s"}`);
console.log(`[cleanup:ok] ${details.length ? details.join("; ") : "stale Bot Studio files are absent"}`);
