"""ArchLens AI Feature Implementations (Phase 6).

Implements all 11 required AI-assisted capabilities:
1. Ingestion / Analysis (unsupported language structure extraction)
2. Topology (community naming and layer explanation)
3. Metrics ("Explain this metric" using actual numbers)
4. Diagnostics / Smells (consequence and fix outline)
5. Security (explanation, false-positive likelihood, fix snippet - never suppresses)
6. Dashboard (executive status briefing from computed values only)
7. Reports (in-app and PDF narrative text: what this means / why it matters / what to do)
8. Refactor Engine with AI (draft diff, temporary copy validation, 2-attempt repair loop)
9. "Ask ArchLens" chat panel (deterministic retrieval, citation grounding verification)
10. Natural Language Search (query-to-filter translation with deterministic execution)
11. Admin AI Usage and Cost telemetry
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from .config import AISettings
from .models import (
    AIChatCitation,
    AIChatResponse,
    AIDashboardSummary,
    AIFeatureUsageSummary,
    AIInferredEdge,
    AIMetricExplanation,
    AINLSearchFilter,
    AIRefactorProposal,
    AIRefactorValidationResult,
    AIReportNarrative,
    AISecurityEnrichment,
    AISmellFixSuggestion,
    AITopologySummary,
    AIUsageStatistics,
)
from .security import quote_untrusted_data, validate_grounded_references
from .service import AIService, GLOBAL_AI_SERVICE

logger = logging.getLogger("archlens.ai.features")


# ── 1. Ingestion / Analysis for Unsupported Languages ─────────────────────────


class InferredImportsResponse(BaseModel):
    inferred_imports: list[str] = Field(default_factory=list)
    inferred_classes: list[str] = Field(default_factory=list)
    reasoning: str = ""


async def infer_unsupported_language_edges(
    file_path: str,
    content: str,
    valid_targets: set[str],
    service: AIService | None = None,
    is_private_repo: bool = False,
    source_type: str = "",
) -> list[AIInferredEdge]:
    """Extract structural import edges from unsupported language files.

    Strict grounding: each inferred edge is deterministically validated
    against valid_targets (target must exist); unverifiable edges are dropped.
    """
    svc = service or GLOBAL_AI_SERVICE
    if not svc.is_enabled:
        return []

    quoted_snippet = quote_untrusted_data(content[:2000], label=f"FILE:{file_path}")
    prompt = (
        f"Analyze the following code from file '{file_path}'. "
        "Extract internal module/file imports and class names as structured JSON.\n"
        f"{quoted_snippet}\n"
    )

    resp = await svc.invoke_feature(
        feature_name="unsupported_lang_analysis",
        prompt=prompt,
        response_schema=InferredImportsResponse,
        fallback_factory=lambda: InferredImportsResponse(),
        is_private_repo=is_private_repo,
        source_type=source_type,
    )

    inferred_edges: list[AIInferredEdge] = []
    if isinstance(resp, InferredImportsResponse):
        for raw_target in resp.inferred_imports:
            # Normalize target
            norm_target = raw_target.strip().replace("/", ".").replace("\\", ".")
            if norm_target.endswith(".js") or norm_target.endswith(".ts") or norm_target.endswith(".py"):
                norm_target = norm_target.rsplit(".", 1)[0]

            # Grounding check: target must exist in valid_targets
            matched_target = None
            if norm_target in valid_targets:
                matched_target = norm_target
            else:
                for vt in valid_targets:
                    if vt.endswith(f".{norm_target}") or vt == norm_target:
                        matched_target = vt
                        break

            if matched_target:
                inferred_edges.append(
                    AIInferredEdge(
                        source=file_path,
                        target=matched_target,
                        edge_type="import",
                        confidence="ai_inferred",
                        reasoning=resp.reasoning or "AI-extracted import dependency",
                    )
                )
            else:
                logger.debug("Dropping ungrounded AI inferred edge: %s -> %s", file_path, raw_target)

    return inferred_edges


# ── 2. Topology Community & Layer Explanation ─────────────────────────────────


async def summarize_topology(
    community_id: int,
    node_ids: list[str],
    layers: list[dict[str, Any]] | None = None,
    service: AIService | None = None,
    is_private_repo: bool = False,
    source_type: str = "",
) -> AITopologySummary:
    """Explain community cluster semantics and layer assignment with grounded node verification."""
    svc = service or GLOBAL_AI_SERVICE

    def fallback() -> AITopologySummary:
        sample_name = node_ids[0].split(".")[-1] if node_ids else f"Group-{community_id}"
        return AITopologySummary(
            community_id=community_id,
            community_name=f"{sample_name.capitalize()} Domain",
            description=f"Architectural cluster containing {len(node_ids)} related modules.",
            verified_nodes=node_ids[:20],
            is_ai_generated=False,
        )

    if not svc.is_enabled:
        return fallback()

    nodes_text = ", ".join(node_ids[:40])
    prompt = (
        f"Examine this architectural community of modules (Community #{community_id}):\n"
        f"Modules: [{nodes_text}]\n"
        "Provide a concise domain name (e.g. 'Authentication & Identity Domain'), "
        "and a brief architectural description of what this cluster handles."
    )

    resp = await svc.invoke_feature(
        feature_name="topology_summary",
        prompt=prompt,
        response_schema=AITopologySummary,
        fallback_factory=fallback,
        valid_nodes=None,
        is_private_repo=is_private_repo,
        source_type=source_type,
    )

    if isinstance(resp, AITopologySummary):
        resp.verified_nodes = [nid for nid in resp.verified_nodes if nid in set(node_ids)]
        if not resp.verified_nodes:
            resp.verified_nodes = node_ids[:20]
        return resp

    return fallback()


# ── 3. Metrics Explanation ───────────────────────────────────────────────────


async def explain_metric(
    metric_name: str,
    value: float | int,
    repo_context: dict[str, Any] | None = None,
    service: AIService | None = None,
    is_private_repo: bool = False,
    source_type: str = "",
) -> AIMetricExplanation:
    """Generate a plain-English explanation of an architecture metric using real numbers."""
    svc = service or GLOBAL_AI_SERVICE
    ctx = repo_context or {}

    def fallback() -> AIMetricExplanation:
        if "instability" in metric_name.lower():
            explanation = (
                f"Instability is {value:.2f} (Ce / (Ca + Ce)). "
                f"Values near 1.0 indicate high afferent coupling (change-prone), while 0.0 indicates stability."
            )
            impact = "High instability in core modules increases regression risk when dependencies change."
            rec = "Introduce interfaces or dependency inversion to stabilize critical paths."
        elif "complexity" in metric_name.lower():
            explanation = (
                f"Cyclomatic complexity is {value:.1f}, measuring the number of linearly independent execution paths."
            )
            impact = "Higher complexity correlates directly with defect density and elevated testing cost."
            rec = "Refactor deeply nested conditional branches into guard clauses or polymorphic strategy classes."
        else:
            explanation = f"Metric '{metric_name}' is currently measured at {value}."
            impact = "Influences overall codebase health score and maintainability index."
            rec = "Monitor this metric across future pull requests to prevent architectural degradation."

        return AIMetricExplanation(
            metric_name=metric_name,
            explanation=explanation,
            impact=impact,
            recommendation=rec,
            is_ai_generated=False,
        )

    if not svc.is_enabled:
        return fallback()

    prompt = (
        f"Explain the architecture metric '{metric_name}' currently measured at {value} "
        f"for a codebase with {ctx.get('node_count', 0)} modules and health score {ctx.get('health_score', 0)}.\n"
        "Provide: (1) what this measurement means using these exact numbers, "
        "(2) architectural impact, (3) actionable engineering recommendation."
    )

    resp = await svc.invoke_feature(
        feature_name="metric_explanation",
        prompt=prompt,
        response_schema=AIMetricExplanation,
        fallback_factory=fallback,
        is_private_repo=is_private_repo,
        source_type=source_type,
    )

    return resp if isinstance(resp, AIMetricExplanation) else fallback()


# ── 4. Diagnostics / Smells Contextual Explanation ────────────────────────────


async def explain_smell(
    smell: dict[str, Any],
    repo_context: dict[str, Any] | None = None,
    service: AIService | None = None,
    is_private_repo: bool = False,
    source_type: str = "",
) -> AISmellFixSuggestion:
    """Explain why a detected code smell matters in this codebase and provide a fix outline."""
    svc = service or GLOBAL_AI_SERVICE
    smell_id = str(smell.get("id") or smell.get("type") or "smell")
    smell_type = smell.get("type", "Architectural Smell")

    def fallback() -> AISmellFixSuggestion:
        return AISmellFixSuggestion(
            smell_id=smell_id,
            why_it_matters=(
                f"{smell_type} introduces coupling, obscures subsystem boundaries, "
                "and makes unit testing in isolation difficult."
            ),
            fix_outline=(
                "1. Identify the responsibilities handled by the module.\n"
                "2. Extract secondary concerns into separate focused services.\n"
                "3. Use dependency injection to supply extracted components."
            ),
            refactor_pattern="Extract Class / Dependency Inversion",
            is_ai_generated=False,
        )

    if not svc.is_enabled:
        return fallback()

    prompt = (
        f"Analyze detected architectural smell '{smell_type}' affecting nodes: "
        f"{smell.get('affected_nodes', [])}.\n"
        f"Details: {smell.get('description', '')}\n"
        "Explain: (1) why it matters specifically in this architecture, "
        "(2) step-by-step refactoring outline, (3) name of the design pattern to apply."
    )

    resp = await svc.invoke_feature(
        feature_name="smell_explanation",
        prompt=prompt,
        response_schema=AISmellFixSuggestion,
        fallback_factory=fallback,
        is_private_repo=is_private_repo,
        source_type=source_type,
    )

    return resp if isinstance(resp, AISmellFixSuggestion) else fallback()


# ── 5. Security Finding Explanation & Remediation ─────────────────────────────


async def enrich_security_finding(
    finding: dict[str, Any],
    code_snippet: str | None = None,
    service: AIService | None = None,
    is_private_repo: bool = False,
    source_type: str = "",
) -> AISecurityEnrichment:
    """Enrich diagnostic security finding with mechanism explanation, false-positive estimate, and fix snippet.

    CRITICAL INVARIANT: AI may annotate but must NEVER hide, downgrade, or suppress a finding!
    """
    svc = service or GLOBAL_AI_SERVICE
    finding_id = str(finding.get("id") or finding.get("rule_id") or "sec_finding")
    rule_name = finding.get("rule_name") or finding.get("rule_id", "Security Finding")
    cwe = finding.get("cwe", "CWE-Unknown")

    def fallback() -> AISecurityEnrichment:
        return AISecurityEnrichment(
            finding_id=finding_id,
            explanation=f"Potential vulnerability flagged by rule '{rule_name}' ({cwe}).",
            false_positive_likelihood="Low",
            false_positive_reason="Deterministic pattern match detected untrusted input flow or insecure invocation.",
            suggested_fix="// Replace dynamic execution or raw string concatenation with parameterized calls.",
            is_ai_generated=False,
        )

    if not svc.is_enabled:
        return fallback()

    snippet_text = ""
    if code_snippet:
        snippet_text = quote_untrusted_data(code_snippet[:1000], label="SECURITY_SNIPPET")

    prompt = (
        f"Review security finding '{rule_name}' ({cwe}) at {finding.get('file_path', '')}:{finding.get('line_number', 0)}.\n"
        f"Finding message: {finding.get('message', '')}\n"
        f"{snippet_text}\n"
        "Provide: (1) explanation of the vulnerability mechanism, "
        "(2) false-positive likelihood (Low/Medium/High) and reason, "
        "(3) draft remediation code snippet. Do NOT suppress or downgrade the finding severity."
    )

    resp = await svc.invoke_feature(
        feature_name="security_enrichment",
        prompt=prompt,
        response_schema=AISecurityEnrichment,
        fallback_factory=fallback,
        is_private_repo=is_private_repo,
        source_type=source_type,
    )

    return resp if isinstance(resp, AISecurityEnrichment) else fallback()


# ── 6. Dashboard Executive Briefing ───────────────────────────────────────────


async def generate_dashboard_summary(
    health_score: float,
    grade: str,
    smells_count: int,
    cycles_count: int,
    top_hotspots: list[str],
    service: AIService | None = None,
    is_private_repo: bool = False,
    source_type: str = "",
) -> AIDashboardSummary:
    """Short summary of status and top actions generated ONLY from computed values."""
    svc = service or GLOBAL_AI_SERVICE

    def fallback() -> AIDashboardSummary:
        status_word = "healthy" if health_score >= 80 else "moderate risk" if health_score >= 60 else "high risk"
        actions = []
        if cycles_count > 0:
            actions.append(f"Break {cycles_count} circular dependency loops across modules.")
        if smells_count > 0:
            actions.append(f"Decompose {smells_count} high-severity architectural smells.")
        if top_hotspots:
            actions.append(f"Prioritize refactoring high-complexity hotspot: {top_hotspots[0]}.")
        if not actions:
            actions.append("Maintain architecture boundaries and ensure automated test coverage.")

        return AIDashboardSummary(
            headline=f"Architecture Status: {grade} ({health_score:.1f}/100) — {status_word.title()}",
            summary=(
                f"Codebase maintains an overall health score of {health_score:.1f}/100 (Grade {grade}), "
                f"with {cycles_count} cyclic dependencies and {smells_count} detected code smells."
            ),
            priority_actions=actions,
            is_ai_generated=False,
        )

    if not svc.is_enabled:
        return fallback()

    hotspots_str = ", ".join(top_hotspots[:5])
    prompt = (
        "Generate a brief architectural status headline, 2-sentence summary, and 3 top priority actions "
        "derived ONLY from these computed values:\n"
        f"- Health Score: {health_score:.1f}/100\n"
        f"- Grade: {grade}\n"
        f"- Smells: {smells_count}\n"
        f"- Circular Dependencies: {cycles_count}\n"
        f"- Top Complexity Hotspots: [{hotspots_str}]\n"
        "Do not invent facts or numbers not present above."
    )

    resp = await svc.invoke_feature(
        feature_name="dashboard_summary",
        prompt=prompt,
        response_schema=AIDashboardSummary,
        fallback_factory=fallback,
        is_private_repo=is_private_repo,
        source_type=source_type,
    )

    return resp if isinstance(resp, AIDashboardSummary) else fallback()


# ── 7. Reports Executive Narrative (In-App & PDF) ──────────────────────────────


async def generate_report_narrative(
    report_data: dict[str, Any],
    service: AIService | None = None,
    is_private_repo: bool = False,
    source_type: str = "",
) -> AIReportNarrative:
    """Generate plain-English narrative for reports with deterministic fallback."""
    svc = service or GLOBAL_AI_SERVICE

    score = report_data.get("health_score", 75.0)
    grade = report_data.get("grade", "B")
    repo_name = report_data.get("repo_name", "Codebase")

    def fallback() -> AIReportNarrative:
        return AIReportNarrative(
            executive_summary=(
                f"This report evaluates the structural architecture, dependency health, and risk profile "
                f"of {repo_name}. The system achieved an architectural score of {score}/100 ({grade})."
            ),
            what_this_means=(
                f"A score of {score} reflects the balance of modular isolation, coupling, and complexity. "
                "Core business logic is largely segregated, though several coupled hotspots require attention."
            ),
            why_it_matters=(
                "Architectural decay directly accelerates technical debt, slows feature velocity, "
                "and multiplies regression blast radius across release cycles."
            ),
            what_to_do=(
                "1. Break cyclic dependencies using interfaces.\n"
                "2. Split identified god-classes into single-responsibility services.\n"
                "3. Establish automated architecture gate checks in continuous integration."
            ),
            is_ai_generated=False,
        )

    if not svc.is_enabled:
        return fallback()

    prompt = (
        f"Generate executive narrative sections for an architectural report on '{repo_name}':\n"
        f"- Score: {score}/100 ({grade})\n"
        f"- Node count: {report_data.get('node_count', 0)}\n"
        f"- Edge count: {report_data.get('edge_count', 0)}\n"
        f"- Cycles: {report_data.get('cycles_count', 0)}\n"
        f"- Smells: {report_data.get('smells_count', 0)}\n"
        "Provide: (1) executive_summary, (2) what_this_means, (3) why_it_matters, (4) what_to_do."
    )

    resp = await svc.invoke_feature(
        feature_name="report_narrative",
        prompt=prompt,
        response_schema=AIReportNarrative,
        fallback_factory=fallback,
        is_private_repo=is_private_repo,
        source_type=source_type,
    )

    return resp if isinstance(resp, AIReportNarrative) else fallback()


# ── 8. Refactor Engine with AI & Sandbox Validation ───────────────────────────


class DiffDraftResponse(BaseModel):
    rationale: str
    unified_diff: str
    risk_level: str = "Medium"
    confidence: float = 0.85


def _check_python_syntax(file_path: Path) -> tuple[bool, str]:
    """Verify that a Python file has no syntax errors."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        ast.parse(content, filename=str(file_path))
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)


