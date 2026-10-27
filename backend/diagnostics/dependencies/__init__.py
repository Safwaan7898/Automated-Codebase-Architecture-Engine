"""Dependency analysis and OSV.dev integration package."""

from __future__ import annotations

from diagnostics.dependencies.osv_client import OSVClient, default_osv_client
from diagnostics.dependencies.parsers import (
    Dependency,
    parse_build_gradle,
    parse_pom_xml,
    parse_requirements_txt,
)
from diagnostics.dependencies.rules import VulnerableDependencyRule

__all__ = [
    "Dependency",
    "OSVClient",
    "VulnerableDependencyRule",
    "default_osv_client",
    "parse_build_gradle",
    "parse_pom_xml",
    "parse_requirements_txt",
]
