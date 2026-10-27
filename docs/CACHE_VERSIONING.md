# Cache and Parser Versioning Policy

## Overview
ArchLens relies on deterministic cache keys for deduplication and analysis reproducibility. The cache key is composed of:
```
cache_key = f"{source_fingerprint}:{parser_version}:{settings_hash}"
```
Where:
- `source_fingerprint`: Deterministic SHA-256 hash across sorted relative POSIX paths and file content hashes (with CRLF normalized).
- `parser_version`: Current semantic version of the parsing and analysis engine (`PARSER_VERSION = "1.1.0"`).
- `settings_hash`: Deterministic SHA-256 hash of analysis configuration parameters and random seeds.

---

## When to Bump `PARSER_VERSION`

Any code change that alters how codebases are parsed, indexed, resolved, scored, or analyzed **requires a bump of `PARSER_VERSION`** to prevent stale or incompatible cache hits.

Specifically, a bump is mandatory when modifying:

1. **AST Parsing & Node Extraction**:
   - Adding or removing supported node types (e.g., classes, functions, modules, interfaces, packages).
   - Changing how module IDs, class identifiers, or node labels are derived from file paths.
   - Adjusting lines-of-code (LOC) or McCabe cyclomatic complexity calculation.

2. **Dependency & Import Resolution**:
   - Modifying import edge resolution rules (absolute imports, relative imports, `__init__.py` handling).
   - Changing suffix indexing, longest-match semantics, or tie-breaking / ambiguity resolution.
   - Classifying external dependencies (stdlib vs third-party vs unresolved).

3. **Graph Algorithms & Health Scoring**:
   - Modifying community detection (Louvain clustering), PageRank, Betweenness centrality, or Tarjan SCC cycle detection.
   - Adjusting architectural smell detection rules or severity weights (god module, circular import, missing hints).
   - Altering health scoring formulas or penalty sub-scores.

4. **Source Fingerprinting & Provenance**:
   - Modifying the ignore/skip directory set (`DEFAULT_SKIP_DIRS`).
   - Changing line normalization, path encoding, or file hashing logic.

---

## Automated Version Bump Guard

ArchLens includes an automated regression test in `backend/tests/test_parsers/test_parser_version_guard.py`.
This test calculates a cryptographic hash over the analyzer core source files (`base.py`, `python_analyzer.py`, `java_analyzer.py`, `fingerprint.py`).

If any analyzer file is modified without bumping `PARSER_VERSION` and updating the recorded hash contract, the test suite will fail during CI/CD.
