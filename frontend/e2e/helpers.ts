import type { Page } from '@playwright/test'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export const ROUTES = [
  { name: 'welcome', path: '/' },
  { name: 'design-system', path: '/design-system' },
  { name: 'login', path: '/login' },
  { name: 'register', path: '/register' },
  { name: 'dashboard', path: '/dashboard' },
  { name: 'ingestion', path: '/ingestion' },
  { name: 'graph', path: '/graph' },
  { name: 'metrics', path: '/metrics' },
  { name: 'security', path: '/security' },
  { name: 'refactor', path: '/refactor' },
  { name: 'reports', path: '/reports' },
  { name: 'analytics', path: '/analytics' },
  { name: 'settings', path: '/settings' },
  { name: 'admin-users', path: '/admin/users' },
  { name: 'admin-audit', path: '/admin/audit' },
]

export const MOCK_ADMIN_USER = {
  id: 'usr-admin-1',
  full_name: 'Eleanor Vance',
  work_email: 'admin@archlens.io',
  employee_id: 'EMP-001',
  department: 'Platform Architecture',
  position: 'Chief Systems Architect',
  role: 'ADMIN',
  status: 'active',
  theme_preference: 'dark',
  notification_preferences: { email_reports: true, security_alerts: true },
}

export const ALL_PERMISSIONS = [
  'view:dashboard',
  'view:graph',
  'view:metrics',
  'view:reports',
  'view:smells',
  'run:ingestion',
  'view:refactor',
  'approve:refactor',
  'generate:reports',
  'view:security_findings',
  'export:security_reports',
  'view:team_analytics',
  'manage:users',
  'view:audit_logs',
]

