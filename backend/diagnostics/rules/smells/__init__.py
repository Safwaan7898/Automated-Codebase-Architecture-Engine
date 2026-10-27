"""Design smell rules suite."""

from __future__ import annotations

from diagnostics.rules.smells.cyclic_dependency import CyclicDependencyRule
from diagnostics.rules.smells.dead_code import DeadCodeRule
from diagnostics.rules.smells.deep_inheritance import DeepInheritanceRule
from diagnostics.rules.smells.feature_envy import FeatureEnvyRule
from diagnostics.rules.smells.god_class import GodClassRule
from diagnostics.rules.smells.high_coupling import HighCouplingRule
from diagnostics.rules.smells.long_method import LongMethodRule

ALL_DESIGN_SMELL_RULES = [
    GodClassRule,
    CyclicDependencyRule,
    HighCouplingRule,
    LongMethodRule,
    DeepInheritanceRule,
    FeatureEnvyRule,
    DeadCodeRule,
]

__all__ = [
    "ALL_DESIGN_SMELL_RULES",
    "CyclicDependencyRule",
    "DeadCodeRule",
    "DeepInheritanceRule",
    "FeatureEnvyRule",
    "GodClassRule",
    "HighCouplingRule",
    "LongMethodRule",
]
