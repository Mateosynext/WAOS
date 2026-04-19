import { buildPlaywrightConfig } from './playwright.shared';
const frontendPort = Number(process.env.PLAYWRIGHT_FRONTEND_PORT || 3000);
const apiPort = Number(process.env.PLAYWRIGHT_API_PORT || 4100);
export default buildPlaywrightConfig({
  frontendPort,
  apiPort,
  testMatch: ['**/*.real.spec.ts'],
  webServer: [
    { command: 'python ../backend/scripts/run_browser_e2e_server.py', port: apiPort, reuseExistingServer: false, env: { ...process.env, PLAYWRIGHT_API_PORT: String(apiPort), PLAYWRIGHT_FRONTEND_PORT: String(frontendPort), WAOS_E2E_FAKE_PROVIDERS: 'true', APP_ENV: 'test', ALLOW_SQLITE_FOR_TESTS: 'true', STRICT_SECURITY_STARTUP: 'false', APP_SECRET: process.env.APP_SECRET || 'waos-browser-e2e-secret-1234567890-abcdef', SECRET_ENCRYPTION_KEY: process.env.SECRET_ENCRYPTION_KEY || 'waos-browser-e2e-encryption-key-1234567890-ab', PUBLIC_APP_URL: `http://localhost:${frontendPort}`, API_BASE_URL: `http://localhost:${apiPort}`, API_INTERNAL_URL: `http://localhost:${apiPort}` } },
    { command: 'npm run dev', port: frontendPort, reuseExistingServer: !process.env.CI, env: { ...process.env, NEXT_TELEMETRY_DISABLED: '1', API_INTERNAL_URL: `http://localhost:${apiPort}`, API_BASE_URL: `http://localhost:${apiPort}`, NEXT_PUBLIC_API_BASE_URL: `http://localhost:${apiPort}`, PUBLIC_APP_URL: `http://localhost:${frontendPort}` } },
  ],
});
