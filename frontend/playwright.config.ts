import { defineConfig, devices } from '@playwright/test'

const liveBaseURL = process.env.PLAYWRIGHT_BASE_URL

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: liveBaseURL ?? 'http://127.0.0.1:8000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: liveBaseURL
    ? undefined
    : {
        command:
          'cmd /d /s /c "set RESEARCH_DEMO_AUTHORIZATION_CODE=research-code&& ..\\.venv\\Scripts\\uvicorn.exe collab.app:app --host 127.0.0.1 --port 8000"',
        url: 'http://127.0.0.1:8000/api/health',
        reuseExistingServer: false,
        timeout: 30_000,
      },
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
