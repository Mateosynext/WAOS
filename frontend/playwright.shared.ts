import { defineConfig, devices } from '@playwright/test';

export function buildPlaywrightConfig(opts: {
  frontendPort: number;
  apiPort: number;
  webServer: NonNullable<ReturnType<typeof defineConfig>['webServer']>;
  testMatch?: string | string[];
  testIgnore?: string | string[];
}) {
  return defineConfig({
    testDir: './tests/e2e',
    testMatch: opts.testMatch,
    testIgnore: opts.testIgnore,
    timeout: 60_000,
    fullyParallel: false,
    retries: process.env.CI ? 1 : 0,
    reporter: [['list'], ['html', { open: 'never' }]],
    outputDir: 'test-results',
    use: {
      baseURL: `http://localhost:${opts.frontendPort}`,
      trace: 'retain-on-failure',
      screenshot: 'only-on-failure',
      video: (process.env.PLAYWRIGHT_VIDEO_MODE as 'off' | 'on' | 'retain-on-failure' | 'on-first-retry') || 'off',
      headless: true,
      launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH || '/usr/bin/chromium' },
    },
    webServer: opts.webServer,
    projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  });
}
