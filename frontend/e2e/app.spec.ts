import { test, expect } from '@playwright/test'
import { ROUTES, setupMocks, createE2EAnalysisAndReport } from './helpers'
import path from 'path'
import fs from 'fs'

const regressionDir = path.resolve('e2e/screenshots/regression')
if (!fs.existsSync(regressionDir)) {
  fs.mkdirSync(regressionDir, { recursive: true })
}

test.describe('ArchLens Full System Regression Suite', () => {
  test.describe.configure({ mode: 'serial' })
  test.setTimeout(90000)
  let dynamicAnalysisId = ''

  test.beforeAll(async ({ request }) => {
    dynamicAnalysisId = await createE2EAnalysisAndReport(request)
  })

  test.beforeEach(async ({ page }) => {
    await setupMocks(page)
  })

  test('Step 1: User Login & Session Establishment', async ({ page }) => {
    // Unauthenticated initial state
    await page.route('**/auth/me', async (route) => {
      // First check unauthenticated
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Unauthenticated' }),
      })
    })

    await page.goto('/login', { waitUntil: 'networkidle' })

    const authCard = page.locator('[data-testid="auth-card"]')
    await expect(authCard).toBeVisible()

    // Fill credentials
    const emailInput = page.locator('input[type="email"]')
    const passwordInput = page.locator('input[type="password"]')

    await emailInput.fill('admin@archlens.io')
    await passwordInput.fill('ArchLensAdmin2026!')

    // Setup authenticated route fulfillment for login request
    await page.route('**/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'mock-jwt-access-token',
          token_type: 'bearer',
          user: {
            id: 'usr-admin-1',
            full_name: 'Eleanor Vance',
            work_email: 'admin@archlens.io',
            role: 'ADMIN',
          },
        }),
      })
    })

    // Now re-route auth/me to authenticated
    await page.route('**/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          user: {
            id: 'usr-admin-1',
            full_name: 'Eleanor Vance',
            work_email: 'admin@archlens.io',
            role: 'ADMIN',
          },
          permissions: ['view:dashboard', 'run:ingestion', 'view:graph', 'view:reports', 'generate:reports'],
        }),
      })
    })

    const submitBtn = page.locator('button[type="submit"]')
    await submitBtn.click()

    // Verify successful authentication and redirection to dashboard
    await expect(page).toHaveURL(/.*dashboard/, { timeout: 8000 })
    await expect(page.locator('h1, h2').first()).toBeVisible()

    await page.screenshot({
      path: path.join(regressionDir, 'step1-login-success.png'),
      fullPage: true,
    })
  })

  test('Step 2: Architectural Ingestion Flow', async ({ page }) => {
    await page.goto('/ingestion', { waitUntil: 'networkidle' })

    const ingestionHeader = page.locator('h1')
    await expect(ingestionHeader).toContainText(/CODEBASE PIPELINE|INGESTION/i)

    // Switch to code snippet tab
    const snippetTabBtn = page.getByRole('button', { name: /SNIPPET|Paste Code/i })
    await snippetTabBtn.click()

    const textarea = page.locator('textarea')
    await expect(textarea).toBeVisible()

    // Trigger real-time ingestion
    const ingestBtn = page.getByRole('button', { name: /RUN REAL-TIME INGESTION/i })
    await expect(ingestBtn).toBeVisible()

    // Mock start ingestion & job status for rapid deterministic completion
    await page.route('**/ingest', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: 'job-test-ingest-1',
          status: 'running',
          source_type: 'snippet',
          source_location: 'memory',
        }),
      })
    })

    await page.route('**/jobs/job-test-ingest-1', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: 'job-test-ingest-1',
          status: 'completed',
          result: {
            repo_id: '8759c211-b331-4c01-a97c-9d6ad909272b',
            language: 'python',
            graph: {
              nodes: [
                { id: 'UserService', name: 'UserService', node_type: 'class', loc: 140, cyclomatic_complexity: 8 },
                { id: 'UserController', name: 'UserController', node_type: 'class', loc: 85, cyclomatic_complexity: 4 },
              ],
              edges: [
                { source: 'UserController', target: 'UserService', edge_type: 'call', weight: 1.0, is_cycle: false },
              ],
            },
            smells: [],
            health: { score: 92.0, grade: 'A', status: 'healthy' },
          },
        }),
      })
    })

    await ingestBtn.click()

    // Verify progress log appears
    await expect(page.locator('text=ARCHLENS_AST_ENGINE_OUTPUT_STREAM')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('text=Real-time analysis succeeded!')).toBeVisible({ timeout: 8000 })

    await page.screenshot({
      path: path.join(regressionDir, 'step2-ingest-success.png'),
      fullPage: true,
    })
  })

  test('Step 3: Verification of Every Page in Light and Dark Mode', async ({ page }) => {
    test.setTimeout(120000)

    for (const r of ROUTES) {
      // 1. Dark Mode
      await page.addInitScript(() => {
        localStorage.setItem('theme', 'dark')
        document.documentElement.classList.remove('light')
        document.documentElement.classList.add('dark')
        document.documentElement.setAttribute('data-theme', 'dark')
        document.documentElement.style.colorScheme = 'dark'
      })

      await page.goto(r.path, { waitUntil: 'domcontentloaded' })
      await page.waitForTimeout(300)

      await page.screenshot({
        path: path.join(regressionDir, `page-${r.name}-dark.png`),
        fullPage: true,
      })

      // 2. Light Mode
      await page.addInitScript(() => {
        localStorage.setItem('theme', 'light')
        document.documentElement.classList.remove('dark')
        document.documentElement.classList.add('light')
        document.documentElement.setAttribute('data-theme', 'light')
        document.documentElement.style.colorScheme = 'light'
      })

      await page.goto(r.path, { waitUntil: 'domcontentloaded' })
      await page.waitForTimeout(300)

      await page.screenshot({
        path: path.join(regressionDir, `page-${r.name}-light.png`),
        fullPage: true,
      })
    }
  })

  test('Step 4: Download Architecture Diagnostic PDF Report', async ({ page }) => {
    let targetAnalysisId = dynamicAnalysisId
    if (!targetAnalysisId) {
      const gRes = await page.request.get('http://127.0.0.1:8000/graphs')
      if (gRes.ok()) {
        const gData = await gRes.json()
        targetAnalysisId = gData.repo_ids?.[0] || ''
      }
    }
    const reportUrl = targetAnalysisId ? `/reports?analysis=${targetAnalysisId}` : '/reports'
    await page.goto(reportUrl, { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(500)

    const downloadBtn = page.locator('[data-testid="download-pdf-button"]')
    await expect(downloadBtn).toBeVisible()

    // Setup download listener and click
    const downloadPromise = page.waitForEvent('download', { timeout: 45000 })
    await downloadBtn.click()
    const download = await downloadPromise

    const suggestedFilename = download.suggestedFilename()
    expect(suggestedFilename).toMatch(/\.pdf$/i)

    const savePath = path.join(regressionDir, 'downloaded-report.pdf')
    await download.saveAs(savePath)

    expect(fs.existsSync(savePath)).toBe(true)
    const stats = fs.statSync(savePath)
    expect(stats.size).toBeGreaterThan(10000)

    // Check PDF magic bytes (%PDF)
    const buf = fs.readFileSync(savePath)
    expect(buf.toString('ascii', 0, 4)).toBe('%PDF')

    await page.screenshot({
      path: path.join(regressionDir, 'step4-download-pdf-success.png'),
      fullPage: true,
    })
  })
})
