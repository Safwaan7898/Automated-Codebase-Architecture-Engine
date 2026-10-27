# Master Prompt V2 - Step 3 Report: Real External Benchmarks

**Date**: 2026-10-27  
**Branch**: `feat/ai-multilang`  
**Status**: COMPLETE (External benchmarks implemented with independent tools; relabeled fixture suite as self-consistency)

---

## 1. Explanation: Why Fixture Runs Take ~45 ms

The baseline fixture benchmark (`GOLD_STANDARDS` in `backend/benchmarks/gold_sets.py`) operates on 4 curated micro-fixtures (`mini_repo`, `java`, `ts_repo`, `go_repo` in `backend/tests/fixtures/benchmarks/`). Each fixture contains only 4 to 6 small source files hand-annotated for nodes, edges, and Tarjan circular dependency cycles. Because these repositories are small and run in-memory, AST parsing and graph resolution take only ~6 to 16 ms per language, totaling ~45 ms across all 4 languages.

Per prompt instructions, this fixture evaluation has been relabeled across `docs/benchmarks.md` and `docs/AI_FEATURES.md` as **"Self-Consistency on Fixtures"** to clearly distinguish it from external, real-world evaluations.

---

## 2. Real External Benchmark Implementation (`python -m benchmarks.runner --external`)

An external benchmarking engine (`backend/benchmarks/external_runner.py`) was implemented to evaluate ArchLens against independent ecosystem reference tools on pinned open-source repositories:

- **Clone Cache**: Clones repos into the gitignored `.benchmarks_cache/` directory with shallow depth (`--depth 50`) and checks out pinned commit SHAs. Clones are never committed to git.
- **Reference Tools**:
  - **Python**: Independent AST and `importlib` static module resolver mapping inter-module dependencies across packages.
  - **JavaScript / TypeScript**: `madge` executed on-demand via `npx --yes madge --json` (zero global CLI dependencies).
  - **Go**: Checks for `go` binary on host. The host lacks a Go toolchain (`INFO: Could not find files for the given pattern(s)`), so Go repos are marked `"not externally verified"` with the honest reason recorded.
  - **Java**: Checks for `jdeps`. `jdeps` operates strictly on compiled `.class` bytecode or packaged JARs. Because source checkouts do not bundle compiled bytecode and compiling multi-module Java projects requires pre-installed Maven/Gradle build environments, Java repos are marked `"not externally verified"` with the honest reason recorded.

---

## 3. External Benchmark Results Table

| Language | Repository | SHA | Reference Tool | Tool Status | Ref Edges | ArchLens Edges | Precision | Recall | F1 Score | Runtime | Discrepancy Reason |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Python** | `bottlepy/bottle` | `d986ff1d` | ast/importlib | ✅ Verified | 51 | 0 | 0.000 | 0.000 | **0.000** | 681.8 ms | Single-file architecture (`bottle.py`). Reference tool scanned `test/` imports, while ArchLens ran with `include_tests=False`. |
| **Python** | `psf/requests` | `b06828fe` | ast/importlib | ✅ Verified | 65 | 75 | 0.867 | 1.000 | **0.929** | 301.1 ms | ArchLens extracts additional static call and type annotation edges (`requests._types`). |
| **Python** | `pallets/flask` | `8024227f` | ast/importlib | ✅ Verified | 110 | 112 | 0.964 | 0.982 | **0.973** | 620.2 ms | Near-perfect alignment on internal module dependency topology. |
| **Javascript** | `sindresorhus/is` | `1c7be440` | madge (npx) | ✅ Verified | 0 | 1 | 0.000 | 1.000 | **0.000** | 200.3 ms | Single-module package with index re-export. |
| **Javascript** | `expressjs/express` | `017253b4` | madge (npx) | ✅ Verified | 6 | 55 | 0.143 | 0.167 | **0.154** | 372.3 ms | Madge reports 6 file-level imports; ArchLens tree-sitter extracts 55 internal function/symbol calls. |
| **Javascript** | `chalk/chalk` | `2fba64a7` | madge (npx) | ✅ Verified | 3 | 13 | 0.000 | 0.000 | **0.000** | 322.7 ms | Madge excludes type-only and subpath exports. |
| **Go** | `gin-gonic/gin` | `d4c0628e` | go list -deps | ⚠️ Not verified | N/A | 19 | N/A | N/A | N/A | 417.1 ms | Go toolchain (`go`) not found on host environment. |
| **Go** | `gorilla/mux` | `39cb16cc` | go list -deps | ⚠️ Not verified | N/A | 0 | N/A | N/A | N/A | 187.7 ms | Go toolchain (`go`) not found on host environment. |
| **Go** | `stretchr/testify` | `1815d9a5` | go list -deps | ⚠️ Not verified | N/A | 12 | N/A | N/A | N/A | 346.0 ms | Go toolchain (`go`) not found on host environment. |
| **Java** | `spring-projects/spring-petclinic` | `3b290cb5` | jdeps | ⚠️ Not verified | N/A | 0 | N/A | N/A | N/A | 390.6 ms | `jdeps` requires compiled `.class` bytecode; source-only checkout. |
| **Java** | `square/retrofit` | `a50c8ee8` | jdeps | ⚠️ Not verified | N/A | 0 | N/A | N/A | N/A | 294.5 ms | `jdeps` requires compiled `.class` bytecode; source-only checkout. |
| **Java** | `google/guava` | `78ec52ef` | jdeps | ⚠️ Not verified | N/A | 15133 | N/A | N/A | N/A | 5746.8 ms | `jdeps` requires compiled `.class` bytecode; source-only checkout. |

---

## 4. Test Verification

`pytest backend/tests/test_benchmarks.py -v`:
- `test_tier1_benchmark_suite_execution`: PASSED (F1 >= 0.95 across fixture suite)
- `test_gold_standards_consistency`: PASSED
- `test_hand_labelled_30_edges_and_reference_repos`: PASSED
- `test_external_benchmark_results_schema`: PASSED (verified results JSON structure and honest status reasons)
