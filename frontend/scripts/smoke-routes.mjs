import fs from "node:fs";

const required = [
  "app/login/page.tsx",
  "app/releases/page.tsx",
  "app/insights/page.tsx",
  "app/components/LoginForm.tsx",
  "app/api/auth/sso/start/route.ts",
  "app/api/auth/sso/callback/route.ts",
  "app/api/reports/executive/[reportId]/pdf/route.ts",
];

const missing = required.filter((item) => !fs.existsSync(new URL(`../${item}`, import.meta.url)));
if (missing.length) {
  console.error("Missing critical routes/files:\n" + missing.join("\n"));
  process.exit(1);
}
console.log(`Smoke OK: ${required.length} critical files present.`);
