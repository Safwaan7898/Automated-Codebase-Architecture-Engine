"""Acceptance tests verifying seeded vulnerable fixtures are detected with 0 false positives on clean fixtures."""

from pathlib import Path

from diagnostics.engine import default_diagnostics_engine

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "diagnostics"

EXPECTED_SECURITY_RULES = {
    "SEC-SQL-CONCAT",
    "SEC-HARDCODED-SECRET",
    "SEC-WEAK-CRYPTO",
    "SEC-INSECURE-DESERIALIZATION",
    "SEC-COMMAND-INJECTION",
    "SEC-PATH-TRAVERSAL",
    "SEC-DISABLED-TLS",
}


def test_acceptance_python_fixtures() -> None:
    vuln_path = FIXTURES_DIR / "vulnerable_python.py"
    clean_path = FIXTURES_DIR / "clean_python.py"

    vuln_content = vuln_path.read_text(encoding="utf-8")
    clean_content = clean_path.read_text(encoding="utf-8")

    # 1. Test Vulnerable Python Fixture
    vuln_findings = default_diagnostics_engine.analyze_source_code(
        content=vuln_content,
        language="python",
        file_path="vulnerable_python.py",
    )
    detected_rule_ids = {f.rule_id for f in vuln_findings}

    # Verify ALL 7 security rules were triggered
    missing_rules = EXPECTED_SECURITY_RULES - detected_rule_ids
    assert not missing_rules, f"Vulnerable Python missed rules: {missing_rules}"
    assert len(vuln_findings) >= 7

    # 2. Test Clean Python Fixture (NO FALSE POSITIVES)
    clean_findings = default_diagnostics_engine.analyze_source_code(
        content=clean_content,
        language="python",
        file_path="clean_python.py",
    )
    assert len(clean_findings) == 0, (
        f"False positives detected on clean Python fixture: {[f.rule_id for f in clean_findings]}"
    )


def test_acceptance_java_fixtures() -> None:
    vuln_path = FIXTURES_DIR / "VulnerableJava.java"
    clean_path = FIXTURES_DIR / "CleanJava.java"

    vuln_content = vuln_path.read_text(encoding="utf-8")
    clean_content = clean_path.read_text(encoding="utf-8")

    # 1. Test Vulnerable Java Fixture
    vuln_findings = default_diagnostics_engine.analyze_source_code(
        content=vuln_content,
        language="java",
        file_path="VulnerableJava.java",
    )
    detected_rule_ids = {f.rule_id for f in vuln_findings}

    # Verify ALL 7 security rules were triggered
    missing_rules = EXPECTED_SECURITY_RULES - detected_rule_ids
    assert not missing_rules, f"Vulnerable Java missed rules: {missing_rules}"
    assert len(vuln_findings) >= 7

    # 2. Test Clean Java Fixture (NO FALSE POSITIVES)
    clean_findings = default_diagnostics_engine.analyze_source_code(
        content=clean_content,
        language="java",
        file_path="CleanJava.java",
    )
    assert len(clean_findings) == 0, (
        f"False positives detected on clean Java fixture: {[f.rule_id for f in clean_findings]}"
    )


def test_acceptance_javascript_fixtures() -> None:
    vuln_path = FIXTURES_DIR / "vulnerable_javascript.js"
    clean_path = FIXTURES_DIR / "clean_javascript.js"

    vuln_content = vuln_path.read_text(encoding="utf-8")
    clean_content = clean_path.read_text(encoding="utf-8")

    # 1. Test Vulnerable JavaScript Fixture
    vuln_findings = default_diagnostics_engine.analyze_source_code(
        content=vuln_content,
        language="javascript",
        file_path="vulnerable_javascript.js",
    )
    detected_rule_ids = {f.rule_id for f in vuln_findings}

    # Verify ALL 7 security rules were triggered with exactly 7 findings
    missing_rules = EXPECTED_SECURITY_RULES - detected_rule_ids
    assert not missing_rules, f"Vulnerable JavaScript missed rules: {missing_rules}"
    assert len(vuln_findings) == 7

    # 2. Test Clean JavaScript Fixture (NO FALSE POSITIVES)
    clean_findings = default_diagnostics_engine.analyze_source_code(
        content=clean_content,
        language="javascript",
        file_path="clean_javascript.js",
    )
    assert len(clean_findings) == 0, (
        f"False positives detected on clean JavaScript fixture: {[f.rule_id for f in clean_findings]}"
    )


def test_acceptance_requirements_manifests() -> None:
    vuln_path = FIXTURES_DIR / "requirements_vulnerable.txt"
    clean_path = FIXTURES_DIR / "requirements_clean.txt"

    vuln_content = vuln_path.read_text(encoding="utf-8")
    clean_content = clean_path.read_text(encoding="utf-8")

    # 1. Vulnerable requirements should detect known CVEs via OSV
    vuln_findings = default_diagnostics_engine.analyze_dependencies_content(
        content=vuln_content,
        manifest_type="requirements.txt",
        manifest_path="requirements_vulnerable.txt",
        query_osv=True,
    )
    assert len(vuln_findings) >= 1
    assert vuln_findings[0].rule_id == "DEP-VULNERABLE-PACKAGE"

    # 2. Clean requirements should return 0 findings
    clean_findings = default_diagnostics_engine.analyze_dependencies_content(
        content=clean_content,
        manifest_type="requirements.txt",
        manifest_path="requirements_clean.txt",
        query_osv=True,
    )
    assert len(clean_findings) == 0


def test_acceptance_pom_xml_manifests() -> None:
    vuln_path = FIXTURES_DIR / "pom_vulnerable.xml"
    clean_path = FIXTURES_DIR / "pom_clean.xml"

    vuln_content = vuln_path.read_text(encoding="utf-8")
    clean_content = clean_path.read_text(encoding="utf-8")

    # 1. Vulnerable pom.xml with Log4Shell 2.14.1
    vuln_findings = default_diagnostics_engine.analyze_dependencies_content(
        content=vuln_content,
        manifest_type="pom.xml",
        manifest_path="pom_vulnerable.xml",
        query_osv=True,
    )
    assert len(vuln_findings) >= 1
    assert any("CVE-2021-44228" in (f.message + str(f.metadata)) for f in vuln_findings)

    # 2. Clean pom.xml
    clean_findings = default_diagnostics_engine.analyze_dependencies_content(
        content=clean_content,
        manifest_type="pom.xml",
        manifest_path="pom_clean.xml",
        query_osv=True,
    )
    assert len(clean_findings) == 0


def test_acceptance_directory_scan_and_risk_scores() -> None:
    # Run full directory scan over fixtures directory
    report = default_diagnostics_engine.analyze_directory(
        root_dir=FIXTURES_DIR,
        query_osv=False,  # Keep local/fast for directory scan test
    )

    assert report.summary["total_findings"] >= 14
    assert report.summary["severity_counts"]["critical"] >= 4
    assert report.summary["severity_counts"]["high"] >= 6
