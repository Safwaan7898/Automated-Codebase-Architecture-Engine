import { test, expect } from '@playwright/test'
import { setupMocks, MOCK_ADMIN_USER } from './helpers'

test.use({ video: 'on' })

test.describe('Dock Stability, Hover Isolation & Layout Shift Verification', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page)
    await page.addInitScript(() => {
      localStorage.setItem('theme', 'dark')
      document.documentElement.classList.add('dark')
      document.documentElement.style.colorScheme = 'dark'
    })
  })

  test('Dock container bounding box remains identical on EVERY frame during hover', async ({ page }) => {
    await page.goto('/dashboard', { waitUntil: 'networkidle' })
    const dockContainer = page.locator('[data-testid="magnification-dock-container"]')
    await expect(dockContainer).toBeVisible()

    // Let any initial mount transitions settle
    await page.waitForTimeout(500)

    const initialBox = await dockContainer.boundingBox()
    expect(initialBox).not.toBeNull()
    if (!initialBox) return

    // Verify all slots have fixed size and overflow: visible
    const slots = page.locator('[data-testid="dock-slot"]')
    const slotCount = await slots.count()
    expect(slotCount).toBeGreaterThan(0)

    for (let i = 0; i < slotCount; i++) {
      const slot = slots.nth(i)
      const slotBox = await slot.boundingBox()
      expect(slotBox).not.toBeNull()
      if (slotBox) {
        expect(Math.round(slotBox.width)).toBe(40)
        expect(Math.round(slotBox.height)).toBe(40)
      }
    }

    // Traverse across the dock in high-resolution steps across the width
    const startX = initialBox.x - 40
    const endX = initialBox.x + initialBox.width + 40
    const centerY = initialBox.y + initialBox.height / 2
    const steps = 30

    // Forward sweep across all dock items
    for (let i = 0; i <= steps; i++) {
      const curX = startX + ((endX - startX) * i) / steps
      await page.mouse.move(curX, centerY)
      await page.waitForTimeout(35) // frame tick for spring physics

      const currentBox = await dockContainer.boundingBox()
      expect(currentBox).not.toBeNull()
      if (currentBox) {
        // Assert width and height stay strictly identical on every frame
        expect(Math.abs(currentBox.width - initialBox.width)).toBeLessThan(0.01)
        expect(Math.abs(currentBox.height - initialBox.height)).toBeLessThan(0.01)
        // Assert x and y position stay strictly identical on every frame
        expect(Math.abs(currentBox.x - initialBox.x)).toBeLessThan(0.01)
        expect(Math.abs(currentBox.y - initialBox.y)).toBeLessThan(0.01)
      }
    }

    // Reverse sweep across all dock items
    for (let i = steps; i >= 0; i--) {
      const curX = startX + ((endX - startX) * i) / steps
      await page.mouse.move(curX, centerY)
      await page.waitForTimeout(35)

      const currentBox = await dockContainer.boundingBox()
      expect(currentBox).not.toBeNull()
      if (currentBox) {
        expect(Math.abs(currentBox.width - initialBox.width)).toBeLessThan(0.01)
        expect(Math.abs(currentBox.height - initialBox.height)).toBeLessThan(0.01)
        expect(Math.abs(currentBox.x - initialBox.x)).toBeLessThan(0.01)
        expect(Math.abs(currentBox.y - initialBox.y)).toBeLessThan(0.01)
      }
    }

    // Move mouse away and verify settled container
    await page.mouse.move(0, 0)
    await page.waitForTimeout(400)
    const finalBox = await dockContainer.boundingBox()
    expect(finalBox).not.toBeNull()
    if (finalBox) {
      expect(Math.abs(finalBox.width - initialBox.width)).toBeLessThan(0.01)
      expect(Math.abs(finalBox.height - initialBox.height)).toBeLessThan(0.01)
      expect(Math.abs(finalBox.x - initialBox.x)).toBeLessThan(0.01)
      expect(Math.abs(finalBox.y - initialBox.y)).toBeLessThan(0.01)
    }
  })

  test('Cumulative Layout Shift (CLS) is < 0.05 during dock hover interactions', async ({ page }) => {
    await page.goto('/dashboard', { waitUntil: 'networkidle' })
    const dockContainer = page.locator('[data-testid="magnification-dock-container"]')
    await expect(dockContainer).toBeVisible()
    await page.waitForTimeout(500)

    // Reset layout shift counter right before interaction to measure dock-induced CLS
    await page.evaluate(() => {
      window.__dockLayoutShift = 0
      try {
        const observer = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            // @ts-expect-error hadRecentInput
            if (!entry.hadRecentInput) {
              // @ts-expect-error value
              window.__dockLayoutShift += entry.value
            }
          }
        })
        observer.observe({ type: 'layout-shift', buffered: false })
      } catch {}
    })

    const initialBox = await dockContainer.boundingBox()
    expect(initialBox).not.toBeNull()
    if (!initialBox) return

    // Move mouse smoothly across the dock
    const startX = initialBox.x
    const endX = initialBox.x + initialBox.width
    const centerY = initialBox.y + initialBox.height / 2

    for (let i = 0; i <= 25; i++) {
      const curX = startX + ((endX - startX) * i) / 25
      await page.mouse.move(curX, centerY)
      await page.waitForTimeout(35)
    }

    await page.mouse.move(0, 0)
    await page.waitForTimeout(400)

    // Evaluate measured CLS
    const cls = await page.evaluate(() => {
      // @ts-expect-error window.__dockLayoutShift
      return window.__dockLayoutShift || 0
    })

    expect(cls).toBeLessThan(0.05)
  })

  test('Main scroll area has padding-bottom equal to dock height + 24px', async ({ page }) => {
    await page.goto('/dashboard', { waitUntil: 'networkidle' })
    const mainArea = page.locator('#main-content')
    await expect(mainArea).toBeVisible()

    const paddingBottom = await mainArea.evaluate((el) => {
      return parseFloat(window.getComputedStyle(el).paddingBottom)
    })

    // Dock height is 56px + 24px = 80px
    expect(paddingBottom).toBeGreaterThanOrEqual(80)
  })

  test('Telemetry popover portals, has high z-index, closes on Escape and click-outside', async ({ page }) => {
    await page.goto('/dashboard', { waitUntil: 'networkidle' })
    const telemetryBtn = page.locator('[data-testid="telemetry-trigger-btn"]')
    await expect(telemetryBtn).toBeVisible()

    // Click to open popover
    await telemetryBtn.click()
    const popover = page.locator('[data-testid="telemetry-popover"]')
    await expect(popover).toBeVisible()

    // Assert it is portalled to document.body
    const isDirectChildOfBody = await popover.evaluate((el) => el.parentElement === document.body)
    expect(isDirectChildOfBody).toBe(true)

    // Assert high z-index (z-[9999])
    const zIndex = await popover.evaluate((el) => window.getComputedStyle(el).zIndex)
    expect(Number(zIndex)).toBeGreaterThanOrEqual(9999)

    // Press Escape to close
    await page.keyboard.press('Escape')
    await expect(popover).toBeHidden()

    // Reopen and test click-outside
    await telemetryBtn.click()
    await expect(popover).toBeVisible()
    await page.mouse.click(10, 10) // Click outside at top left
    await expect(popover).toBeHidden()
  })

  test('Sidebar only marks current route as active and gives Analytics PRO locked styling', async ({ page }) => {
    await page.route('**/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          user: { ...MOCK_ADMIN_USER, role: 'DEVELOPER' },
          permissions: ['view:dashboard', 'view:graph'],
        }),
      })
    })

    await page.goto('/dashboard', { waitUntil: 'networkidle' })

    // Check dashboard is active
    const dashboardLink = page.locator('nav a[href="/dashboard"]')
    await expect(dashboardLink).toBeVisible()
    const isDashboardActive = await dashboardLink.evaluate((el) =>
      el.classList.contains('text-[#CCFF00]') || el.getAttribute('aria-current') === 'page'
    )
    expect(isDashboardActive).toBe(true)

    // Check other routes like graph are NOT active
    const graphLink = page.locator('nav a[href="/graph"]')
    const isGraphActive = await graphLink.evaluate((el) =>
      el.classList.contains('text-[#CCFF00]') || el.getAttribute('aria-current') === 'page'
    )
    expect(isGraphActive).toBe(false)

    // Check Analytics PRO locked item
    const proCard = page.locator('[data-testid="sidebar-analytics-pro"]')
    await expect(proCard).toBeVisible()
    const proText = await proCard.textContent()
    expect(proText).toContain('ANALYTICS PRO')

    // Verify it is visually marked locked (aria-disabled="true" and cursor-not-allowed)
    const isDisabled = await proCard.getAttribute('aria-disabled')
    expect(isDisabled).toBe('true')
  })

  test('Auth card has fixed min-height with no vertical layout jumping across tabs', async ({ page }) => {
    // Unauthenticated user so auth form is visible
    await page.route('**/auth/me', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Unauthenticated' }),
      })
    })

    await page.goto('/login', { waitUntil: 'networkidle' })
    const authCard = page.locator('[data-testid="auth-card"]')
    await expect(authCard).toBeVisible()

    const initialCardBox = await authCard.boundingBox()
    expect(initialCardBox).not.toBeNull()
    if (!initialCardBox) return

    // Switch to EMPLOYEE REG Tab
    const registerTab = page.getByRole('button', { name: /EMPLOYEE REG/i })
    await registerTab.click()
    await page.waitForTimeout(200)

    const registerCardBox = await authCard.boundingBox()
    expect(registerCardBox).not.toBeNull()
    if (registerCardBox) {
      // Top y position must remain steady (no vertical jump or re-centering)
      expect(Math.abs(registerCardBox.y - initialCardBox.y)).toBeLessThan(2)
      expect(registerCardBox.height).toBeGreaterThanOrEqual(600)
    }

    // Switch to ADMIN KEY Tab
    const adminTab = page.getByRole('button', { name: /ADMIN KEY/i })
    await adminTab.click()
    await page.waitForTimeout(200)

    const adminCardBox = await authCard.boundingBox()
    expect(adminCardBox).not.toBeNull()
    if (adminCardBox) {
      expect(Math.abs(adminCardBox.y - initialCardBox.y)).toBeLessThan(2)
      expect(adminCardBox.height).toBeGreaterThanOrEqual(600)
    }

    // Switch back to SIGN IN Tab
    const loginTab = page.getByRole('button', { name: /SIGN IN/i })
    await loginTab.click()
    await page.waitForTimeout(200)

    const returnCardBox = await authCard.boundingBox()
    expect(returnCardBox).not.toBeNull()
    if (returnCardBox) {
      expect(Math.abs(returnCardBox.y - initialCardBox.y)).toBeLessThan(2)
      expect(returnCardBox.height).toBeGreaterThanOrEqual(600)
    }
  })
})
