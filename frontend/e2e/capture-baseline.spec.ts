import { test } from '@playwright/test'
import { ROUTES, setupMocks } from './helpers'
import path from 'path'
import fs from 'fs'

test.describe('Capture Dark Baseline Screenshots', () => {
  test('capture all routes in dark mode before changes', async ({ page }) => {
    test.setTimeout(120000)
    await setupMocks(page)

    const outDir = path.resolve('e2e/screenshots/dark-before')
    if (!fs.existsSync(outDir)) {
      fs.mkdirSync(outDir, { recursive: true })
    }

    // Set dark mode in localStorage
    await page.addInitScript(() => {
      localStorage.setItem('theme', 'dark')
      document.documentElement.classList.add('dark')
      document.documentElement.style.colorScheme = 'dark'
    })

    for (const r of ROUTES) {
      await page.goto(r.path, { waitUntil: 'domcontentloaded' })
      await page.waitForTimeout(300) // let animations settle
      await page.screenshot({
        path: path.join(outDir, `${r.name}.png`),
        fullPage: true,
      })
    }
  })
})
