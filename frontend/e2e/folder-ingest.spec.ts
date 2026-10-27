import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'
import { setupMocks } from './helpers'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

test.describe('Folder Ingestion & Pipeline Panel Controls', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page)
  })

  test('Folder selection, metadata stats, pipeline execution, and tab reset', async ({ page }) => {
    await page.goto('/ingestion')
    await page.waitForLoadState('networkidle')

    // 1. Pipeline panel must NOT be visible before a run starts
    await expect(page.locator('text=PIPELINE EXECUTION STATUS')).not.toBeVisible()
    await expect(page.locator('text=ARCHLENS_AST_ENGINE_OUTPUT_STREAM')).not.toBeVisible()

    // 2. Switch to Folder Drop tab
    await page.click('[data-testid="tab-folder"]')

    // Run button must be disabled with an inline hint until input is valid
    const runBtn = page.locator('[data-testid="run-ingestion-button"]')
    await expect(runBtn).toBeDisabled()
    const hint = page.locator('[data-testid="run-validation-hint"]')
    await expect(hint).toBeVisible()
    await expect(hint).toContainText(/select or drop a project folder/i)

    // 3. Select folder using directory fixture (mini_repo has 4 python files)
    const fixtureDir = path.resolve(__dirname, '../../backend/tests/fixtures/mini_repo')

    await page.locator('[data-testid="folder-input"]').setInputFiles(fixtureDir)

    // 4. Verify folder metadata card appears showing:
    // folder name, file count, ignored count, and total size
    const folderInfo = page.locator('[data-testid="folder-info"]')
    await expect(folderInfo).toBeVisible()

    await expect(page.locator('[data-testid="folder-name"]')).toHaveText('mini_repo')
    await expect(page.locator('[data-testid="folder-file-count"]')).toHaveText('4')
    await expect(page.locator('[data-testid="folder-ignored-count"]')).toHaveText('0')
    await expect(page.locator('[data-testid="folder-total-size"]')).toBeVisible()

    // 5. Run button should now be enabled and inline hint disappears
    await expect(runBtn).toBeEnabled()
    await expect(hint).not.toBeVisible()

    // 6. Test tab switching resets pipeline panel and state
    await page.click('[data-testid="tab-snippet"]')
    await expect(page.locator('text=PIPELINE EXECUTION STATUS')).not.toBeVisible()

    // Return to folder tab and select folder again
    await page.click('[data-testid="tab-folder"]')
    await page.locator('[data-testid="folder-input"]').setInputFiles(fixtureDir)
    await expect(runBtn).toBeEnabled()

    // 7. Click Run Ingestion - verifies client-side zip creation & pipeline
    await runBtn.click()

    // Pipeline panel should now become visible
    await expect(page.locator('text=PIPELINE EXECUTION STATUS')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('text=ARCHLENS_AST_ENGINE_OUTPUT_STREAM')).toBeVisible()

    // Wait for analysis to succeed and redirect to dashboard
    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 30000 })
  })
})
