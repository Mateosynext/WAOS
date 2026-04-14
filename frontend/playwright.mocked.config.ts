import { buildPlaywrightConfig } from './playwright.shared';
const frontendPort = Number(process.env.PLAYWRIGHT_FRONTEND_PORT || 3000);
const apiPort = Number(process.env.PLAYWRIGHT_API_PORT || 4100);
export default buildPlaywrightConfig({
  frontendPort,
  apiPort,
  testMatch: ['**/*.mock.spec.ts'],
  webServer: [
    { command: 'node ./tests/e2e/mock-api-server.mjs', port: apiPort, reuseExistingServer: !process.env.CI, env: { ...process.env, PLAYWRIGHT_API_PORT: String(apiPort) } },
    { command: 'npm run dev', port: frontendPort, reuseExistingServer: !process.env.CI, env: { ...process.env, NEXT_TELEMETRY_DISABLED: '1', API_INTERNAL_URL: `http://127.0.0.1:${apiPort}`, API_BASE_URL: `http://127.0.0.1:${apiPort}`, NEXT_PUBLIC_API_BASE_URL: `http://127.0.0.1:${apiPort}`, PUBLIC_APP_URL: `http://127.0.0.1:${frontendPort}` } },
  ],
});
