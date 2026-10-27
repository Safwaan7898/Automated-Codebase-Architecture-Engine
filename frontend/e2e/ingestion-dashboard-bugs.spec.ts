import { test, expect } from '@playwright/test'
import path from 'path'
import fs from 'fs'
import { fileURLToPath } from 'url'

import { setupMocks } from './helpers'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const screenshotsDir = path.resolve(__dirname, 'screenshots/bugs-fix')
if (!fs.existsSync(screenshotsDir)) {
  fs.mkdirSync(screenshotsDir, { recursive: true })
}

test.describe('Ingestion & Dashboard Bug Suite', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page)
    // Clear storage before each test
    await page.goto('/')
    await page.evaluate(() => {
      localStorage.clear()
      sessionStorage.clear()
    })
  })

  test('(1) fresh start shows the empty state with no analysis loaded', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Expect empty state container
    const emptyState = page.locator('[data-testid="empty-clean-start"]')
    await expect(emptyState).toBeVisible()
    await expect(emptyState).toContainText('No repository analysed yet')
    await expect(page.locator('button', { hasText: 'INGEST FROM GITHUB' })).toBeVisible()
    await expect(page.locator('button', { hasText: 'UPLOAD ARCHIVE' })).toBeVisible()

    // Gauge must show neutral empty state
    const gauge = page.locator('[data-testid="risk-gauge-card"]')
    await expect(gauge).toBeVisible()
    await expect(gauge).toContainText('Awaiting Ingestion')
    await expect(gauge).toContainText('Architecture Health')

    // Should NOT show "NOT ENOUGH DATA" twice
    const textContent = await page.locator('body').innerText()
    const occurrences = (textContent.match(/Not enough data/gi) || []).length
    expect(occurrences).toBe(0)

    // Capture screenshots for empty state (dark and light)
    await page.screenshot({ path: path.join(screenshotsDir, '1-empty-clean-start-dark.png') })
    await page.evaluate(() => document.documentElement.classList.add('light'))
    await page.evaluate(() => document.documentElement.classList.remove('dark'))
    await page.screenshot({ path: path.join(screenshotsDir, '1-empty-clean-start-light.png') })
  })

  test('(2) upload the fixture zip -> progress -> Dashboard shows nodes > 0 and a real score', async ({ page }) => {
    await page.goto('/ingestion')
    await page.waitForLoadState('networkidle')

    // Click on Archive tab
    await page.click('[data-testid="tab-archive"]')

    const fixtureZipPath = path.resolve(__dirname, '../../backend/tests/fixtures/mini_repo.zip')
    expect(fs.existsSync(fixtureZipPath)).toBeTruthy()

    // Upload archive
    const fileInput = page.locator('[data-testid="archive-file-input"]')
    await fileInput.setInputFiles(fixtureZipPath)

    // Check selected file info is displayed
    const selectedInfo = page.locator('[data-testid="selected-file-info"]')
    await expect(selectedInfo).toBeVisible()
    await expect(selectedInfo).toContainText('mini_repo.zip')

    // Click Run Real-time Ingestion
    const runBtn = page.locator('[data-testid="run-ingestion-button"]')
    await runBtn.click()

    // Wait for redirect to dashboard with ?analysis=<id>
    await page.waitForURL(/\/dashboard\?analysis=/, { timeout: 25000 })
    expect(page.url()).toContain('?analysis=')

    // Expect nodes > 0 and real score
    const nodesCount = page.locator('[data-testid="parsed-nodes-count"]')
    await expect(nodesCount).toBeVisible({ timeout: 15000 })
    const countText = await nodesCount.innerText()
    expect(parseInt(countText, 10)).toBeGreaterThan(0)

    // Gauge should show real score
    const gauge = page.locator('[data-testid="risk-gauge-card"]')
    await expect(gauge).toBeVisible()
    await expect(gauge).not.toContainText('Awaiting Ingestion')

    // Capture success screenshot (dark & light)
    await page.screenshot({ path: path.join(screenshotsDir, '2-success-dashboard-dark.png') })
    await page.evaluate(() => document.documentElement.classList.add('light'))
    await page.evaluate(() => document.documentElement.classList.remove('dark'))
    await page.screenshot({ path: path.join(screenshotsDir, '2-success-dashboard-light.png') })
  })

  test('(3) upload a .png -> blocked with the type error', async ({ page }) => {
    await page.goto('/ingestion')
    await page.waitForLoadState('networkidle')

    await page.click('[data-testid="tab-archive"]')

    const pngPath = path.resolve(__dirname, 'fixtures/sample.png')
    const fileInput = page.locator('[data-testid="archive-file-input"]')
    await fileInput.setInputFiles(pngPath)

    // Inline error should appear immediately without clicking Run
    const inlineError = page.locator('[data-testid="archive-inline-error"]')
    await expect(inlineError).toBeVisible()
    await expect(inlineError).toContainText('Only .zip, .tar.gz, .tgz or .tar archives are supported')

    // Selected file info should not display an accepted file
    await expect(page.locator('[data-testid="selected-file-info"]')).not.toBeVisible()

    // Capture invalid type screenshot
    await page.screenshot({ path: path.join(screenshotsDir, '3-type-error-blocked-dark.png') })
    await page.evaluate(() => document.documentElement.classList.add('light'))
    await page.evaluate(() => document.documentElement.classList.remove('dark'))
    await page.screenshot({ path: path.join(screenshotsDir, '3-type-error-blocked-light.png') })
  })

  test('(4) upload an empty zip -> "no supported source files" or empty archive error', async ({ page }) => {
    await page.goto('/ingestion')
    await page.waitForLoadState('networkidle')

    await page.click('[data-testid="tab-archive"]')

    const emptyZipPath = path.resolve(__dirname, '../../backend/tests/fixtures/empty.zip')
    const fileInput = page.locator('[data-testid="archive-file-input"]')
    await fileInput.setInputFiles(emptyZipPath)

    // Click Run
    await page.click('[data-testid="run-ingestion-button"]')

    // Wait for error to surface in status log or error banner
    await expect(page.locator('text=empty or contains no files').or(page.locator('text=ANALYSIS FAILURE')).first()).toBeVisible({ timeout: 15000 })

    // Capture failed/empty screenshot
    await page.screenshot({ path: path.join(screenshotsDir, '4-empty-failed-dark.png') })
    await page.evaluate(() => document.documentElement.classList.add('light'))
    await page.evaluate(() => document.documentElement.classList.remove('dark'))
    await page.screenshot({ path: path.join(screenshotsDir, '4-empty-failed-light.png') })
  })

  test('(5) reload the page -> state restored from ?analysis=<id>, not from a default repo', async ({ page }) => {
    // Navigate with a specific analysis ID from backend
    // First, get an analysis ID by calling backend or using the fixture job
    const res = await page.request.get('http://127.0.0.1:8000/graphs')
    const data = await res.json()
    const validId = data.repo_ids?.[0]
    expect(validId).toBeTruthy()

    await page.goto(`/dashboard?analysis=${validId}`)
    await page.waitForLoadState('networkidle')

    // Verify it loaded the specific repository
    const nodesCount = page.locator('[data-testid="parsed-nodes-count"]')
    await expect(nodesCount).toBeVisible()
    const count = parseInt(await nodesCount.innerText(), 10)
    expect(count).toBeGreaterThan(0)

    // Reload the page
    await page.reload()
    await page.waitForLoadState('networkidle')

    // Expect the URL to maintain ?analysis=<id>
    expect(page.url()).toContain(`?analysis=${validId}`)
    await expect(nodesCount).toBeVisible()
    expect(parseInt(await nodesCount.innerText(), 10)).toBe(count)

    // Test non-existent ID shows not found state
    await page.goto('/dashboard?analysis=00000000-0000-0000-0000-000000000000')
    await page.waitForLoadState('networkidle')
    const notFound = page.locator('[data-testid="not-found-state"]')
    await expect(notFound).toBeVisible()
    await expect(notFound).toContainText('Analysis Not Found')

    // Capture not found screenshot
    await page.screenshot({ path: path.join(screenshotsDir, '5-not-found-state-dark.png') })
    await page.evaluate(() => document.documentElement.classList.add('light'))
    await page.evaluate(() => document.documentElement.classList.remove('dark'))
    await page.screenshot({ path: path.join(screenshotsDir, '5-not-found-state-light.png') })
  })
})