export async function setupMocks(page: Page) {
  await page.route('**/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user: MOCK_ADMIN_USER,
        permissions: ALL_PERMISSIONS,
      }),
    })
  })

  await page.route('**/auth/demo-users', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  })

  await page.route('**/api/settings/profile', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_ADMIN_USER),
    })
  })

  await page.route('**/api/settings/preferences', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        theme_preference: 'dark',
        notification_preferences: {},
      }),
    })
  })

  await page.route('**/api/admin/users', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([MOCK_ADMIN_USER]),
    })
  })

  await page.route('**/api/admin/audit-logs*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'log-1',
          timestamp: new Date().toISOString(),
          user_id: 'usr-admin-1',
          user_email: 'admin@archlens.io',
          user_role: 'ADMIN',
          action: 'login_success',
          resource_type: 'user',
          resource_id: 'usr-admin-1',
          details: { ip: '127.0.0.1' },
          ip_address: '127.0.0.1',
        },
      ]),
    })
  })

  await page.route('**/api/analytics/team', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        team_size: 12,
        active_scans: 4,
        avg_health_score: 92,
      }),
    })
  })

  await page.route('**/api/reports/history*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  })

  // AI Feature Mock Endpoints (Zero network / fake provider in test mode)
  await page.route('**/api/ai/topology-summary*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        summary: 'Layered architecture with 3 tiers (API, domain, infrastructure).',
        community_names: { c1: 'API Gateway', c2: 'Domain Core' },
        is_ai_generated: true,
      }),
    })
  })

  await page.route('**/api/ai/metric-explanation*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        metric_name: 'cyclomatic_complexity',
        explanation: 'Measures linearly independent paths through program source code.',
        why_it_matters: 'Higher complexity correlates directly with defect probability and testing cost.',
        recommendations: ['Extract helper functions', 'Simplify nested conditional branching'],
        is_ai_generated: true,
      }),
    })
  })

  await page.route('**/api/ai/smell-fix*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        smell_type: 'circular_import',
        why_it_matters: 'Creates tight bidirectional coupling and hampers independent testability.',
        fix_outline: 'Extract common interfaces or shared types into an independent leaf module.',
        is_ai_generated: true,
      }),
    })
  })

  await page.route('**/api/ai/security-enrichment*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        finding_id: 'sec-001',
        explanation: 'Dynamic argument passed to subprocess execution without argument sanitization.',
        suggested_fix: 'Use a static list of string arguments and maintain shell=False.',
        false_positive_likelihood: 'low',
        false_positive_reason: 'Input parameter derives directly from untrusted HTTP request payload.',
        is_ai_generated: true,
      }),
    })
  })

  await page.route('**/api/ai/dashboard-summary*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        executive_summary: 'Overall architecture demonstrates strong modular separation with low coupling.',
        key_findings: ['High cohesion across core modules', 'Zero critical security vulnerabilities'],
        priority_actions: ['Refactor 2 circular dependency loops in domain layer'],
        is_ai_generated: true,
      }),
    })
  })

  await page.route('**/reports/narrative*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        executive_summary: 'Comprehensive analysis of repository architecture and structural maintainability.',
        what_this_means: 'Sound architecture with balanced layering and isolated dependencies.',
        why_it_matters: 'Protects developer velocity and limits unexpected blast radius during changes.',
        what_to_do: 'Address circular dependency warnings prior to major release.',
        is_ai_generated: true,
      }),
    })
  })

  await page.route('**/api/reports/narrative*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        executive_summary: 'Comprehensive analysis of repository architecture and structural maintainability.',
        what_this_means: 'Sound architecture with balanced layering and isolated dependencies.',
        why_it_matters: 'Protects developer velocity and limits unexpected blast radius during changes.',
        what_to_do: 'Address circular dependency warnings prior to major release.',
        is_ai_generated: true,
      }),
    })
  })

  await page.route('**/api/ai/chat*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        answer: 'The system is organized into a clean 3-tier architecture with entry points in app/main.py.',
        citations: [{ node_id: 'backend/app/main.py', title: 'Main Entry', snippet: 'FastAPI application' }],
        verified: true,
        is_ai_generated: true,
      }),
    })
  })

  await page.route('**/api/ai/nl-search*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        name_contains: 'service',
        min_complexity: null,
        max_instability: null,
        smell_type: null,
      }),
    })
  })

  await page.route('**/api/admin/ai/usage*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        total_calls: 58,
        total_tokens: 18450,
        total_cost_usd: 0.052,
        by_provider: {
          groq: { calls: 42, tokens: 12200, failures: 0 },
          gemini: { calls: 16, tokens: 6250, failures: 0 },
        },
      }),
    })
  })

  await page.route('**/graph/*', async (route) => {
    // Avoid intercepting frontend assets or other routes
    if (route.request().url().includes('/assets/') || route.request().url().includes('.js')) return
    const url = route.request().url()
    if (url.includes('00000000-0000-0000-0000-000000000000')) {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: "No analysis found for repo_id='00000000-0000-0000-0000-000000000000'" }),
      })
      return
    }
    await route.fallback()
  })

  await page.route('**/api/analysis/explain-metric*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        metric_name: 'test_metric',
        value: 42,
        explanation: 'Detailed architectural metric explanation with contextual analysis.',
        why_it_matters: 'Indicates coupling and structural stability across modules.',
        recommendations: ['Decouple core modules', 'Review circular imports'],
        is_ai_generated: true,
      }),
    })
  })

  await page.route('**/api/projects/compare*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        base_id: 'ana-001',
        target_id: 'ana-002',
        base_score: 82.0,
        target_score: 88.5,
        score_delta: 6.5,
        base_grade: 'B',
        target_grade: 'A',
        added_modules: ['app.services.auth', 'app.utils.crypto'],
        removed_modules: ['app.legacy.helper'],
        modified_modules: [
          {
            id: 'app.main',
            loc_before: 120,
            loc_after: 145,
            loc_delta: 25,
            complexity_before: 12,
            complexity_after: 10,
            complexity_delta: -2,
          },
        ],
        added_edges: [{ source: 'app.services.auth', target: 'app.utils.crypto' }],
        removed_edges: [],
        base_cycles: 2,
        target_cycles: 0,
        cycles_delta: -2,
        base_smells: 8,
        target_smells: 3,
        smells_delta: -5,
        summary: 'Architectural health improved by +6.5 points. All 2 circular dependencies were eliminated, and smell count dropped from 8 to 3.',
        is_ai_generated: true,
      }),
    })
  })

  await page.route('**/api/projects*', async (route) => {
    if (route.request().url().includes('/compare')) return
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          project_id: 'proj-archlens-main',
          name: 'archlens (main)',
          repo_url: 'https://github.com/acme/archlens.git',
          branch: 'main',
          last_analyzed: new Date().toISOString(),
          analysis_count: 5,
          latest_analysis_id: 'ana-002',
          score: 88.5,
          grade: 'A',
          cycles: 0,
          smells: 3,
          risk_score: 21.5,
          total_nodes: 42,
          total_edges: 86,
          languages: { python: 32, typescript: 10 },
          history: [
            {
              analysis_id: 'ana-002',
              created_at: new Date().toISOString(),
              commit_sha: 'c1a2b3d4',
              status: 'complete',
              score: 88.5,
              cycles: 0,
              smells: 3,
              node_count: 42,
              edge_count: 86,
            },
            {
              analysis_id: 'ana-001',
              created_at: new Date(Date.now() - 86400000).toISOString(),
              commit_sha: 'a0b1c2d3',
              status: 'complete',
              score: 82.0,
              cycles: 2,
              smells: 8,
              node_count: 40,
              edge_count: 82,
            },
          ],
        },
      ]),
    })
  })
}

export async function createE2EAnalysisAndReport(request: any): Promise<string> {
  const fixtureZipPath = path.resolve(__dirname, '../../backend/tests/fixtures/mini_repo.zip')
  if (!fs.existsSync(fixtureZipPath)) return ''
  const fileBuffer = fs.readFileSync(fixtureZipPath)

  const uploadRes = await request.post('http://127.0.0.1:8000/ingest/archive', {
    multipart: {
      archive: {
        name: 'mini_repo.zip',
        mimeType: 'application/zip',
        buffer: fileBuffer,
      },
    },
  })
  if (!uploadRes.ok()) return ''
  const uploadJson = await uploadRes.json()
  const jobId = uploadJson.job_id

  let analysisId = ''
  for (let i = 0; i < 30; i++) {
    const jobRes = await request.get(`http://127.0.0.1:8000/jobs/${jobId}`)
    if (jobRes.ok()) {
      const jobData = await jobRes.json()
      if (jobData.status === 'completed' || jobData.status === 'complete') {
        analysisId = jobData.result?.repo_id || jobData.result?.id || jobId
        break
      }
    }
    await new Promise((r) => setTimeout(r, 500))
  }
  if (analysisId) {
    await request.get(`http://127.0.0.1:8000/reports/${analysisId}/pdf`)
  }
  return analysisId
}

