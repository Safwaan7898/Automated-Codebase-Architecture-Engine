import { test, expect } from '@playwright/test'
import { setupMocks } from './helpers'
import AxeBuilder from '@axe-core/playwright'
import path from 'path'
import fs from 'fs'

const acceptanceScreenshotsDir = path.resolve('e2e/screenshots/acceptance')
if (!fs.existsSync(acceptanceScreenshotsDir)) {
  fs.mkdirSync(acceptanceScreenshotsDir, { recursive: true })
}

const MOCK_GRAPH_DATA = {
  repo_id: '8759c211-b331-4c01-a97c-9d6ad909272b',
  language: 'python',
  graph: {
    nodes: [
      { id: 'UserService', name: 'UserService', node_type: 'class', loc: 140, cyclomatic_complexity: 8 },
      { id: 'UserController', name: 'UserController', node_type: 'class', loc: 85, cyclomatic_complexity: 4 },
      { id: 'OrderService', name: 'OrderService', node_type: 'class', loc: 210, cyclomatic_complexity: 12 },
      { id: 'DatabasePool', name: 'DatabasePool', node_type: 'module', loc: 50, cyclomatic_complexity: 2 },
    ],
    edges: [
      { source: 'UserController', target: 'UserService', edge_type: 'call', weight: 1.0, is_cycle: false },
      { source: 'UserService', target: 'DatabasePool', edge_type: 'import', weight: 1.0, is_cycle: false },
    ],
  },
  smells: [],
  health: { score: 92.0, grade: 'A', status: 'healthy' },
}

async function setupGraphMocks(page: any) {
  await setupMocks(page)

  await page.route('**/graphs', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ repo_ids: ['8759c211-b331-4c01-a97c-9d6ad909272b'] }),
    })
  })

  await page.route('**/api/graphs', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ repo_ids: ['8759c211-b331-4c01-a97c-9d6ad909272b'] }),
    })
  })

  await page.route('**/graph/**', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_GRAPH_DATA),
    })
  })

  await page.route('**/graphs/**', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_GRAPH_DATA),
    })
  })

  await page.route('**/api/graph/**', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_GRAPH_DATA),
    })
  })

  await page.route('**/api/graphs/**', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_GRAPH_DATA),
    })
  })

  await page.route('**/reports/**', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_GRAPH_DATA),
    })
  })

  await page.route('**/api/reports/**', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_GRAPH_DATA),
    })
  })
}

