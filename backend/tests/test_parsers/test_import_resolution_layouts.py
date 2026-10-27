"""Tests for suffix-based import resolution across project layouts.

Covers:
- Flat layout (files in root)
- src/ layout (code under src/package)
- backend/app/ layout (nested application package)
- Deterministic ambiguity resolution (same top-level directory first, then lexicographic)
- Counting ambiguous_imports in AnalysisResult
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.analyzers.python_analyzer import PythonAnalyzer


def test_flat_layout(tmp_path: Path) -> None:
    """Flat layout: root modules import each other directly."""
    (tmp_path / "gamma.py").write_text("class Gamma:\n    pass\n", encoding="utf-8")
    (tmp_path / "beta.py").write_text("from gamma import Gamma\n", encoding="utf-8")
    (tmp_path / "alpha.py").write_text("from beta import Gamma\nimport beta\n", encoding="utf-8")

    analyzer = PythonAnalyzer()
    res = analyzer.analyze(tmp_path)

    edge_tuples = {(e.source, e.target) for e in res.graph.edges}
    assert ("alpha", "beta") in edge_tuples
    assert ("beta", "gamma") in edge_tuples
    assert res.ambiguous_imports == 0


def test_src_layout(tmp_path: Path) -> None:
    """src/ layout: package root is nested under src/."""
    src_dir = tmp_path / "src" / "mypkg"
    src_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text("from mypkg.service import Service\n", encoding="utf-8")
    (src_dir / "model.py").write_text("class Model:\n    pass\n", encoding="utf-8")
    (src_dir / "service.py").write_text("from mypkg.model import Model\n", encoding="utf-8")

    analyzer = PythonAnalyzer()
    res = analyzer.analyze(tmp_path)

    edge_tuples = {(e.source, e.target) for e in res.graph.edges}
    assert ("src.mypkg", "src.mypkg.service") in edge_tuples
    assert ("src.mypkg.service", "src.mypkg.model") in edge_tuples
    assert res.ambiguous_imports == 0


def test_backend_app_layout(tmp_path: Path) -> None:
    """backend/app/ layout: nested app package with internal imports."""
    app_dir = tmp_path / "backend" / "app"
    services_dir = app_dir / "services"
    models_dir = app_dir / "models"
    services_dir.mkdir(parents=True)
    models_dir.mkdir(parents=True)

    (app_dir / "__init__.py").write_text("", encoding="utf-8")
    (models_dir / "__init__.py").write_text("", encoding="utf-8")
    (models_dir / "item.py").write_text("class Item:\n    pass\n", encoding="utf-8")
    (services_dir / "__init__.py").write_text("", encoding="utf-8")
    (services_dir / "worker.py").write_text("from app.models.item import Item\n", encoding="utf-8")
    (app_dir / "main.py").write_text(
        "from app.services.worker import do_work\nfrom app.models.item import Item\n",
        encoding="utf-8",
    )

    analyzer = PythonAnalyzer()
    res = analyzer.analyze(tmp_path)

    edge_tuples = {(e.source, e.target) for e in res.graph.edges}
    assert ("backend.app.main", "backend.app.services.worker") in edge_tuples
    assert ("backend.app.main", "backend.app.models.item") in edge_tuples
    assert ("backend.app.services.worker", "backend.app.models.item") in edge_tuples
    assert res.ambiguous_imports == 0


def test_deterministic_ambiguity_resolution(tmp_path: Path) -> None:
    """Ambiguous suffix matches resolve same-top-level first, then lexicographically."""
    pkg1 = tmp_path / "pkg1"
    pkg2 = tmp_path / "pkg2"
    pkg1.mkdir()
    pkg2.mkdir()

    (pkg1 / "common.py").write_text("def run(): pass\n", encoding="utf-8")
    (pkg2 / "common.py").write_text("def run(): pass\n", encoding="utf-8")

    # pkg1.consumer imports 'common'; both pkg1.common and pkg2.common match suffix 'common'
    # Same-top-level directory rule must resolve to pkg1.common
    (pkg1 / "consumer.py").write_text("from common import run\n", encoding="utf-8")

    analyzer = PythonAnalyzer()
    res = analyzer.analyze(tmp_path)

    edge_tuples = {(e.source, e.target) for e in res.graph.edges}
    assert ("pkg1.consumer", "pkg1.common") in edge_tuples
    assert ("pkg1.consumer", "pkg2.common") not in edge_tuples
    assert res.ambiguous_imports >= 1
