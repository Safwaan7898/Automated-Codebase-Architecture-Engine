"""Diagnostic rules package."""

from __future__ import annotations

from diagnostics.rules.base import BaseRule, DependencyRule, DesignSmellRule, SecurityRule
from diagnostics.rules.security import ALL_SECURITY_RULES
from diagnostics.rules.smells import ALL_DESIGN_SMELL_RULES

ALL_RULES = ALL_SECURITY_RULES + ALL_DESIGN_SMELL_RULES

__all__ = [
    "ALL_DESIGN_SMELL_RULES",
    "ALL_RULES",
    "ALL_SECURITY_RULES",
    "BaseRule",
    "DependencyRule",
    "DesignSmellRule",
    "SecurityRule",
]
