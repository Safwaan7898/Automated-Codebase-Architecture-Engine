# Phase 5 Report: AI Core (Provider Interface, Adapters, Fallback)

## 1. Overview
Phase 5 implements the modular, privacy-first AI Core foundation for ArchLens (`backend/ai/`):
- **Provider Interface & Registry**:
  - `BaseAIProvider`: Abstract class managing token budgeting, per-analysis cost caps, timeout handling, and exponential backoff retry loops.
  - Adapters: `FakeProvider` (deterministic mock for tests and offline execution), `GeminiProvider` (Google Gemini REST API), `AnthropicProvider` (Claude Messages API), and `OpenAIProvider` (OpenAI-compatible Chat Completions API).
- **Graceful Degradation & Fallback**:
  - `AIService.invoke_feature(...)` wraps all invocations with automatic fallback to deterministic baselines if AI is disabled, times out, exceeds budget, or encounters network errors.
- **Privacy & Secret Redaction**:
  - `backend/ai/privacy.py`: Regular expression and pattern matching scrubbing AWS access keys, GitHub/GitLab tokens, Slack tokens, JWTs, database connection strings, passwords, and RSA/EC private keys prior to prompt construction.
- **Security & Prompt-Injection Defense**:
  - `backend/ai/security.py`: Untrusted repository source code is wrapped in explicit isolation boundaries (`<<<BEGIN_UNTRUSTED_DATA:...>>>`) with anti-jailbreak instructions.
  - Structured output validator (`validate_grounded_references`): Verifies that every referenced node, file, or line in structured AI outputs exists in the deterministic graph, discarding hallucinated references.
- **Auditing & Telemetry**:
  - `backend/ai/audit.py`: Records token counts, model names, latency, and costs directly into the system audit trail without logging prompts containing user source code.
- **Hard Invariant Verification**:
  - Proven with automated acceptance test `test_hard_invariant_scores_and_graphs_identical_with_ai_on_and_off`: Architecture scores, grades, sub-scores, node counts, edge sets, and circular dependency detection are 100% bit-identical with AI enabled versus AI disabled.

---

## 2. Backend Test Gate
Command: `..\venv\Scripts\python.exe -m pytest -q` (executed in `backend/`)
```
================ 367 passed, 728 warnings in 273.67s (0:04:33) ================
```
Status: PASS (367 passed, 0 failed, 100% green)

### Specific AI Core Test Gate
Command: `..\venv\Scripts\python.exe -m pytest tests/test_ai_core.py -v` (executed in `backend/`)
```
tests/test_ai_core.py::test_provider_factory_and_adapters PASSED         [ 11%]
tests/test_ai_core.py::test_secret_redaction PASSED                      [ 22%]
tests/test_ai_core.py::test_prompt_injection_isolation PASSED            [ 33%]
tests/test_ai_core.py::test_reference_grounding_validation PASSED        [ 44%]
tests/test_ai_core.py::test_budget_exhaustion_enforcement PASSED         [ 55%]
tests/test_ai_core.py::test_response_caching PASSED                      [ 66%]
tests/test_ai_core.py::test_graceful_degradation PASSED                  [ 77%]
tests/test_ai_core.py::test_graceful_degradation_when_disabled PASSED    [ 88%]
tests/test_ai_core.py::test_hard_invariant_scores_and_graphs_identical_with_ai_on_and_off PASSED [100%]
======================= 9 passed, 151 warnings in 4.11s =======================
```
Status: PASS (9 passed, 0 failed)

---

## 3. Frontend Build Gate
Command: `npm run build` (executed in `frontend/`)
```
> frontend@0.0.0 build
> tsc -b && vite build

vite v8.3.2 building client environment for production...
transforming...
✓ 2411 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   1.91 kB │ gzip:   0.94 kB
dist/assets/index-BBxKr2Ik.css   94.64 kB │ gzip:  15.75 kB
dist/assets/index-C8Gf_Kqq.js   916.64 kB │ gzip: 257.31 kB
✓ built in 4.36s
```
Status: PASS (Exit code 0)

---

---

## 5. Provider Chain Addendum (Phase 5 Finish)
- **Multi-Provider Failover Chain**:
  - `ARCHLENS_AI_PROVIDER_ORDER` configuration (e.g. `groq,nvidia,gemini,ollama`).
  - Adapters:
    - Groq (`https://api.groq.com/openai/v1`) using OpenAI-compatible interface.
    - NVIDIA NIM (`https://integrate.api.nvidia.com/v1`) using OpenAI-compatible interface.
    - Gemini (`https://generativelanguage.googleapis.com/v1beta`) using dedicated REST adapter (`trains_on_prompts=True`).
    - Ollama (`http://localhost:11434`, optional local provider, no key required).
  - Exponential backoff and ordered failover across providers on 429, timeout, or quota errors.
  - Providers without API keys automatically skipped (except Ollama and FakeProvider).
  - Sliding-window Requests-Per-Minute (`rpm_limit`) rate limiter per provider respecting `Retry-After` HTTP headers.
- **Privacy Controls**:
  - Training providers (`gemini`) automatically skipped for private repos (when token supplied) or ZIP/folder source uploads unless `ARCHLENS_AI_ALLOW_TRAINING_PROVIDERS=true`.
  - Secret redaction prevents API keys from ever leaking in exceptions, logs, or status outputs.
  - Documented in `.env.example`: `ARCHLENS_AI_MAX_TOKENS_PER_ANALYSIS` (per analysis) and `ARCHLENS_AI_BUDGET` (USD ceiling).
- **Admin Endpoints**:
  - `/admin/ai/status` and `/api/admin/ai/status`: Reports per-provider health, RPM usage, cooldowns, and remaining quota (strictly zero API keys).
- **CLI Model Verification (`python -m ai.check`)**:
  - Probes configured providers, verifies model ID presence against remote model listings, sends 1-token request, displays OK/FAIL with latency and HTTP status, and suggests closest matching IDs on mismatch with non-zero exit code.
- **Provider Chain Test Suite Gate**:
  - Command: `..\venv\Scripts\python.exe -m pytest tests/test_ai_chain.py -v` (executed in `backend/`)
  - Output: 5 passed, 0 failed in 1.54s
- **Full Backend Pytest Gate**:
  - Command: `..\venv\Scripts\python.exe -m pytest -q` (executed in `backend/`)
  - Output: 372 passed, 0 failed in 285.15s (100% green)
