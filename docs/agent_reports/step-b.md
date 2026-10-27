# Step B Report: Fix .env Loading

## Summary
- **Unified Settings Mechanism**: Absolute path resolution derived from package location `(Path(__file__).resolve().parent.parent / ".env")` across `backend/ai/config.py` and `backend/app/core/config.py`.
- **Environment Overrides**: Process environment variables take strict precedence over `.env` file values.
- **Provider Catalog & Model Validation**:
  - `python -m ai.check` prints loaded `.env` path, variable names, keys present (count only, never values), effective model per provider, and warnings for built-in defaults or `-latest` aliases.
  - Added `--list-models` to list chat-capable models and mark the configured one.
  - Replaced outdated built-in default models with verified models:
    - Groq: `qwen/qwen3.8-27b`
    - NVIDIA: `meta/muse-glimmer-30b`
    - Gemini: `gemini-2.5-flash`
  - Real 1-token chat request verification per active provider.
- **Offline Tests**: Added `backend/tests/test_ai_env_loading.py` (loading from multiple working directories, environment variable overrides, secret redaction in output/logs/exceptions).

## Gate Outputs

### Backend Tests (`pytest -q`)
```
================ 387 passed, 873 warnings in 306.46s (0:05:06) ================
```

### Targeted Env Loading Tests (`pytest backend/tests/test_ai_env_loading.py -q`)
```
======================= 4 passed, 143 warnings in 0.26s =======================
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
✓ built in 5.20s
```

### Frontend Lint (`npm run lint`)
```
> frontend@0.0.0 lint
> eslint src --ext ts,tsx --report-unused-disable-directives --max-warnings 0
```
Exit code: 0 (clean, no warnings, no errors).
