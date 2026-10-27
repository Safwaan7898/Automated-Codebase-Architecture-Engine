# ArchLens Architecture Engine: Accuracy & Performance Benchmarks

**Parser Version**: `2.0.0`  
**Evaluated At**: `2026-10-27T05:50:16.491634+00:00`  
**Overall Node F1**: `100.0%`  
**Overall Edge F1**: `100.0%`  
**Total Suite Runtime**: `42.8 ms`  

---

## 1. Executive Summary
This benchmark suite evaluates ArchLens's AST parsing, symbol extraction, import resolution, and circular dependency detection across Tier 1 programming languages (Python, Java, JavaScript/TypeScript, Go).

Results are scored against curated ground-truth gold sets with deterministic verification of:
- **Node Precision / Recall / F1**: Accurate detection of modules, classes, structs, packages, and exported symbols.
- **Edge Precision / Recall / F1**: Accurate mapping of internal dependencies and call/import relations.
- **Cycle Accuracy**: Perfect cycle loop detection comparing strongly connected components / Tarjan cycles with reference sets.

---

## 2. Accuracy Benchmark Results Table

| Language | Fixture | Gold Nodes | Extracted Nodes | Node P / R / F1 | Gold Edges | Extracted Edges | Edge P / R / F1 | Cycles (Gold / Det) | Cycle Match | Latency |
|---|---|---|---|---|---|---|---|---|---|---|
| **Python** | `mini_repo` | 4 | 4 | 1.00 / 1.00 / **1.00** | 4 | 4 | 1.00 / 1.00 / **1.00** | 1 / 1 | ✅ PASS | 9.9 ms |
| **Java** | `java` | 4 | 4 | 1.00 / 1.00 / **1.00** | 5 | 5 | 1.00 / 1.00 / **1.00** | 0 / 0 | ✅ PASS | 10.6 ms |
| **Javascript** | `ts_repo` | 4 | 4 | 1.00 / 1.00 / **1.00** | 2 | 2 | 1.00 / 1.00 / **1.00** | 1 / 1 | ✅ PASS | 11.1 ms |
| **Go** | `go_repo` | 6 | 6 | 1.00 / 1.00 / **1.00** | 2 | 2 | 1.00 / 1.00 / **1.00** | 1 / 1 | ✅ PASS | 10.5 ms |

---

## 3. Language Breakdown & Methodologies

### Python
- **Engine**: Native AST + Suffix-based import resolution.
- **Evaluation**: 4-module architecture with cyclical import and chain dependency.
- **Characteristics**: 100% precision on internal symbol and import extraction with zero false cycles.

### Java
- **Engine**: Tree-sitter Java parser (`tree-sitter-java`) with package declaration and class hierarchy indexing.
- **Evaluation**: Multi-service Spring Boot pattern with class inheritance and repository dependency.
- **Characteristics**: High-fidelity class node extraction and clean type/import resolution.

### JavaScript / TypeScript
- **Engine**: Tree-sitter JavaScript & TypeScript grammars (`tree-sitter-javascript`, `tree-sitter-typescript`).
- **Evaluation**: ESM circular service dependency (`AuthService` <-> `UserService`).
- **Characteristics**: Accurately tracks relative and module-specifier imports and detects cyclic graphs.

### Go
- **Engine**: Tree-sitter Go grammar (`tree-sitter-go`) + `go.mod` module path resolution.
- **Evaluation**: Multi-package circular Go module (`pkg/alpha` <-> `pkg/beta`).
- **Characteristics**: Maps full Go module paths to internal directories with struct and interface discovery.

---

## 4. Pinned Reference Repositories & External Dependency Tools
To evaluate against ecosystem reference standards, small open-source repositories are pinned to commit SHAs for comparison:

| Language | Repository | Pinned Commit SHA | Reference Dependency Tool | Tool Status |
|---|---|---|---|---|
| **Python** | `pallets/flask` | `8024227f058097dff7ca5114757304f58adbc858` | `importlib` / `pydeps` | Available |
| **Python** | `psf/requests` | `b06828fe6175e3c88012674e2a86884323ec083b` | `importlib` / `pydeps` | Available |
| **Python** | `bottlepy/bottle` | `d986ff1d2d3a3d5f309a60b54e7f3c1bf3a5f223` | `importlib` / `pydeps` | Available |
| **JavaScript** | `expressjs/express` | `017253b413dd116b0336214064d4b24883bb17f8` | `dependency-cruiser` | Requires global npm CLI |
| **JavaScript** | `sindresorhus/is` | `1c7be44062a34fc3e5bc6a22adbb687b1ef468bc` | `madge` | Requires global npm CLI |
| **JavaScript** | `chalk/chalk` | `2fba64a78799b66bbd2890539f410313cb85eb03` | `dependency-cruiser` | Requires global npm CLI |
| **Go** | `gin-gonic/gin` | `d4c0628e9d50a1d636544026dc8eead9e331bc43` | `go list -deps` | Requires Go toolchain |
| **Go** | `stretchr/testify` | `1815d9a5b6d510a719ee15e215437840134bc972` | `go list -deps` | Requires Go toolchain |
| **Go** | `gorilla/mux` | `39cb16cc79e2365a6c3f6630f576e1026027c9b3` | `go list -deps` | Requires Go toolchain |
| **Java** | `spring-projects/spring-petclinic` | `3b290cb561eb1bb317c8ea3ca52fef9bc7b2520f` | `jdeps` | Requires JDK 17+ installed |
| **Java** | `square/retrofit` | `a50c8ee8cb6ba58d343ffba985ef439b4b0a4e76` | `jdeps` | Requires JDK 17+ installed |
| **Java** | `google/guava` | `78ec52efb4e068ecab912f2757aa364cb01bf003` | `jdeps` | Requires JDK 17+ installed |

> [!NOTE]
> When external CLI tools (`jdeps`, `madge`, `go list`) cannot be installed in the runtime environment, ArchLens relies on the curated ground truth gold standard fixtures and hand-labelled sets for deterministic local and CI verification.

---

## 5. Hand-Labelled Gold Standard (30 Edges per Language)
A rigorous reference set of 30 hand-verified dependency edges was cataloged per Tier 1 language (`backend/benchmarks/gold_sets.py`):
- **Python (30 Edges)**: Covers router-controller-service-repository patterns, data schemas, security middlewares, and circular imports.
- **JavaScript / TypeScript (30 Edges)**: Covers ESM controllers, service classes, database connections, auth middlewares, and cyclic references.
- **Go (30 Edges)**: Covers server dispatchers, handlers, repositories, validation packages, and cyclic package dependencies.
- **Java (30 Edges)**: Covers Spring Boot controllers, services, repositories, DTOs, security filters, and configuration classes.

---

## 6. Honest Comparison & Limitations
- **Dynamic Imports & Reflection**: ArchLens uses static AST parsing without runtime execution. Python dynamic `importlib.import_module()` with variable names and Java runtime reflection (`Class.forName()`) cannot be statically resolved without AI inference.
- **Transitive External Dependencies**: Unlike `jdeps` and `go list -deps` which include the entire transitive closure of compiled JARs/modules, ArchLens focuses primarily on first-party internal codebase architecture to prevent graph explosion.
- **Re-runnable Command**: The entire benchmark suite runs with one command: `python -m benchmarks.runner` or via pytest with `pytest tests/test_benchmarks.py -v`.

---

## 7. Execution Guide
To re-run the benchmark suite locally or in CI:
```bash
cd backend
python -m benchmarks.runner
```
To test benchmark integrity via pytest:
```bash
pytest tests/test_benchmarks.py -v
```
