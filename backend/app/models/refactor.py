"""Pydantic models for architectural smells and refactoring suggestions."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SmellSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SmellType(StrEnum):
    GOD_MODULE = "god_module"
    CIRCULAR_IMPORT = "circular_import"
    DEAD_CODE = "dead_code"
    DEEP_INHERITANCE = "deep_inheritance"
    LARGE_CLASS = "large_class"
    FEATURE_ENVY = "feature_envy"
    LONG_PARAMETER_LIST = "long_parameter_list"
    DUPLICATE_CODE = "duplicate_code"
    MISSING_TYPE_HINTS = "missing_type_hints"


class Smell(BaseModel):
    """A detected architectural smell."""

    type: SmellType
    file: str
    severity: SmellSeverity
    description: str
    line: int | None = None
    suggestion: str | None = None


class Suggestion(BaseModel):
    """An actionable refactoring suggestion."""

    title: str
    description: str
    affected_files: list[str] = Field(default_factory=list)
    effort: str = Field(default="medium", description="low | medium | high")
    impact: str = Field(default="medium", description="low | medium | high")
