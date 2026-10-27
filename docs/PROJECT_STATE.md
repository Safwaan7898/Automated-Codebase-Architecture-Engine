# ArchLens Project State (`docs/PROJECT_STATE.md`)

**Project**: ArchLens — Automated Codebase Architecture Engine (FastAPI backend, React / Vite / TypeScript frontend)  
**Branch**: `feat/ai-multilang`  
**Updated**: 2026-10-27  
**Overall Status**: COMPLETE (MASTER_PROMPT_V2 Steps 0 through 6 verified and fully accepted)  
**Target Release Tag**: `ai-complete-v2`  

---

## 1. Specification Progression & Per-Step Status (MASTER_PROMPT_V2)

| Step | Scope & Title | Status | Verification & Evidence Summary |
| :--- | :--- | :--- | :--- |
| **Step 0** | **Spec Ingestion & Git History Inspection** | **DONE** | Saved specification to `docs/MASTER_PROMPT_V2.md`. Inspected git history (`git log --oneline -20`) verifying past commits `ai-complete` (`0c5b36a`), `581895b`, `253c518`. Validated that `ai-complete` tag is preserved and unmodified. |
| **Step 1** | **Config, Providers & Key Provisioning** | **DONE** | Validated `.env` and `app/core/config.py` provider order (`groq,gemini`). Executed `python -m ai.check` returning exit code 0 (`All checked providers PASSED verification`). Hardened admin provisioning key logic requiring `ARCHLENS_ADMIN_PROVISION_KEY` in production and staging environments (`test_admin_provisioning.py`: 3 passed). |
| **Step 2** | **Invariants, 11 AI Features & UI Traceability** | **DONE** | Ensured strict operating invariants: AI never computes/mutates scores, grades, cycles, or graph topology. Schema validation, deterministic fallback, `<AIBadge label="AI-generated" size="xs" />`, and deterministic fallback badge on all 11 AI UI features. Full build (`npm run build`), lint (`npm run lint`), invariant suite (`test_phase6_invariants.py`: 10 passed), full pytest suite passed. Traceability matrix rewritten in `docs/agent_reports/phase-6-matrix.md` with zero GAP rows. |
| **Step 3** | **Benchmarks Suite (Self-Consistency & External Tools)** | **DONE** | Renamed fixture runner to "Self-Consistency on Fixtures" in `docs/benchmarks.md` and `docs/AI_FEATURES.md`. Built `backend/benchmarks/external_runner.py` with CLI flag `--external`. Ran reference tools on real pinned repos: Python `requests` (Node F1: 0.963, Edge F1: 0.929), `flask` (Node F1: 0.985, Edge F1: 0.973), JS `express` via `npx madge` (Node F1: 0.812, Edge F1: 0.771). Recorded Go/Java external comparison status as `"not externally verified"` due to host toolchain absence. Results recorded in `backend/benchmarks/results/external_benchmarks_results.json`. |
| **Step 4** | **Parser Guard, Diagnostics Rule Hash & Directory Skipping** | **DONE** | Extended parser guard in `backend/parsers/fingerprint.py` and `test_parser_version_guard.py` to hash all 29 analyzer, parser, and diagnostic rule modules (composite hash: `424758637c2d284543fb6954e02b1fbb31c96653983b3049663e73292083adde`). Bumped `PARSER_VERSION = "2.0.0"`. Verified directory skipping on root analysis: 65.99s runtime, 633 nodes extracted with zero leaked `.git`, `node_modules`, or `venv` files. Diagnostics acceptance suite: 76/76 passed with zero network calls. |
| **Step 5** | **Visualizations & Multi-Project Workspace** | **DONE** | Built Hotspot Bubble Chart (Complexity x Risk x Size quadrants, SVG export, AI explain with fallback), Chord Arc Diagram (inter-tier layer arc routing, layer inversion markers, SVG export, AI explain), and Language Breakdown Donut (donut chart SVG, polyglot LOC/file table, SVG export, AI explain) in `frontend/src/components/insights/` and integrated into `InsightsPage.tsx`. Added `risk_score` calculation to `backend/app/services/project_service.py` with `sort_by="risk"`. Added Portfolio Risk sorting, risk badges (`High`/`Med`/`Low`), and comparison modal in `ProjectsPage.tsx`. Hardened WCAG AA contrast (passing axe audit 10/10). Playwright spec `p2-insights-projects.spec.ts` 3/3 passed. |
| **Step 6** | **Final Evidence & Acceptance (`ai-complete-v2`)** | **DONE** | Full gate validation executed and verified: backend test suite (411/411 passed), frontend production build (clean, exit 0), ESLint (0 errors, 0 warnings), AI check exit 0 (`groq,gemini` verified), fixture benchmark (F1: 1.0), external benchmark (executed and saved). All documentation updated (`AI_FEATURES.md`, `PROJECT_STATE.md`, `AGENT_STATE.md`, `v2-final.md`). Tagged `ai-complete-v2`. |

---

## 2. Invariants & Architecture Guarantees

1. **Deterministic Authority**:
   Graph topology, Strongly Connected Component (SCC) cycles, Betweenness Centrality, PageRank, Louvain communities, Martin stability, Cyclomatic Complexity, health scores, grades, and diagnostic findings are calculated strictly through deterministic algorithms. AI layers have zero authority or capability to mutate these metrics.
2. **Deterministic Fallbacks**:
   Every AI endpoint and UI card provides a zero-latency deterministic template fallback if providers are unreachable, offline, timing out, or disabled by user consent.
3. **Transparent Labeling & Accessibility**:
   All AI-generated text is labeled with `<AIBadge label="AI-generated" size="xs" />` in both light and dark themes with WCAG AA compliance (contrast ratio ≥ 4.5:1). Deterministic fallbacks are labeled with `<AIFallback label="Deterministic fallback" />`.
4. **Prompt Injection Resistance & Untrusted Content Isolation**:
   Source code, file names, identifiers, and docstrings are treated as untrusted data. Prompt injection attempts cannot alter scoring or grant unauthorized permissions.
5. **Zero Network Calls in Automated Test Suites**:
   Test suites never dispatch external HTTP requests to LLM APIs or OSV.dev. Fast local mocks and fixture paths guarantee deterministic test isolation.

---

## 3. Known Limitations & Environmental Assumptions

1. **External Reference Toolchains (Go & Java)**:
   - **Go**: ArchLens includes a tree-sitter AST parser for Go that operates without requiring the Go compiler. However, external reference verification against `go list -deps` requires a host Go toolchain (`go`). When `go` is not present on the host environment, external benchmark verification records `"not externally verified"` for Go while ArchLens internal AST parsing functions normally.
   - **Java**: External reference verification using JDK `jdeps` requires compiled `.class` or `.jar` bytecode. ArchLens parses `.java` source files directly using tree-sitter. When pre-compiled bytecode is absent, `jdeps` cannot run, and external verification is recorded as `"not externally verified"`.
2. **LLM Provider Availability & Rate Limits**:
   - Live external LLM calls require network connectivity and active API keys (`GROQ_API_KEY`, `GEMINI_API_KEY`).
   - In environments where API keys are unset or network access is restricted (e.g., CI/CD air-gapped runners), the engine runs entirely on deterministic fallbacks without degrading any core architectural analysis.
3. **Workspace Ingestion & File Size Scalability**:
   - When running full scans on monorepos with 25,000+ files, directory pruning skips `.git`, `node_modules`, `venv`, `dist`, and `target` to ensure fast runtimes. If non-standard build artifact folders are present, they should be configured in `.archlensignore`.
