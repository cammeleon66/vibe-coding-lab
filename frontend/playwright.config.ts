import { defineConfig, devices } from '@playwright/test'

const liveBaseURL = process.env.PLAYWRIGHT_BASE_URL

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: liveBaseURL ?? 'http://127.0.0.1:8100',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: liveBaseURL
    ? undefined
    : (
        [
          ['nl', 8101],
          ['de', 8102],
          ['hub', 8100],
        ] as const
      ).map(([site, port]) => ({
        command: `cmd /d /s /c "set SITE=${site}&& set PYTHONPATH=..\\src&& set FED_DATA_DIR=..\\.fed-e2e&& set FRONTEND_DIST=dist&& ..\\.venv\\Scripts\\python.exe -m uvicorn fednet.main:app --host 127.0.0.1 --port ${port}"`,
        url: `http://127.0.0.1:${port}/api/health`,
        reuseExistingServer: false,
        timeout: 30_000,
      })),
  projects: [
    {
      name: 'desktop-chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 960 } },
    },
    {
      name: 'mobile-chromium',
      use: { ...devices['Pixel 7'] },
    },
  ],
})
