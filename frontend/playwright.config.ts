import path from 'node:path'
import os from 'node:os'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'
import { defineConfig, devices } from '@playwright/test'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const rootDir = path.resolve(__dirname, '..')
const isWin = process.platform === 'win32'
const venvPython = isWin
  ? path.join(rootDir, 'venv', 'Scripts', 'python.exe')
  : path.join(rootDir, 'venv', 'bin', 'python')

const testDataDir = path.join(os.tmpdir(), 'archlens-test-data')
if (!fs.existsSync(testDataDir)) {
  fs.mkdirSync(testDataDir, { recursive: true })
}

export default defineConfig({
  testDir: './e2e',
  timeout: 60 * 1000,
  expect: {
    timeout: 10000,
  },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : 2,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    headless: true,
    viewport: { width: 1280, height: 720 },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5173',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000,
    },
    {
      command: `"${venvPython}" -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
      cwd: path.join(rootDir, 'backend'),
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: true,
      timeout: 120 * 1000,
      env: {
        ARCHLENS_ENV: 'test',
        ARCHLENS_DATA_DIR: testDataDir,
        ARCHLENS_AI_ENABLED: 'true',
        ARCHLENS_AI_PROVIDER_ORDER: 'fake',
        ARCHLENS_AI_PROVIDER: 'fake',
        ARCHLENS_HOST: '127.0.0.1',
        ARCHLENS_PORT: '8000',
      },
    },
  ],
})
