# ArchLens Agent State (`docs/AGENT_STATE.md`)

**Branch**: `feat/ai-multilang`  
**Current Phase**: T9 (CI Pipeline) & T1 (Playwright Suite with Backend) Completed  
**Last Updated**: 2026-10-27  
**Active Work**: T9 CI pipeline verified passing locally (all checks 0); T1 Playwright suite running self-contained with real backend (74/74 passed, stable on re-run, no baselines modified).

---

## Operating Invariants

1. Work on `feat/ai-multilang`.
2. Commit after every task with a clear message and specific file staging (`git add <file>`). Never `git add .` or `git add -A`.
3. Secret-scan every staged diff before committing (`rg -i "api[_-]?key|secret|password|token"`).
4. Gates after every phase:
   - Backend: `pytest -q` fully green (411/411 passed).
   - Frontend: `npm run build` (clean production build), `npm run lint` (0 errors, 0 warnings).
   - Playwright: Axe WCAG AA contrast audit and P2 visualization suite 13/13 passed.
   - Provider check: `python -m ai.check` exit 0 (`groq`, `gemini` verified).
   - Benchmarks: `python -m benchmarks.runner` (F1: 1.0) and `python -m benchmarks.runner --external` (results saved).
   - `git status` clean after commit.
   - `docs/AGENT_STATE.md` updated and `docs/agent_reports/` written with raw gate outputs.
5. Invariant enforcement: AI never alters graph topology, cycles, scores, grades, or diagnostic finding counts. Transparent `<AIBadge label="AI-generated" size="xs" />` and deterministic fallbacks on every AI screen.
6. Forbidden git operations: `reset --hard`, `clean`, `stash drop`, `push --force`, deleting branches/tags, rewriting history. Never move or delete existing tags (`ai-complete`).

---

## MASTER_PROMPT_V2 Progression & Status

| Step | Title | Status | Report / Evidence Artifact |
| :--- | :--- | :--- | :--- |
| **Step 0** | Specs & Git History Inspection | **DONE** | `docs/agent_reports/v2-step-0.md` (Commit: `2e8938f`) |
| **Step 1** | Config, Providers & Key Provisioning | **DONE** | `docs/agent_reports/v2-step-1.md` (Commit: `d962a1c`) |
| **Step 2** | Invariants, 11 AI Features & UI Traceability | **DONE** | `docs/agent_reports/v2-step-2.md`, `phase-6-matrix.md` (Commit: `f29007a`) |
| **Step 3** | Benchmarks Suite (Self-Consistency & External Tools) | **DONE** | `docs/agent_reports/v2-step-3.md`, `benchmarks.md` (Commit: `899afc8`) |
| **Step 4** | Parser Guard, Diagnostics Rule Hash & Directory Skipping | **DONE** | `docs/agent_reports/v2-step-4.md` (Commit: `aa526cc`) |
| **Step 5** | Visualizations & Multi-Project Workspace (Hotspots, Chord, Donut, Risk) | **DONE** | `docs/agent_reports/v2-step-5.md` (Commit: `cb75c08`) |
| **Step 6** | Final Evidence & Acceptance (`ai-complete-v2`) | **DONE** | `docs/agent_reports/v2-final.md`, `docs/AI_FEATURES.md`, `docs/PROJECT_STATE.md` |

---

## Release Artifacts

- **Tag**: `ai-complete-v2`
- **Previous Preserved Tag**: `ai-complete` (`0c5b36a`)
- **Documentation**:
  - `docs/AI_FEATURES.md`: Full verification table with all 11 AI features, AskArchLens, and P2 additions.
  - `docs/PROJECT_STATE.md`: Per-step status, invariants, and honest known limitations.
  - `docs/agent_reports/v2-final.md`: Raw summary outputs of all validation gates.
  - `docs/agent_reports/phase-6-matrix.md`: Zero-gap component traceability matrix.
