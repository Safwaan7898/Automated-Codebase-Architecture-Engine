"""Vulnerable dependency rule leveraging OSV.dev data."""

from __future__ import annotations

from typing import Any

from diagnostics.models import Finding, RuleCategory, Severity
from diagnostics.rules.base import DependencyRule


class VulnerableDependencyRule(DependencyRule):
    """Flags dependencies with known CVEs/advisories from OSV.dev."""

    id = "DEP-VULNERABLE-PACKAGE"
    name = "Known Vulnerability in Dependency"
    severity = Severity.HIGH
    cwe = "CWE-1395: Dependency on Vulnerable Third-Party Component"
    owasp = "A06:2021-Vulnerable and Outdated Components"
    category = RuleCategory.DEPENDENCY
    remediation = "Upgrade the dependency to a secure patched release."

    def check_dependency(
        self,
        package_name: str,
        version: str,
        ecosystem: str,
        manifest_path: str,
        cve_data: list[dict[str, Any]],
    ) -> list[Finding]:
        findings: list[Finding] = []

        for vuln in cve_data:
            vuln_id = vuln.get("id", "UNKNOWN-VULN")
            aliases = vuln.get("aliases", [])
            cve_id = next((a for a in aliases if a.startswith("CVE-")), None)
            display_id = cve_id or vuln_id
            summary = vuln.get("summary") or vuln.get("details", "")[:120]

            # Determine severity from database_specific or CVSS
            sev = Severity.HIGH
            db_sev = vuln.get("database_specific", {}).get("severity", "").upper()
            if db_sev == "CRITICAL":
                sev = Severity.CRITICAL
            elif db_sev == "LOW":
                sev = Severity.LOW
            elif db_sev == "MODERATE" or db_sev == "MEDIUM":
                sev = Severity.MEDIUM

            # Check CVSS scores if present
            for s_entry in vuln.get("severity", []):
                score_str = s_entry.get("score", "")
                if "CVSS:3" in score_str:
                    # e.g. CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
                    if "/C:H/I:H/A:H" in score_str or "CRITICAL" in score_str:
                        sev = Severity.CRITICAL

            msg = f"Dependency '{package_name}'@{version} has known vulnerability {display_id}: {summary}"

            findings.append(
                Finding(
                    rule_id=self.id,
                    rule_name=self.name,
                    severity=sev,
                    category=self.category,
                    message=msg,
                    remediation=f"Upgrade '{package_name}' beyond version {version} to resolve {display_id}.",
                    cwe=self.cwe,
                    owasp=self.owasp,
                    file_path=manifest_path,
                    node_id=f"ext:{package_name}",
                    metadata={
                        "package": package_name,
                        "version": version,
                        "ecosystem": ecosystem,
                        "vuln_id": vuln_id,
                        "aliases": aliases,
                    },
                )
            )

        return findings
