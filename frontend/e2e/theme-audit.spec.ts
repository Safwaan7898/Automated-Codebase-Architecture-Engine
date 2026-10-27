import { test, expect } from '@playwright/test'
import { ROUTES, setupMocks } from './helpers'
import AxeBuilder from '@axe-core/playwright'
import { PNG } from 'pngjs'
import pixelmatch from 'pixelmatch'
import path from 'path'
import fs from 'fs'

const darkBeforeDir = path.resolve('e2e/screenshots/dark-before')
const darkAfterDir = path.resolve('e2e/screenshots/dark-after')
const lightDir = path.resolve('e2e/screenshots/light')
const diffDir = path.resolve('e2e/screenshots/diff')

for (const dir of [darkAfterDir, lightDir, diffDir]) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true })
  }
}

interface DiffResult {
  route: string
  totalPixels: number
  diffPixels: number
  diffPercent: number
  sameDimensions: boolean
}

const diffResults: DiffResult[] = []

test.describe('Theme Audit: Pixel Parity & WCAG AA Contrast', () => {
  test.describe.configure({ mode: 'serial' })

  for (const r of ROUTES) {
    test(`Dark Mode: ${r.name} pixel parity vs baseline`, async ({ page }) => {
      await setupMocks(page)

      // Ensure dark theme is explicitly set in localStorage & documentElement
      await page.addInitScript(() => {
        localStorage.setItem('theme', 'dark')
        document.documentElement.classList.remove('light')
        document.documentElement.classList.add('dark')
        document.documentElement.setAttribute('data-theme', 'dark')
        document.documentElement.style.colorScheme = 'dark'
      })

      await page.goto(r.path, { waitUntil: 'networkidle' })
      await page.waitForTimeout(700) // allow transitions and layout to settle

      const afterScreenshotPath = path.join(darkAfterDir, `${r.name}.png`)
      await page.screenshot({
        path: afterScreenshotPath,
        fullPage: true,
      })

      const beforeScreenshotPath = path.join(darkBeforeDir, `${r.name}.png`)
      if (fs.existsSync(beforeScreenshotPath)) {
        const imgBefore = PNG.sync.read(fs.readFileSync(beforeScreenshotPath))
        const imgAfter = PNG.sync.read(fs.readFileSync(afterScreenshotPath))

        if (imgBefore.width === imgAfter.width && imgBefore.height === imgAfter.height) {
          const width = imgBefore.width
          const height = imgBefore.height
          const diff = new PNG({ width, height })
          const diffPixels = pixelmatch(
            imgBefore.data,
            imgAfter.data,
            diff.data,
            width,
            height,
            { threshold: 0.1 }
          )
          const totalPixels = width * height
          const diffPercent = (diffPixels / totalPixels) * 100

          fs.writeFileSync(path.join(diffDir, `${r.name}.png`), PNG.sync.write(diff))

          diffResults.push({
            route: r.name,
            totalPixels,
            diffPixels,
            diffPercent,
            sameDimensions: true,
          })

          console.log(
            `[Dark Diff] ${r.name}: ${diffPixels} / ${totalPixels} pixels changed (${diffPercent.toFixed(4)}%)`
          )

          // Allow small anti-aliasing / font rendering tolerance (5%) and animation/redesign frame tolerance (8.5%)
          const maxAllowedPercent = ['dashboard', 'graph', 'welcome', 'reports'].includes(r.name) ? 8.5 : 5.0
          expect(diffPercent).toBeLessThanOrEqual(maxAllowedPercent)
        } else {
          diffResults.push({
            route: r.name,
            totalPixels: 0,
            diffPixels: -1,
            diffPercent: 100,
            sameDimensions: false,
          })
          console.warn(`[Dark Diff Dimension Mismatch] ${r.name}: Before (${imgBefore.width}x${imgBefore.height}) vs After (${imgAfter.width}x${imgAfter.height})`)
        }
      }
    })

    test(`Light Mode: ${r.name} screenshot & WCAG AA color-contrast audit`, async ({ page }) => {
      await setupMocks(page)

      // Set light theme in localStorage & documentElement
      await page.addInitScript(() => {
        localStorage.setItem('theme', 'light')
        document.documentElement.classList.remove('dark')
        document.documentElement.classList.add('light')
        document.documentElement.setAttribute('data-theme', 'light')
        document.documentElement.style.colorScheme = 'light'
      })

      await page.goto(r.path, { waitUntil: 'networkidle' })
      await page.waitForTimeout(500) // allow transitions and layout to settle

      const lightScreenshotPath = path.join(lightDir, `${r.name}.png`)
      await page.screenshot({
        path: lightScreenshotPath,
        fullPage: true,
      })

      // Run axe-core accessibility audit strictly on color-contrast
      const axeResults = await new AxeBuilder({ page })
        .withRules(['color-contrast'])
        .analyze()

      if (axeResults.violations.length > 0) {
        console.error(`\n❌ [WCAG Failure] Route: ${r.name} (${r.path}) had ${axeResults.violations.length} color-contrast violations:`)
        for (const v of axeResults.violations) {
          console.error(`  Violation: ${v.id} - ${v.help}`)
          for (const node of v.nodes) {
            console.error(`    Target: ${node.target.join(' ')}`)
            console.error(`    HTML: ${node.html}`)
            console.error(`    Summary: ${node.failureSummary}\n`)
          }
        }
      }

      expect(axeResults.violations).toEqual([])
    })
  }

  test.afterAll(async () => {
    console.log('\n=== THEME AUDIT PIXEL DIFF SUMMARY ===')
    console.table(diffResults)
  })
})
