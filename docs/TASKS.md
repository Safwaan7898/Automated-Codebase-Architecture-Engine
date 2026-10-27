# ArchLens Tasks Tracking (`docs/TASKS.md`)

- [x] **T1**: Run the full Playwright suite with a real backend
  - Self-contained dual webServer in `frontend/playwright.config.ts` (Vite dev server + Uvicorn with `ARCHLENS_ENV=test`, temporary data dir, fake AI provider guard against production).
  - All 74 tests executed and passed (`74 passed (3.6m)`, 0 failed, 0 skipped).
  - Stability verified on re-run (`74 passed (3.6m)`).
  - Theme pixel-diff baselines unchanged; working tree free of test output.

- [x] **T9**: Make the real CI pipeline pass locally
  - Backend: `python -m ruff check app tests` (exit 0, all checks passed).
  - Backend: `python -m ruff format --check app tests` (exit 0, 126 files already formatted).
  - Backend: `python -m pytest tests/ -v --tb=short --cov=app --cov-report=term-missing --cov-report=xml` (exit 0, 411 passed).
  - Frontend: `npm run lint` (exit 0, 0 errors, 0 warnings).
  - Frontend: `npx tsc --noEmit` (exit 0).
  - Frontend: `npm run build` (exit 0, production build clean).
  - Smoke test: `GET /health` returns status ok (`{"status":"ok","version":"0.1.0","environment":"development"}`).
