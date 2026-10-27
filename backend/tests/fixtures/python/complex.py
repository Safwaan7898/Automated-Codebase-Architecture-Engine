"""Complex Python module — covers inheritance, decorators, high complexity."""

from __future__ import annotations

import functools
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar

from . import simple as _simple

logger = logging.getLogger(__name__)
F = TypeVar("F", bound=Callable[..., Any])


def retry(max_attempts: int = 3) -> Callable[[F], F]:
    """Decorator factory: retry a function on exception."""

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for attempt in range(max_attempts):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    logger.warning("Attempt %d failed: %s", attempt + 1, exc)
            raise RuntimeError(f"All {max_attempts} attempts failed") from last_exc

        return wrapper  # type: ignore[return-value]

    return decorator  # type: ignore[return-value]


class BaseProcessor(ABC):
    """Abstract base for all processors."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._registry: dict[str, Any] = {}

    @abstractmethod
    def process(self, data: Any) -> Any: ...

    @abstractmethod
    def validate(self, data: Any) -> bool: ...

    def register(self, key: str, value: Any) -> None:
        self._registry[key] = value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"


class DataProcessor(BaseProcessor):
    """Concrete processor with complex branching logic."""

    def __init__(self, name: str, threshold: float = 0.5) -> None:
        super().__init__(name)
        self.threshold = threshold
        self._simple = _simple.SimpleClass(name)

    def validate(self, data: Any) -> bool:
        if data is None:
            return False
        if isinstance(data, str) and len(data) == 0:
            return False
        if isinstance(data, (list, dict)) and len(data) == 0:
            return False
        return True

    @retry(max_attempts=3)
    def process(self, data: Any) -> dict[str, Any]:
        if not self.validate(data):
            raise ValueError(f"Invalid data: {data!r}")
        result: dict[str, Any] = {}
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    result[item] = len(item)
                elif isinstance(item, int):
                    result[str(item)] = item * 2
                else:
                    result[repr(item)] = None
        elif isinstance(data, dict):
            for k, v in data.items():
                if v is None:
                    continue
                elif isinstance(v, (int, float)):
                    result[k] = v * self.threshold
                else:
                    result[k] = str(v)
        else:
            result["value"] = data
        return result

    def classify(self, value: float) -> str:
        """High-complexity classification method."""
        if value < 0:
            category = "negative"
        elif value == 0:
            category = "zero"
        elif value < 0.1:
            category = "tiny"
        elif value < 1.0:
            category = "small"
        elif value < 10.0:
            category = "medium"
        elif value < 100.0:
            category = "large"
        else:
            category = "huge"
        return f"{self.name}:{category}"


class StreamingProcessor(DataProcessor):
    """Subclass of DataProcessor — tests multi-level inheritance."""

    def __init__(self, name: str, chunk_size: int = 100) -> None:
        super().__init__(name)
        self.chunk_size = chunk_size

    def process_stream(self, items: list[Any]) -> list[dict[str, Any]]:
        results = []
        for i in range(0, len(items), self.chunk_size):
            chunk = items[i : i + self.chunk_size]
            results.append(self.process(chunk))
        return results