test.describe('Acceptance Suite: UI Bug Fixes Verification', () => {
  const themes = ['dark', 'light'] as const

  test('Font verification: ensure all requested fonts are served without 404s', async ({ page }) => {
    const failed404s: string[] = []

    page.on('response', (response) => {
      const url = response.url()
      if (
        (url.includes('fonts.googleapis.com') ||
          url.includes('fonts.gstatic.com') ||
          url.includes('.woff') ||
          url.includes('.ttf')) &&
        response.status() === 404
      ) {
        failed404s.push(url)
      }
    })

    await setupGraphMocks(page)
    await page.goto('/dashboard', { waitUntil: 'networkidle' })
    expect(failed404s).toEqual([])
  })

  for (const theme of themes) {
    test(`Dashboard (${theme}): percentage digits rendered, gauge consistent, axe contrast zero violations`, async ({
      page,
    }) => {
      await setupGraphMocks(page)

      await page.addInitScript((th) => {
        localStorage.setItem('theme', th)
        sessionStorage.setItem('last_analysis_id', '8759c211-b331-4c01-a97c-9d6ad909272b')
        document.documentElement.classList.remove('dark', 'light')
        document.documentElement.classList.add(th)
        document.documentElement.setAttribute('data-theme', th)
        document.documentElement.style.colorScheme = th
      }, theme)

      await page.goto('/dashboard?analysis=8759c211-b331-4c01-a97c-9d6ad909272b', {
        waitUntil: 'networkidle',
      })
      // Allow animated counter to complete (duration is ~1.2s)
      await page.waitForTimeout(1500)

      // 1. Verify percentage digits are visible and not rendered as transparent/grey box
      const percentageDigits = page.locator('span:has-text("92")').first()
      await expect(percentageDigits).toBeVisible({ timeout: 10000 })
      const textContent = await percentageDigits.textContent()
      expect(textContent?.trim()).toBe('92')

      // Verify computed styling does not hide text
      const computedStyles = await percentageDigits.evaluate((el) => {
        const style = window.getComputedStyle(el)
        return {
          color: style.color,
          visibility: style.visibility,
          display: style.display,
          webkitTextFillColor: (style as any).webkitTextFillColor,
        }
      })
      expect(computedStyles.visibility).toBe('visible')
      expect(computedStyles.display).not.toBe('none')

      // 2. Verify gauge labels: Poor, Fair, Good, Excellent
      await expect(page.getByText('Poor', { exact: true })).toBeVisible()
      await expect(page.getByText('Fair', { exact: true })).toBeVisible()
      await expect(page.getByText('Good', { exact: true })).toBeVisible()
      await expect(page.getByText('Excellent', { exact: true })).toBeVisible()

      // 3. Screenshot
      await page.screenshot({
        path: path.join(acceptanceScreenshotsDir, `dashboard-${theme}.png`),
        fullPage: true,
      })

      // 4. Axe-core color-contrast audit
      const axeResults = await new AxeBuilder({ page }).withRules(['color-contrast']).analyze()
      expect(axeResults.violations).toEqual([])
    })

    test(`Ingestion 5 tabs (${theme}): git, local, archive, folder, snippet with axe contrast audit`, async ({
      page,
    }) => {
      await setupMocks(page)

      await page.addInitScript((th) => {
        localStorage.setItem('theme', th)
        document.documentElement.classList.remove('dark', 'light')
        document.documentElement.classList.add(th)
        document.documentElement.setAttribute('data-theme', th)
        document.documentElement.style.colorScheme = th
      }, theme)

      await page.goto('/ingestion', { waitUntil: 'networkidle' })
      await page.waitForTimeout(400)

      const tabs = [
        { id: 'git', name: /GITHUB \/ GIT/i },
        { id: 'local', name: /LOCAL PATH/i },
        { id: 'archive', name: /ZIP ARCHIVE/i },
        { id: 'folder', name: /FOLDER DROP/i },
        { id: 'snippet', name: /SNIPPET/i },
      ]

      for (const tab of tabs) {
        const tabBtn = page.getByRole('button', { name: tab.name })
        const isDisabled = await tabBtn.isDisabled()
        if (!isDisabled) {
          await tabBtn.click()
          await page.waitForTimeout(300)
        }

        // Capture screenshot of each tab
        await page.screenshot({
          path: path.join(acceptanceScreenshotsDir, `ingestion-tab-${tab.id}-${theme}.png`),
          fullPage: true,
        })

        // Run axe audit on tab view
        const axeResults = await new AxeBuilder({ page }).withRules(['color-contrast']).analyze()
        expect(axeResults.violations).toEqual([])
      }
    })

    test(`Metrics (${theme}): screenshot & axe contrast audit`, async ({ page }) => {
      await setupMocks(page)

      await page.addInitScript((th) => {
        localStorage.setItem('theme', th)
        document.documentElement.classList.remove('dark', 'light')
        document.documentElement.classList.add(th)
        document.documentElement.setAttribute('data-theme', th)
        document.documentElement.style.colorScheme = th
      }, theme)

      await page.goto('/metrics', { waitUntil: 'networkidle' })
      await page.waitForTimeout(400)

      await page.screenshot({
        path: path.join(acceptanceScreenshotsDir, `metrics-${theme}.png`),
        fullPage: true,
      })

      const axeResults = await new AxeBuilder({ page }).withRules(['color-contrast']).analyze()
      expect(axeResults.violations).toEqual([])
    })

    test(`Reports (${theme}): screenshot & axe contrast audit`, async ({ page }) => {
      await setupMocks(page)

      await page.addInitScript((th) => {
        localStorage.setItem('theme', th)
        document.documentElement.classList.remove('dark', 'light')
        document.documentElement.classList.add(th)
        document.documentElement.setAttribute('data-theme', th)
        document.documentElement.style.colorScheme = th
      }, theme)

      await page.goto('/reports', { waitUntil: 'networkidle' })
      await page.waitForTimeout(400)

      await page.screenshot({
        path: path.join(acceptanceScreenshotsDir, `reports-${theme}.png`),
        fullPage: true,
      })

      const axeResults = await new AxeBuilder({ page }).withRules(['color-contrast']).analyze()
      expect(axeResults.violations).toEqual([])
    })

    test(`Settings (${theme}): screenshot & axe contrast audit`, async ({ page }) => {
      await setupMocks(page)

      await page.addInitScript((th) => {
        localStorage.setItem('theme', th)
        document.documentElement.classList.remove('dark', 'light')
        document.documentElement.classList.add(th)
        document.documentElement.setAttribute('data-theme', th)
        document.documentElement.style.colorScheme = th
      }, theme)

      await page.goto('/settings', { waitUntil: 'networkidle' })
      await page.waitForTimeout(400)

      await page.screenshot({
        path: path.join(acceptanceScreenshotsDir, `settings-${theme}.png`),
        fullPage: true,
      })

      const axeResults = await new AxeBuilder({ page }).withRules(['color-contrast']).analyze()
      expect(axeResults.violations).toEqual([])
    })
  }
})
