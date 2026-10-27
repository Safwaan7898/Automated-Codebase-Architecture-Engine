import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { setupMocks } from './helpers'

test.describe('P2 Items: Insights Visualizations & Multi-Project Workspace', () => {
  test('Insights Page: Hotspot Bubble, Chord Arc, and Language Donut render and function', async ({ page }) => {
    await setupMocks(page)

    await page.goto('/insights', { waitUntil: 'networkidle' })
    await page.waitForTimeout(600)

    // Load sample dataset if in empty state
    const flaskBtn = page.getByRole('button', { name: 'Flask API' })
    if (await flaskBtn.isVisible()) {
      await flaskBtn.click()
      await page.waitForTimeout(500)
    }

    // 1. Hotspot Bubble Chart
    const hotspotHeading = page.getByText('Architectural Hotspot Bubble Chart')
    await expect(hotspotHeading).toBeVisible()

    const hotspotSvg = page.locator('#hotspot-bubble-svg')
    await expect(hotspotSvg).toBeVisible()

    const hotspotCaption = page.getByText(/How to read this chart:/i).first()
    await expect(hotspotCaption).toBeVisible()

    // Trigger AI explanation for Hotspots
    const explainHotspotsBtn = page.locator('button:has-text("AI Explain")').first()
    await expect(explainHotspotsBtn).toBeVisible()
    await explainHotspotsBtn.click()
    await page.waitForTimeout(400)

    // AI Badge must appear
    const aiBadge = page.locator('span[aria-label="AI-generated content"]').first()
    await expect(aiBadge).toBeVisible()

    // 2. Chord / Arc Diagram
    const chordHeading = page.getByText(/Layer Dependency Chord/i)
    await expect(chordHeading).toBeVisible()

    const chordSvg = page.locator('#chord-arc-svg')
    await expect(chordSvg).toBeVisible()

    // 3. Language Breakdown Donut
    const languageHeading = page.getByText(/Language Breakdown & Polyglot Share/i)
    await expect(languageHeading).toBeVisible()

    const languageSvg = page.locator('#language-donut-svg')
    await expect(languageSvg).toBeVisible()

    // Trigger AI explanation for Language Breakdown
    const explainLangBtn = page.getByRole('button', { name: /Explain Breakdown/i })
    await expect(explainLangBtn).toBeVisible()
    await explainLangBtn.click()
    await page.waitForTimeout(400)
    await expect(page.locator('span[aria-label="AI-generated content"]').first()).toBeVisible()
  })

  test('Projects Page: Portfolio Risk ranking and AI Compare modal', async ({ page }) => {
    await setupMocks(page)

    await page.goto('/projects', { waitUntil: 'networkidle' })
    await page.waitForTimeout(600)

    // Check project card loaded
    const projectTitle = page.getByText('archlens (main)')
    await expect(projectTitle).toBeVisible()

    // Check Portfolio Risk metric card
    const cardRiskText = page.locator('.glass-card').locator('div:has-text("Portfolio Risk")').first()
    await expect(cardRiskText).toBeVisible()

    // Sort by risk
    const sortSelect = page.locator('select').first()
    await sortSelect.selectOption('risk')
    await page.waitForTimeout(300)

    // Open Compare modal
    const compareBtn = page.getByRole('button', { name: /Compare/i }).first()
    await compareBtn.click()
    await page.waitForTimeout(400)

    // Run Comparison
    const runCompareBtn = page.getByRole('button', { name: /Run Comparison/i })
    await expect(runCompareBtn).toBeVisible()
    await runCompareBtn.click()
    await page.waitForTimeout(500)

    // Check Delta Summary and AI-generated badge
    const deltaSummary = page.getByText(/Architectural Delta Summary/i)
    await expect(deltaSummary).toBeVisible()

    const aiBadge = page.locator('span[aria-label="AI-generated content"]').first()
    await expect(aiBadge).toBeVisible()
  })

  test('P2 Visualizations: Axe Contrast Audit in Light and Dark themes', async ({ page }) => {
    await setupMocks(page)

    for (const theme of ['dark', 'light'] as const) {
      await page.addInitScript((selectedTheme) => {
        localStorage.setItem('theme', selectedTheme)
        if (selectedTheme === 'dark') {
          document.documentElement.classList.remove('light')
          document.documentElement.classList.add('dark')
          document.documentElement.setAttribute('data-theme', 'dark')
          document.documentElement.style.colorScheme = 'dark'
        } else {
          document.documentElement.classList.remove('dark')
          document.documentElement.classList.add('light')
          document.documentElement.setAttribute('data-theme', 'light')
          document.documentElement.style.colorScheme = 'light'
        }
      }, theme)

      await page.goto('/insights', { waitUntil: 'networkidle' })
      await page.waitForTimeout(500)

      const results = await new AxeBuilder({ page })
        .withRules(['color-contrast'])
        .analyze()

      expect(results.violations).toEqual([])
    }
  })
})
