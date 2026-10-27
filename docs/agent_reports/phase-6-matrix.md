# Phase 6 AI Capabilities Matrix & Verification Report

**Branch**: `feat/ai-multilang`  
**Date**: 2026-10-27  
**Status**: Completed (Zero GAP Rows, Every Cell Populated with Exact File Paths)

---

## 1. Traceability Matrix

| requirement | backend function | route | frontend component FILE PATH | test names | status |
|---|---|---|---|---|---|
| **Ingestion: Unsupported Language Structure Extraction**<br>Extract import dependencies and module structure from unsupported languages when AI is enabled & consent granted; grounded verification; labeled `ai_inferred`. | `infer_unsupported_language_edges` (`backend/ai/features.py`) invoked in `run_analysis` (`backend/app/services/analyzer_service.py`) | `POST /analyze`<br>`POST /ingest`<br>`POST /ingest/archive`<br>`POST /ingest/folder` | `frontend/src/pages/IngestionPage.tsx` | `test_unsupported_language_edge_inference`<br>`test_ai_on_off_identical_metrics` | **Verified** |
| **Topology: Community Naming & Layer Explanation**<br>Semantic clustering naming and architectural layer semantics grounded in Louvain community node IDs. | `summarize_topology` (`backend/ai/features.py`) | `POST /api/analysis/topology-summary` | `frontend/src/pages/GraphPage.tsx` | `test_topology_summary`<br>`test_all_11_features_deterministic_fallback` | **Verified** |
| **Metrics: "Explain This Metric"**<br>Plain-English explanation of instability, coupling, complexity, and health using computed numbers; deterministic fallback. | `explain_metric` (`backend/ai/features.py`) | `POST /api/analysis/explain-metric` | `frontend/src/pages/MetricsPage.tsx` | `test_metrics_explanation`<br>`test_all_11_features_deterministic_fallback` | **Verified** |
| **Diagnostics: Smell Context & Fix Outline**<br>Detailed consequence explanation, refactoring pattern, and step-by-step fix outline for detected code smells. | `explain_smell` (`backend/ai/features.py`) | `POST /api/diagnostics/explain-smell` | `frontend/src/components/DiagnosticsSmellPanel.tsx`<br>`frontend/src/components/SmellList.tsx` | `test_smells_explanation`<br>`test_all_11_features_deterministic_fallback` | **Verified** |
| **Security: Finding Enrichment**<br>Contextual explanation, false-positive estimation, and safe remediation snippet. Hard invariant: never suppresses, hides, or downgrades findings. | `enrich_security_finding` (`backend/ai/features.py`) | `POST /api/diagnostics/enrich-security` | `frontend/src/pages/SecurityPage.tsx` | `test_security_finding_enrichment`<br>`test_security_ai_never_changes_finding_count` | **Verified** |
| **Dashboard: Executive Status Briefing**<br>High-level architecture status summary derived strictly from computed health scores, grades, smells, and cycles. | `generate_dashboard_summary` (`backend/ai/features.py`) | `POST /api/analysis/dashboard-summary` | `frontend/src/pages/DashboardPage.tsx` | `test_dashboard_summary`<br>`test_all_11_features_deterministic_fallback` | **Verified** |
| **Reports: In-App & PDF Executive Narrative**<br>Plain-English narrative (what this means / why it matters / what to do) synchronized across in-app preview and downloadable PDF report. | `generate_report_narrative` (`backend/ai/features.py`) | `POST /api/reports/narrative`<br>`POST /reports/narrative` | `frontend/src/pages/ReportsPage.tsx` | `test_report_narrative`<br>`test_report_narrative_http_route` | **Verified** |
| **Refactor Engine: Sandbox Validation & Repair Loop**<br>AI drafts unified diff; validated on temporary clone (`git apply --check`, AST parse); up to 2 repair loops; never touches user repo; exportable patch. | `draft_and_validate_refactor` (`backend/ai/features.py`)<br>`export_patch` (`backend/app/api/refactor_routes.py`) | `POST /api/refactor/ai-proposal`<br>`GET /api/refactor/export-patch/{id}` | `frontend/src/pages/RefactorPage.tsx` | `test_refactor_engine_ai_proposal`<br>`test_refactor_validator_bad_patch_rejected`<br>`test_refactor_validator_syntax_error_rejected`<br>`test_refactor_repair_loop_success`<br>`test_refactor_repair_loop_exhaustion` | **Verified** |
| **Chat: "Ask ArchLens" Panel**<br>Deterministic fact retrieval (nodes, cycles, smells, hotspots); model answers strictly grounded in retrieved facts and must cite node IDs; invalid citations rejected. | `ask_archlens_chat` (`backend/ai/features.py`) | `POST /api/analysis/chat` | `frontend/src/components/AskArchLensPanel.tsx` | `test_ask_archlens_chat`<br>`test_all_11_features_deterministic_fallback` | **Verified** |
| **Search: Natural Language Search to Filter**<br>Query-to-filter translation (name, depends_on, min_complexity, max_instability, smell_type, language) with deterministic graph execution. | `natural_language_search` (`backend/ai/features.py`) | `POST /api/analysis/nl-search` | `frontend/src/pages/GraphPage.tsx` | `test_natural_language_search`<br>`test_all_11_features_deterministic_fallback` | **Verified** |
| **Admin: Telemetry & Usage Tracking**<br>Tracks total calls, input/output tokens, cost (USD), and per-feature breakdown. Sensitive keys are never returned or logged. | `get_ai_usage_statistics` (`backend/ai/features.py`)<br>`check_ai_status` (`backend/app/api/admin_routes.py`) | `GET /api/admin/ai/usage`<br>`GET /api/admin/ai/status`<br>`GET /admin/ai/status` | `frontend/src/pages/AdminAuditPage.tsx` | `test_admin_ai_usage_telemetry`<br>`test_admin_ai_status_endpoint` | **Verified** |

---

## 2. Hard Invariants Verification Summary

1. **Determinism (AI On vs Off)**:
   - Proved in `test_ai_on_off_identical_metrics`: health score, grade, node count, edge count, cycles, smells, and security findings are 100% identical whether AI is enabled or disabled.
2. **Security Invariant**:
   - Proved in `test_security_ai_never_changes_finding_count`: AI enrichment never removes, downgrades, or suppresses any CWE or vulnerability finding.
3. **Prompt Injection Safety**:
   - Proved in `test_prompt_injection_safety`: Adversarial text inside analyzed files cannot alter computed health scores, drop tables, or break schema validation.
4. **Refactor Safety**:
   - Temporary sandbox isolation guarantees user repositories are never written to or modified by AI.
   - `ARCHLENS_AI_RUN_TESTS` defaults to `false` preventing execution of untrusted code.
   - Two-attempt self-repair loop verifies clean patching and syntax before presenting verified proposals.
5. **Labels and Fallbacks**:
   - Every AI feature renders an explicit `AI-generated` label via `<AIBadge />` or `<AIBlock />`.
   - Every AI feature has deterministic fallback handling with tests verifying graceful degradation when AI providers are unavailable.
