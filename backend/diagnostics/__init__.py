"""ArchLens Diagnostics & Rule Engine package."""

from __future__ import annotations

from diagnostics.dependencies.osv_client import OSVClient, default_osv_client
from diagnostics.dependencies.parsers import (
    Dependency,
    parse_build_gradle,
    parse_pom_xml,
    parse_requirements_txt,
)
from diagnostics.dependencies.rules import VulnerableDependencyRule
from diagnostics.engine import (
    DiagnosticsEngine,
    RuleRegistry,
    default_diagnostics_engine,
)
from diagnostics.models import (
    DiagnosticsReport,
    Finding,
    NodeRiskScore,
    RuleCategory,
    Severity,
)
from diagnostics.rules.base import (
    BaseRule,
    DependencyRule,
    DesignSmellRule,
    SecurityRule,
)
from diagnostics.rules.security import (
    ALL_SECURITY_RULES,
    CommandInjectionRule,
    DisabledTlsVerificationRule,
    HardcodedSecretsRule,
    InsecureDeserializationRule,
    PathTraversalRule,
    SqlConcatenationRule,
    WeakCryptoRule,
)
from diagnostics.rules.smells import (
    ALL_DESIGN_SMELL_RULES,
    CyclicDependencyRule,
    DeadCodeRule,
    DeepInheritanceRule,
    FeatureEnvyRule,
    GodClassRule,
    HighCouplingRule,
    LongMethodRule,
)
from diagnostics.scoring import NodeRiskScorer, default_risk_scorer

__all__ = [
    "ALL_DESIGN_SMELL_RULES",
    "ALL_SECURITY_RULES",
    "BaseRule",
    "CommandInjectionRule",
    "CyclicDependencyRule",
    "DeadCodeRule",
    "DeepInheritanceRule",
    "Dependency",
    "DependencyRule",
    "DesignSmellRule",
    "DiagnosticsEngine",
    "DiagnosticsReport",
    "DisabledTlsVerificationRule",
    "FeatureEnvyRule",
    "Finding",
    "GodClassRule",
    "HardcodedSecretsRule",
    "HighCouplingRule",
    "InsecureDeserializationRule",
    "LongMethodRule",
    "NodeRiskScore",
    "NodeRiskScorer",
    "OSVClient",
    "PathTraversalRule",
    "RuleCategory",
    "RuleRegistry",
    "SecurityRule",
    "Severity",
    "SqlConcatenationRule",
    "VulnerableDependencyRule",
    "WeakCryptoRule",
    "default_diagnostics_engine",
    "default_osv_client",
    "default_risk_scorer",
    "parse_build_gradle",
    "parse_pom_xml",
    "parse_requirements_txt",
]
