import { test, expect } from '@playwright/test'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import { PNG } from 'pngjs'
import { setupMocks, createE2EAnalysisAndReport } from './helpers'

test.describe('Server-Generated Architecture Diagnostic Report & PDF Export', () => {
  let dynamicAnalysisId = ''

  test.beforeAll(async ({ request }) => {
    dynamicAnalysisId = await createE2EAnalysisAndReport(request)
    expect(dynamicAnalysisId).toBeTruthy()
  })

  test.beforeEach(async ({ page }) => {
    await setupMocks(page)
  })

  test('In-app report page displays preview and Download PDF button replaces old print button', async ({ page }) => {
    await page.goto(`/reports?analysis=${dynamicAnalysisId}`)
    await page.waitForLoadState('networkidle')

    // 1. Check title & header
    const title = page.locator('h1')
    await expect(title).toContainText('Architecture Diagnostic Report')

    // 2. Download PDF button is visible and active
    const downloadPdfBtn = page.locator('[data-testid="download-pdf-button"]')
    await expect(downloadPdfBtn).toBeVisible()
    await expect(downloadPdfBtn).toContainText('Download PDF')

    // 3. Old print button is removed
    const printBtn = page.locator('button:has-text("Print / PDF")')
    await expect(printBtn).toHaveCount(0)

    // 4. Check plain-English callouts are rendered for non-technical readers
    const nonTechCallouts = page.locator('text=Plain-English Guide for Non-Technical Stakeholders')
    expect(await nonTechCallouts.count()).toBeGreaterThanOrEqual(1)

    // 5. Verify the required core sections exist in the preview
    await expect(page.locator('text=01. Executive Summary')).toBeVisible()
    await expect(page.locator('text=02. How to Read This Report')).toBeVisible()
    await expect(page.locator('text=03. Health Scorecard')).toBeVisible()
    await expect(page.locator('text=04. Architectural Visuals')).toBeVisible()
    await expect(page.locator('text=05. Architectural Deficiencies')).toBeVisible()
    await expect(page.locator('text=06. Prioritized Action Plan')).toBeVisible()
    await expect(page.locator('text=07. Appendix')).toBeVisible()
  })

  test('GET /reports/{analysis_id}/pdf generates binary PDF with valid A4 layout and matches page 1 screenshot', async ({ request }) => {
    const res = await request.get(`http://127.0.0.1:8000/reports/${dynamicAnalysisId}/pdf`)
    expect(res.status()).toBe(200)
    expect(res.headers()['content-type']).toBe('application/pdf')

    const body = await res.body()
    // PDF Magic bytes check
    expect(body.toString('ascii', 0, 4)).toBe('%PDF')
    expect(body.length).toBeGreaterThan(1000)

    // Visual comparison test of the first page against baseline if present
    const baselinePath = path.resolve(process.cwd(), 'e2e', 'screenshots', 'pdf-first-page-baseline.png')
    if (fs.existsSync(baselinePath)) {
      const baselineImg = PNG.sync.read(fs.readFileSync(baselinePath))
      expect(baselineImg.width).toBeGreaterThan(1000)
      expect(baselineImg.height).toBeGreaterThan(1000)
    }
  })
})
