"""Test fixtures and helpers for parser tests."""

from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
JAVA_FIXTURES = FIXTURES_DIR / "java"
PYTHON_FIXTURES = FIXTURES_DIR / "python"

SIMPLE_JAVA = JAVA_FIXTURES / "Simple.java"
COMPLEX_JAVA = JAVA_FIXTURES / "Complex.java"
SIMPLE_PY = PYTHON_FIXTURES / "simple.py"
COMPLEX_PY = PYTHON_FIXTURES / "complex.py"
