import { test, expect } from '@playwright/test'
import path from 'path'

const ARTIFACTS_DIR = 'C:/Users/mmoha/.gemini/antigravity-ide/brain/f406697d-bd3c-4749-83f7-baf55fb467e5'

test.describe('Capture in-app report screenshots for Clean and Cycle repos', () => {
  test('Capture in-app screenshots for clean repo and cycle repo', async ({ page, request }) => {
    // 1. Trigger Clean Repo analysis on backend
    const cleanReq = await request.post('http://127.0.0.1:8000/analyze', {
      data: {
        path: path.resolve('../backend/tests/fixtures/python'),
        language: 'python',
        include_tests: false,
      },
    })
    expect(cleanReq.ok()).toBeTruthy()
    const cleanData = await cleanReq.json()
    const cleanId = cleanData.repo_id
    console.log('Clean repo analysis ID:', cleanId)

    // 2. Trigger Cycle Repo (mini_repo) analysis on backend
    const cycleReq = await request.post('http://127.0.0.1:8000/analyze', {
      data: {
        path: path.resolve('../backend/tests/fixtures/mini_repo'),
        language: 'python',
        include_tests: false,
      },
    })
    expect(cycleReq.ok()).toBeTruthy()
    const cycleData = await cycleReq.json()
    const cycleId = cycleData.repo_id
    console.log('Cycle repo analysis ID:', cycleId)

    // Set viewport
    await page.setViewportSize({ width: 1366, height: 900 })

    // ── 3. Navigate to Clean Report ──────────────────────────────────────────
    await page.goto(`http://localhost:5173/reports?analysis=${cleanId}`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    // Verify key narrative phrases in clean report
    const cleanText = await page.textContent('body')
    expect(cleanText).toContain('No circular dependencies were found')
    expect(cleanText).toContain('No monolithic god classes were detected')
    expect(cleanText).toContain('Zero critical security vulnerabilities')
    expect(cleanText).toContain('No significant risks found')
    expect(cleanText).not.toContain('Tight coupling and circular dependencies detected')

    // Capture clean in-app screenshot (Executive Summary & Risks)
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'in_app_clean_report.png'),
      fullPage: false,
    })

    // Capture entire clean report page
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'in_app_clean_report_full.png'),
      fullPage: true,
    })

    // ── 4. Navigate to Cycle Report ──────────────────────────────────────────
    await page.goto(`http://localhost:5173/reports?analysis=${cycleId}`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    // Verify key narrative phrases in cycle report
    const cycleText = await page.textContent('body')
    expect(cycleText).toContain('circular dependency loop')
    expect(cycleText).toContain('Cyclic Dependencies')
    expect(cycleText).toContain('Break Circular Dependency')

    // Capture cycle in-app screenshot (Executive Summary & Risks)
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'in_app_cycle_report.png'),
      fullPage: false,
    })

    // Capture entire cycle report page
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'in_app_cycle_report_full.png'),
      fullPage: true,
    })
  })
})
