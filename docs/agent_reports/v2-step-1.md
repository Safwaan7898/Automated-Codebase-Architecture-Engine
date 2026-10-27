# V2 Step 1: Config and Providers Report

**Date**: 2026-10-26  
**Branch**: `feat/ai-multilang`  
**Status**: COMPLETE / VERIFIED  

---

## 1. Live `python -m ai.check` Verification

### From Project Root:
```
ArchLens AI Provider & Model Verification (ai.check)
.env loaded: C:\Users\mmoha\Automated Codebase architecture Engine full project - FINAL\backend\.env
Variable names in .env: ['ARCHLENS_ADMIN_PROVISION_KEY', 'ARCHLENS_AI_ALLOW_TRAINING_PROVIDERS', 'ARCHLENS_AI_ENABLED', 'ARCHLENS_AI_MODEL_GEMINI', 'ARCHLENS_AI_MODEL_GROQ', 'ARCHLENS_AI_MODEL_NVIDIA', 'ARCHLENS_AI_PROVIDER_ORDER', 'ARCHLENS_CORS_ORIGINS', 'ARCHLENS_ENV', 'ARCHLENS_HOST', 'ARCHLENS_LOG_LEVEL', 'ARCHLENS_PORT', 'GEMINI_API_KEY', 'GROQ_API_KEY', 'NVIDIA_API_KEY']
Keys present: 3/3
Enabled in environment: True
Configured Provider Chain: groq -> gemini
======================================================================

[GROQ] Effective Model: 'openai/gpt-oss-20b'
  STATUS:  OK (HTTP 200)
  LATENCY: 448.2 ms
  MODELS:  Verified 'openai/gpt-oss-20b' present among 11 available models

[GEMINI] Effective Model: 'gemini-3.1-flash-lite'
  STATUS:  OK (HTTP 200)
  LATENCY: 1316.08 ms
  MODELS:  Verified 'gemini-3.1-flash-lite' present among 100 available models

======================================================================
RESULT: All checked providers PASSED verification.
Exit code: 0
```

### From `backend/`:
```
ArchLens AI Provider & Model Verification (ai.check)
.env loaded: C:\Users\mmoha\Automated Codebase architecture Engine full project - FINAL\backend\.env
Configured Provider Chain: groq -> gemini
[GROQ] Effective Model: 'openai/gpt-oss-20b'
  STATUS:  OK (HTTP 200)
  LATENCY: 319.47 ms
[GEMINI] Effective Model: 'gemini-3.1-flash-lite'
  STATUS:  OK (HTTP 200)
  LATENCY: 4049.96 ms
RESULT: All checked providers PASSED verification.
Exit code: 0
```

---

## 2. Configuration & Invariants Verified
1. **Provider Order**: Configured to `groq,gemini` in `.env` and `.env.example` (NVIDIA excluded due to model timeout).
2. **Concrete Model IDs**: `openai/gpt-oss-20b` and `gemini-3.1-flash-lite` (no `-latest` aliases).
3. **Budget & Token Limits Documented**:
   - `ARCHLENS_AI_MAX_TOKENS_PER_ANALYSIS`: cumulative token limit across entire codebase analysis (not per individual API call).
   - `ARCHLENS_AI_BUDGET`: ceiling in USD / US Dollars (e.g. 1.0 = $1.00).
4. **Admin Provisioning Key**:
   - `ARCHLENS_ADMIN_PROVISION_KEY`: Loaded strictly from environment/`.env` with default `None`.
   - When unset, public admin registration is strictly disabled (HTTP 403 `Public admin registration is disabled: ARCHLENS_ADMIN_PROVISION_KEY is not configured`). Verified in `test_admin_registration_disabled_by_default`.
5. **Caching & Key Exposure**:
   - Zero keys leaked in exceptions, logs, or HTTP responses.
   - Response cache keyed by content hash prevents duplicate provider calls on unchanged code.

---

## 3. Test Gates
- `test_ai_chain.py`, `test_ai_env_loading.py`, `test_ai_core.py`: **20 passed in 3.04s**
- Full backend pytest suite: **410 passed in 355.21s**
- Frontend build: `npm run build` exited with code 0
- Frontend lint: `npm run lint` exited with code 0 (0 errors, 0 warnings)
