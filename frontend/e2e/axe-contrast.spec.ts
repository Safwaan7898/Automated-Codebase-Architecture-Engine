import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { setupMocks } from './helpers'

const TARGET_PAGES = [
  { name: 'Dashboard', path: '/dashboard' },
  { name: 'Ingestion', path: '/ingestion' },
  { name: 'Reports', path: '/reports' },
  { name: 'Insights', path: '/insights' },
  { name: 'Projects', path: '/projects' },
]

test.describe('Axe Contrast Audit (Dashboard, Ingestion, Reports)', () => {
  for (const pageInfo of TARGET_PAGES) {
    for (const theme of ['dark', 'light'] as const) {
      test(`${pageInfo.name} - ${theme} theme contrast check`, async ({ page }) => {
        await setupMocks(page)

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

        await page.goto(pageInfo.path, { waitUntil: 'networkidle' })
        await page.waitForTimeout(600)

        const results = await new AxeBuilder({ page })
          .withRules(['color-contrast'])
          .analyze()

        if (results.violations.length > 0) {
          console.error(`\n❌ [Axe Contrast Violation] ${pageInfo.name} (${theme}):`)
          for (const v of results.violations) {
            console.error(`  Violation: ${v.id} - ${v.help}`)
            for (const node of v.nodes) {
              console.error(`    Target: ${node.target.join(' ')}`)
              console.error(`    HTML: ${node.html}`)
              console.error(`    Summary: ${node.failureSummary}\n`)
            }
          }
        }

        expect(results.violations).toEqual([])
      })
    }
  }
})
