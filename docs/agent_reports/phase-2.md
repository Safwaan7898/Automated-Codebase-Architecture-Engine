# Phase 2 Report: Baseline Verification

## 1. Backend Test Gate
Command: `..\venv\Scripts\python.exe -m pytest -q` (executed in `backend/`)
```
350 passed, 692 warnings in 233.12s (0:03:53)
```
Status: PASS (350 passed, 0 failed)

## 2. Frontend Build Gate
Command: `npm run build` (executed in `frontend/`)
```
> frontend@0.0.0 build
> tsc -b && vite build

vite v8.3.2 building client environment for production...
transforming...
✓ 2411 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   1.91 kB │ gzip:   0.93 kB
dist/assets/index-Dm984GU0.css   94.59 kB │ gzip:  15.73 kB
dist/assets/index-KAFrKKwt.js   913.73 kB │ gzip: 256.80 kB
✓ built in 4.38s
```
Status: PASS (Exit code 0)

## 3. Frontend Lint Gate
Command: `npm run lint` (executed in `frontend/`)
```
> frontend@0.0.0 lint
> eslint src --ext ts,tsx --report-unused-disable-directives --max-warnings 0
```
Status: PASS (Exit code 0, 0 warnings, 0 errors)

## 4. Parser Version & Guard Check
- `backend/tests/test_parsers/test_parser_version_guard.py`: Passed.
- Current `PARSER_VERSION`: `1.4.0`.

## 5. Baseline Git Tag
- Commit: `a2abeba fix(security): resolve command injection false positives, cwe-95 overrides, and js security fixtures`
- Tag: `ai-baseline`
```
$ git tag -l
ai-baseline
pre-redesign
```