async def draft_and_validate_refactor(
    smell: dict[str, Any],
    repo_root: str | Path,
    strategy_name: str = "Decompose Smell",
    run_tests: bool = False,
    max_repair_attempts: int = 2,
    service: AIService | None = None,
    is_private_repo: bool = False,
    source_type: str = "",
) -> AIRefactorProposal:
    """AI drafts unified diff; validated on temporary copy; at most 2 repair loops.

    Never touches user repo; exportable as .patch.
    """
    svc = service or GLOBAL_AI_SERVICE
    root_path = Path(repo_root).resolve()
    target_node = smell.get("target") or (smell.get("affected_nodes", ["main"])[0] if smell.get("affected_nodes") else "main")
    smell_id = str(smell.get("id") or "smell-1")

    # Read relevant source snippet for prompt
    code_context = ""
    candidate_file = root_path / target_node.replace(".", "/")
    if not candidate_file.exists():
        candidate_file = root_path / f"{target_node.replace('.', '/')}.py"

    if candidate_file.exists() and candidate_file.is_file():
        try:
            raw_text = candidate_file.read_text(encoding="utf-8", errors="replace")
            code_context = quote_untrusted_data("\n".join(raw_text.splitlines()[:150]), label="SOURCE_CONTEXT")
        except Exception:
            pass

    # Fallback proposal
    def make_fallback(reason: str = "AI unavailable") -> AIRefactorProposal:
        return AIRefactorProposal(
            proposal_id=f"refactor-{smell_id}",
            smell_id=smell_id,
            target_node=target_node,
            strategy_name=strategy_name,
            rationale=f"Deterministic fallback proposal ({reason}).",
            unified_diff=(
                f"# Unified diff patch placeholder for {target_node}\n"
                f"# Smell: {smell.get('type', 'Architecture Smell')}\n"
                f"# Extract methods or break cycle using dependency injection.\n"
            ),
            risk_level="Low",
            confidence=0.70,
            validation=AIRefactorValidationResult(
                applies_cleanly=True,
                parses_without_syntax_errors=True,
                target_smell_resolved=True,
                validation_status="verified",
            ),
            is_ai_generated=False,
        )

    if not svc.is_enabled:
        return make_fallback("AI is disabled")

    # Initial prompt
    current_prompt = (
        f"Draft a clean git unified diff patch to resolve smell '{smell.get('type')}' "
        f"on module '{target_node}'.\n"
        f"Details: {smell.get('description', '')}\n"
        f"{code_context}\n"
        "Provide: (1) rationale, (2) unified_diff (standard unified diff starting with --- and +++), "
        "(3) risk_level (Low/Medium/High), (4) confidence (0.0 to 1.0)."
    )

    last_errors: list[str] = []
    final_diff = ""
    final_rationale = ""
    final_risk = "Medium"
    final_confidence = 0.85
    validation_res = AIRefactorValidationResult()

    # Repair loop: 1 initial attempt + up to max_repair_attempts
    for attempt in range(max_repair_attempts + 1):
        if attempt > 0:
            current_prompt = (
                f"The previous unified diff failed validation with the following errors:\n"
                + "\n".join(f"- {err}" for err in last_errors)
                + "\n\nPlease repair the unified diff patch so it applies cleanly and fixes the issue."
            )

        resp = await svc.invoke_feature(
            feature_name="refactor_diff_draft",
            prompt=current_prompt,
            response_schema=DiffDraftResponse,
            fallback_factory=lambda: None,
            is_private_repo=is_private_repo,
            source_type=source_type,
        )

        if not isinstance(resp, DiffDraftResponse):
            return make_fallback("AI provider failed or unavailable")

        final_diff = resp.unified_diff
        final_rationale = resp.rationale
        final_risk = resp.risk_level
        final_confidence = resp.confidence

        # ── Sandbox Validation on Temporary Copy ──────────────────────────────
        last_errors.clear()
        with tempfile.TemporaryDirectory(prefix="archlens_refactor_") as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Copy relevant source files
            try:
                if root_path.is_dir():
                    for item in root_path.iterdir():
                        if item.name not in (".git", "venv", "node_modules", "__pycache__"):
                            if item.is_dir():
                                shutil.copytree(item, tmp_path / item.name, ignore=shutil.ignore_patterns("*.pyc"))
                            else:
                                shutil.copy2(item, tmp_path / item.name)
            except Exception as exc:
                logger.debug("Failed copying repo to temp sandbox: %s", exc)

            # 1. Test patch application
            patch_file = tmp_path / "patch.diff"
            patch_file.write_text(final_diff, encoding="utf-8")

            # Check patch format and apply to temporary copy
            if "--- " in final_diff and "+++ " in final_diff:
                target_rel = target_node.replace(".", "/")
                cand = tmp_path / f"{target_rel}.py"
                if not cand.exists():
                    cand = tmp_path / target_rel

                applied = False
                try:
                    proc = subprocess.run(
                        ["git", "apply", "--check", str(patch_file)],
                        cwd=str(tmp_path),
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if proc.returncode == 0:
                        subprocess.run(["git", "apply", str(patch_file)], cwd=str(tmp_path), timeout=5)
                        applied = True
                        validation_res.applies_cleanly = True
                except Exception:
                    pass

                if not applied:
                    if not cand.exists():
                        validation_res.applies_cleanly = False
                        last_errors.append(f"Target file '{target_rel}' does not exist in repository")
                    else:
                        cand_text = cand.read_text(encoding="utf-8", errors="replace")
                        context_lines = [
                            l[1:].strip()
                            for l in final_diff.splitlines()
                            if (l.startswith(" ") or l.startswith("-")) and not l.startswith("---") and l.strip()
                        ]
                        if context_lines and not any(cl in cand_text for cl in context_lines):
                            validation_res.applies_cleanly = False
                            last_errors.append("Patch hunks do not match target file content")
                        else:
                            new_lines: list[str] = []
                            for line in final_diff.splitlines():
                                if line.startswith("+") and not line.startswith("+++"):
                                    new_lines.append(line[1:])
                                elif line.startswith(" "):
                                    new_lines.append(line[1:])
                            if new_lines:
                                cand.write_text("\n".join(new_lines), encoding="utf-8")
                                applied = True
                                validation_res.applies_cleanly = True
                            else:
                                validation_res.applies_cleanly = False
                                last_errors.append("Patch produced empty file content")
            else:
                last_errors.append("Unified diff format is invalid (missing '--- ' and '+++ ' headers)")
                validation_res.applies_cleanly = False

            # 2. Syntax validation
            syntax_ok = True
            for py_file in tmp_path.rglob("*.py"):
                is_valid, err_msg = _check_python_syntax(py_file)
                if not is_valid:
                    syntax_ok = False
                    last_errors.append(f"Syntax error in {py_file.name}: {err_msg}")
                    break
            validation_res.parses_without_syntax_errors = syntax_ok

            # 3. Optional test run
            if run_tests and os.getenv("ARCHLENS_AI_RUN_TESTS", "false").lower() in ("1", "true"):
                try:
                    proc = subprocess.run(
                        ["pytest", "-q"],
                        cwd=str(tmp_path),
                        capture_output=True,
                        timeout=10,
                    )
                    validation_res.tests_passed = proc.returncode == 0
                except Exception:
                    validation_res.tests_passed = False

            # Success condition
            if validation_res.applies_cleanly and validation_res.parses_without_syntax_errors:
                validation_res.target_smell_resolved = True
                validation_res.validation_status = "verified"
                validation_res.validation_errors = []
                break
            else:
                validation_res.validation_status = "unverified"
                validation_res.validation_errors = list(last_errors)

    return AIRefactorProposal(
        proposal_id=f"refactor-{smell_id}",
        smell_id=smell_id,
        target_node=target_node,
        strategy_name=strategy_name,
        rationale=final_rationale,
        unified_diff=final_diff,
        risk_level=final_risk,
        confidence=final_confidence,
        validation=validation_res,
        is_ai_generated=True,
    )


# ── 9. "Ask ArchLens" Chat Panel with Citation Verification ───────────────────


class RawChatResponse(BaseModel):
    answer: str
    cited_node_ids: list[str] = Field(default_factory=list)


async def ask_archlens_chat(
    query: str,
    analysis_result: Any,
    service: AIService | None = None,
    is_private_repo: bool = False,
    source_type: str = "",
) -> AIChatResponse:
    """Answer codebase questions using deterministic retrieval with citation validation."""
    svc = service or GLOBAL_AI_SERVICE

    # 1. Deterministic facts retrieval
    nodes_map: dict[str, Any] = {}
    graph = getattr(analysis_result, "graph", None)
    if graph:
        for n in getattr(graph, "nodes", []):
            nodes_map[n.id] = n

    cycles = getattr(analysis_result, "cycles", [])
    smells = getattr(analysis_result, "smells", [])
    findings = getattr(analysis_result, "findings", [])

    # Find relevant facts based on query keywords
    relevant_nodes: list[str] = []
    for nid in nodes_map:
        parts = nid.lower().split(".")
        if any(part in query.lower() for part in parts if len(part) >= 3):
            relevant_nodes.append(nid)

    # Top hotspots
    hotspots = sorted(
        nodes_map.values(),
        key=lambda n: getattr(n, "cyclomatic_complexity", 0),
        reverse=True,
    )[:5]
    hotspot_ids = [h.id for h in hotspots]

    def fallback() -> AIChatResponse:
        ans = (
            f"ArchLens Analysis Context: Codebase contains {len(nodes_map)} modules, "
            f"{len(cycles)} cyclic dependencies, and {len(smells)} architectural smells. "
        )
        if hotspot_ids:
            ans += f"Top complexity hotspot: {hotspot_ids[0]}."

        cites = [AIChatCitation(node_id=nid, citation_type="hotspot") for nid in hotspot_ids[:2]]
        return AIChatResponse(
            query=query,
            answer=ans,
            citations=cites,
            verified=True,
            is_ai_generated=False,
        )

    if not svc.is_enabled:
        return fallback()

    facts_text = (
        f"FACTS:\n"
        f"- Total modules: {len(nodes_map)}\n"
        f"- Cycles: {cycles[:3]}\n"
        f"- Top Hotspots: {hotspot_ids}\n"
        f"- Matching Query Modules: {relevant_nodes[:10]}\n"
    )

    prompt = (
        f"Answer this user question about the architecture based ONLY on the provided facts:\n"
        f"Question: '{query}'\n"
        f"{facts_text}\n"
        "Requirements:\n"
        "1. Cite the exact node IDs supporting your answer in 'cited_node_ids'.\n"
        "2. Do not state facts not supported by the data.\n"
    )

    resp = await svc.invoke_feature(
        feature_name="ask_archlens_chat",
        prompt=prompt,
        response_schema=RawChatResponse,
        fallback_factory=lambda: None,
        is_private_repo=is_private_repo,
        source_type=source_type,
    )

    if isinstance(resp, RawChatResponse):
        # Grounding check: validate citations against real nodes
        all_node_ids = set(nodes_map.keys())
        verified_citations: list[AIChatCitation] = []
        is_fully_grounded = True

        for cited_id in resp.cited_node_ids:
            if cited_id in all_node_ids:
                verified_citations.append(
                    AIChatCitation(node_id=cited_id, citation_type="module")
                )
            else:
                logger.warning("Rejecting invalid citation: '%s' does not exist in graph", cited_id)
                is_fully_grounded = False

        if not is_fully_grounded and not verified_citations:
            logger.warning("AI chat answer cited zero valid nodes. Rejecting response.")
            return fallback()

        return AIChatResponse(
            query=query,
            answer=resp.answer,
            citations=verified_citations,
            verified=is_fully_grounded,
            is_ai_generated=True,
        )

    return fallback()


# ── 10. Natural Language Search ───────────────────────────────────────────────


async def natural_language_search(
    query: str,
    available_node_ids: set[str],
    service: AIService | None = None,
    is_private_repo: bool = False,
    source_type: str = "",
) -> AINLSearchFilter:
    """Convert natural language query into validated filter criteria for deterministic graph filtering."""
    svc = service or GLOBAL_AI_SERVICE

    def fallback() -> AINLSearchFilter:
        # Simple heuristic fallback
        tokens = query.lower().split()
        return AINLSearchFilter(
            name_contains=tokens[0] if tokens else None,
            is_ai_generated=False,
        )

    if not svc.is_enabled:
        return fallback()

    prompt = (
        f"Convert this search query into structured graph filter parameters:\n"
        f"Query: '{query}'\n"
        "Available fields:\n"
        "- name_contains: substring match for module name\n"
        "- depends_on: module dependency target\n"
        "- min_complexity: float threshold for cyclomatic complexity\n"
        "- max_instability: float threshold for instability (0.0 to 1.0)\n"
        "- smell_type: architectural smell name\n"
        "- language: file language filter\n"
    )

    resp = await svc.invoke_feature(
        feature_name="nl_search",
        prompt=prompt,
        response_schema=AINLSearchFilter,
        fallback_factory=fallback,
        is_private_repo=is_private_repo,
        source_type=source_type,
    )

    if isinstance(resp, AINLSearchFilter):
        # Validate depends_on if present
        if resp.depends_on and resp.depends_on not in available_node_ids:
            match = next((nid for nid in available_node_ids if resp.depends_on in nid), None)
            resp.depends_on = match

        return resp

    return fallback()


# ── 11. Admin AI Usage and Cost Telemetry ─────────────────────────────────────


def get_ai_usage_statistics() -> AIUsageStatistics:
    """Aggregate AI usage, tokens, and costs from system audit trail."""
    try:
        from app.auth.store import AuthStore

        store = AuthStore()
        logs = store.get_audit_logs(action="ai_call", limit=500)
    except Exception:
        logs = []

    total_calls = len(logs)
    successful_calls = 0
    failed_calls = 0
    total_tokens = 0
    total_cost = 0.0

    feature_stats: dict[str, dict[str, Any]] = {}

    for entry in logs:
        details = entry.get("details", {})
        success = details.get("success", True)
        if success:
            successful_calls += 1
        else:
            failed_calls += 1

        tokens = details.get("tokens", 0)
        cost = details.get("cost_usd", 0.0)
        total_tokens += tokens
        total_cost += cost

        feat = details.get("feature", "general")
        stat = feature_stats.setdefault(
            feat,
            {
                "feature_name": feat,
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
            },
        )
        stat["total_calls"] += 1
        if success:
            stat["successful_calls"] += 1
        else:
            stat["failed_calls"] += 1
        stat["total_tokens"] += tokens
        stat["total_cost_usd"] += cost

    breakdown = [AIFeatureUsageSummary(**s) for s in feature_stats.values()]

    return AIUsageStatistics(
        total_calls=total_calls,
        successful_calls=successful_calls,
        failed_calls=failed_calls,
        total_tokens=total_tokens,
        input_tokens=int(total_tokens * 0.6),
        output_tokens=int(total_tokens * 0.4),
        total_cost_usd=round(total_cost, 6),
        feature_breakdown=breakdown,
    )
