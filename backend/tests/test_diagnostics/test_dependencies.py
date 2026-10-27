"""Tests for dependency parsing, OSV.dev querying, and dependency rules."""

from diagnostics.dependencies.osv_client import OSVClient
from diagnostics.dependencies.parsers import (
    parse_build_gradle,
    parse_pom_xml,
    parse_requirements_txt,
)
from diagnostics.dependencies.rules import VulnerableDependencyRule
from diagnostics.models import Severity


def test_parse_requirements_txt() -> None:
    content = """
    # Comments should be ignored
    fastapi==0.115.12
    requests>=2.20.0
    jinja2==2.10
    """
    deps = parse_requirements_txt(content, "reqs.txt")
    assert len(deps) == 3
    names = {d.name: d.version for d in deps}
    assert names["fastapi"] == "0.115.12"
    assert names["jinja2"] == "2.10"
    assert all(d.ecosystem == "PyPI" for d in deps)


def test_parse_pom_xml() -> None:
    xml = """
    <project>
      <dependencies>
        <dependency>
          <groupId>org.apache.logging.log4j</groupId>
          <artifactId>log4j-core</artifactId>
          <version>2.14.1</version>
        </dependency>
      </dependencies>
    </project>
    """
    deps = parse_pom_xml(xml, "pom.xml")
    assert len(deps) == 1
    assert deps[0].name == "org.apache.logging.log4j:log4j-core"
    assert deps[0].version == "2.14.1"
    assert deps[0].ecosystem == "Maven"


def test_parse_build_gradle() -> None:
    gradle = """
    dependencies {
        implementation 'org.apache.logging.log4j:log4j-core:2.14.1'
        testImplementation("org.junit.jupiter:junit-jupiter:5.8.2")
    }
    """
    deps = parse_build_gradle(gradle, "build.gradle")
    assert len(deps) == 2
    assert deps[0].name == "org.apache.logging.log4j:log4j-core"
    assert deps[0].version == "2.14.1"


def test_vulnerable_dependency_rule_flags_cve() -> None:
    rule = VulnerableDependencyRule()
    fake_cve = [
        {
            "id": "GHSA-jfh8-c2jp-5v3q",
            "aliases": ["CVE-2021-44228"],
            "summary": "Log4Shell remote code execution",
            "database_specific": {"severity": "CRITICAL"},
        }
    ]

    findings = rule.check_dependency(
        package_name="org.apache.logging.log4j:log4j-core",
        version="2.14.1",
        ecosystem="Maven",
        manifest_path="pom.xml",
        cve_data=fake_cve,
    )

    assert len(findings) == 1
    assert findings[0].rule_id == "DEP-VULNERABLE-PACKAGE"
    assert findings[0].severity == Severity.CRITICAL
    assert "CVE-2021-44228" in findings[0].message
    assert "pom.xml" in findings[0].file_path


def test_osv_client_caching() -> None:
    client = OSVClient()
    # Pre-populate cache to test local resolution without network
    client._cache[("pypi", "jinja2", "2.10")] = [{"id": "TEST-VULN", "aliases": ["CVE-9999-0001"]}]

    res = client.query_sync("jinja2", "2.10", "PyPI")
    assert len(res) == 1
    assert res[0]["id"] == "TEST-VULN"
