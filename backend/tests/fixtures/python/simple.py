"""Simple Python module used as a parser fixture."""

from __future__ import annotations

import os
from pathlib import Path


CONSTANT = "archlens"


def greet(name: str) -> str:
    """Return a greeting string."""
    return f"Hello, {name}!"


def read_file(path: str | Path) -> str:
    """Read a file and return its text content."""
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class SimpleClass:
    """A straightforward class with basic methods."""

    def __init__(self, name: str, value: int = 0) -> None:
        self.name = name
        self.value = value

    def describe(self) -> str:
        return f"SimpleClass(name={self.name!r}, value={self.value})"

    @property
    def is_positive(self) -> bool:
        return self.value > 0

    @staticmethod
    def from_env(key: str) -> "SimpleClass":
        val = os.environ.get(key, "")
        return SimpleClass(key, len(val))
