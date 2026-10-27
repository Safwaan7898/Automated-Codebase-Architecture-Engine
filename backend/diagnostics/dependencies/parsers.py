"""Parsers for project dependency manifests (requirements.txt, pom.xml, build.gradle)."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass
class Dependency:
    """Declared dependency in a package manifest."""

    name: str  # e.g. "jinja2" or "org.apache.logging.log4j:log4j-core"
    version: str  # e.g. "2.10" or "2.14.1"
    ecosystem: str  # "PyPI" or "Maven"
    manifest_path: str = ""
    line_number: int | None = None


def parse_requirements_txt(content: str, manifest_path: str = "requirements.txt") -> list[Dependency]:
    """Parse dependencies and versions from Python requirements.txt."""
    deps: list[Dependency] = []
    lines = content.splitlines()

    # Matches name==version or name>=version or name~=version
    req_pattern = re.compile(r"^\s*([a-zA-Z0-9_\-\.]+)\s*(?:==|>=|<=|~=)\s*([a-zA-Z0-9_\-\.]+)")

    for idx, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith(("#", "-", "@")):
            continue
        m = req_pattern.match(line)
        if m:
            pkg_name = m.group(1).lower()
            version = m.group(2)
            deps.append(
                Dependency(
                    name=pkg_name,
                    version=version,
                    ecosystem="PyPI",
                    manifest_path=manifest_path,
                    line_number=idx,
                )
            )

    return deps


def parse_pom_xml(content: str, manifest_path: str = "pom.xml") -> list[Dependency]:
    """Parse dependencies from Maven pom.xml."""
    deps: list[Dependency] = []
    try:
        root = ET.fromstring(content)  # noqa: S314
    except ET.ParseError:
        return deps

    # Strip XML namespaces for simplified element finding
    for elem in root.iter():
        if "}" in elem.tag:
            elem.tag = elem.tag.split("}", 1)[1]

    for dep_elem in root.iter("dependency"):
        group_id = dep_elem.findtext("groupId")
        artifact_id = dep_elem.findtext("artifactId")
        version = dep_elem.findtext("version")

        if group_id and artifact_id and version:
            # Skip variable interpolation like ${project.version} or ${log4j.version}
            clean_ver = version.strip()
            if not clean_ver.startswith("${"):
                package_name = f"{group_id.strip()}:{artifact_id.strip()}"
                deps.append(
                    Dependency(
                        name=package_name,
                        version=clean_ver,
                        ecosystem="Maven",
                        manifest_path=manifest_path,
                    )
                )

    return deps


def parse_build_gradle(content: str, manifest_path: str = "build.gradle") -> list[Dependency]:
    """Parse dependencies from Gradle build.gradle."""
    deps: list[Dependency] = []
    lines = content.splitlines()

    # Matches implementation 'group:artifact:version' or implementation("group:artifact:version")
    gradle_pattern = re.compile(
        r"""(?:implementation|api|compile|testImplementation)\s*\(?['"]([a-zA-Z0-9_\-\.]+):([a-zA-Z0-9_\-\.]+):([a-zA-Z0-9_\-\.]+)['"]\)?"""
    )

    for idx, line in enumerate(lines, 1):
        line = line.strip()
        if line.startswith("//"):
            continue
        m = gradle_pattern.search(line)
        if m:
            group = m.group(1)
            artifact = m.group(2)
            version = m.group(3)
            deps.append(
                Dependency(
                    name=f"{group}:{artifact}",
                    version=version,
                    ecosystem="Maven",
                    manifest_path=manifest_path,
                    line_number=idx,
                )
            )

    return deps
