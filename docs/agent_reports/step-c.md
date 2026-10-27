# Step C Report: Verify the Provider Chain

## Summary
- **Ordered Failover Chain**: Verified sequential failover according to `ARCHLENS_AI_PROVIDER_ORDER`.
- **429 & Retry-After Handling**: Verified exponential backoff and provider cooldown respecting `Retry-After` header.
- **Privacy & Upload Skipping**: Providers with `trains_on_prompts=True` (Gemini) are automatically skipped for private repositories or ZIP/folder source uploads unless `ARCHLENS_AI_ALLOW_TRAINING_PROVIDERS=true`.
- **Robust JSON Extraction for Reasoning Models**: Implemented `backend/ai/json_utils.py` extracting clean JSON objects and Pydantic models from reasoning model outputs containing `<think>...</think>` tags, markdown code blocks, or conversational preambles/postambles.
- **Per-Analysis Budget Enforcement**: Added `check_budget()` and token/cost accumulation tracking to `ProviderChain` ensuring `ARCHLENS_AI_MAX_TOKENS_PER_ANALYSIS` and `ARCHLENS_AI_BUDGET` ceilings are enforced across calls.
- **Live Provider Probe Verification (`python -m ai.check`)**:
  - Groq (`openai/gpt-oss-20b`): HTTP 200, latency ~400-500 ms, 11 models available.
  - NVIDIA (`google/diffusiongemma-26b-a4b-it`): HTTP 200, latency ~720-1000 ms, 85 models available.
  - Gemini (`gemini-3.1-flash-lite`): HTTP 200, latency ~700-880 ms, 100 models available.
  - All configured models are concrete versions with zero `-latest` alias warnings.

## Gate Outputs

### Live Probe Output (`python -m ai.check`)
```
======================================================================
ArchLens AI Provider & Model Verification (ai.check)
.env loaded: C:\Users\mmoha\Automated Codebase architecture Engine full project - FINAL\backend\.env
Variable names in .env: ['ARCHLENS_ADMIN_PROVISION_KEY', 'ARCHLENS_AI_ALLOW_TRAINING_PROVIDERS', 'ARCHLENS_AI_ENABLED', 'ARCHLENS_AI_MODEL_GEMINI', 'ARCHLENS_AI_MODEL_GROQ', 'ARCHLENS_AI_MODEL_NVIDIA', 'ARCHLENS_AI_PROVIDER_ORDER', 'ARCHLENS_CORS_ORIGINS', 'ARCHLENS_ENV', 'ARCHLENS_HOST', 'ARCHLENS_LOG_LEVEL', 'ARCHLENS_PORT', 'GEMINI_API_KEY', 'GROQ_API_KEY', 'NVIDIA_API_KEY']
Keys present: 3/3
Enabled in environment: True
Configured Provider Chain: groq -> nvidia -> gemini
======================================================================

[GROQ] Effective Model: 'openai/gpt-oss-20b'
  STATUS:  OK (HTTP 200)
  LATENCY: 403.33 ms
  MODELS:  Verified 'openai/gpt-oss-20b' present among 11 available models

[NVIDIA] Effective Model: 'google/diffusiongemma-26b-a4b-it'
  STATUS:  OK (HTTP 200)
  LATENCY: 720.84 ms
  MODELS:  Verified 'google/diffusiongemma-26b-a4b-it' present among 85 available models

[GEMINI] Effective Model: 'gemini-3.1-flash-lite'
  STATUS:  OK (HTTP 200)
  LATENCY: 701.94 ms
  MODELS:  Verified 'gemini-3.1-flash-lite' present among 100 available models

======================================================================
RESULT: All checked providers PASSED verification.
```

### AI Test Suites (`pytest tests/test_ai_chain.py tests/test_ai_core.py tests/test_ai_env_loading.py tests/test_ai_features.py -q`)
```
====================== 31 passed, 305 warnings in 14.83s ======================
```

### Frontend Build (`npm run build`)
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
dist/assets/index-DHDzP9eu.js   917.11 kB │ gzip: 257.45 kB
✓ built in 3.44s
```

### Frontend Lint (`npm run lint`)
```
> frontend@0.0.0 lint
> eslint src --ext ts,tsx --report-unused-disable-directives --max-warnings 0
```
Exit code: 0 (clean, no warnings, no errors).
