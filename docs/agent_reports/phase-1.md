# Phase 1 Report: Fix the 4 Known Failures

## Summary of Fixes
1. **`backend/diagnostics/rules/base.py`**:
   - Extended `BaseRule.create_finding` with optional `cwe: str | None = None` and `owasp: str | None = None` overrides to allow specific rule checks (e.g. `eval`/`Function` as CWE-95) to override default rule-level taxonomy.
2. **`backend/diagnostics/rules/security/command_injection.py`**:
   - Fixed false positives in Python `subprocess.*` calls: literal list arguments (e.g., `subprocess.run(["ls", "-l"])`) without `shell=True` are clean and no longer falsely flagged.
   - Preserved true positives: `shell=True`, or first argument constructed dynamically via variable (`ast.Name`), concatenation (`ast.BinOp`), or f-string (`ast.JoinedStr`) are properly flagged.
   - Added `cwe="CWE-95: Improper Neutralization of Directives in Dynamically Evaluated Code ('Eval Injection')"` for `eval()` and `new Function()` in JavaScript analysis.
3. **Acceptance Test Fixtures**:
   - Created `backend/tests/fixtures/diagnostics/vulnerable_javascript.js` with exactly 7 findings covering all security rules (SQL concatenation, hardcoded secret, weak cryptography, insecure deserialization, command injection, path traversal, disabled TLS).
   - Created `backend/tests/fixtures/diagnostics/clean_javascript.js` with 0 findings.
4. **Acceptance & Unit Tests**:
   - Added `test_acceptance_javascript_fixtures` in `backend/tests/test_diagnostics/test_acceptance.py`.
   - Added unit tests in `backend/tests/test_diagnostics/test_security_rules.py` covering Python subprocess literal list clean behavior and dynamic arguments / `shell=True` detection.

## Gate Results
`..\venv\Scripts\python.exe -m pytest -q` executed from `backend/`:
```
350 passed, 692 warnings in 233.12s (0:03:53)
```
Status: PASS (0 failed, 350 passed)
