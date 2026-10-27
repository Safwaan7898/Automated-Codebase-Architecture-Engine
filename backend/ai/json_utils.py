"""Robust JSON extraction and validation utility for AI provider responses.

Handles outputs from reasoning models (e.g. models emitting `<think>...</think>`,
markdown fences, or conversational preambles/postambles before/after JSON).
"""

from __future__ import annotations

import json
import re
from typing import Any, Type, TypeVar
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def extract_raw_json_str(text: str) -> str:
    """Extract a candidate JSON string from text, stripping reasoning tags and markdown blocks."""
    if not text:
        return ""

    # 1. Strip reasoning thoughts if emitted (<think>...</think>)
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.DOTALL).strip()

    # 2. Extract from markdown code fences if present (e.g. ```json ... ``` or ``` ... ```)
    code_fence_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    fence_matches = re.findall(code_fence_pattern, cleaned, flags=re.IGNORECASE)
    if fence_matches:
        for candidate in fence_matches:
            candidate_str = candidate.strip()
            if candidate_str.startswith(("{", "[")):
                return candidate_str

    # 3. Find first '{' or '[' and match to balanced or last '}' or ']'
    first_brace = cleaned.find("{")
    first_bracket = cleaned.find("[")

    if first_brace == -1 and first_bracket == -1:
        return cleaned

    # Determine whether object or array starts first
    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        start_idx = first_brace
        end_char = "}"
    else:
        start_idx = first_bracket
        end_char = "]"

    # Use JSONDecoder raw_decode to parse starting from start_idx
    sub_text = cleaned[start_idx:]
    try:
        decoder = json.JSONDecoder()
        _, end_pos = decoder.raw_decode(sub_text)
        return sub_text[:end_pos]
    except Exception:
        # Fallback to finding the last occurrence of end_char
        last_idx = cleaned.rfind(end_char)
        if last_idx > start_idx:
            return cleaned[start_idx : last_idx + 1]

    return cleaned


def extract_and_parse_json(text: str) -> dict[str, Any] | list[Any]:
    """Extract JSON object or list from arbitrary text emitted by reasoning models.

    Raises ValueError if valid JSON cannot be found or decoded.
    """
    candidate = extract_raw_json_str(text)
    try:
        data = json.loads(candidate)
        if isinstance(data, (dict, list)):
            return data
    except json.JSONDecodeError:
        pass

    # Secondary attempt: find the first '{' or '[' in the original text and raw_decode
    first_brace = text.find("{")
    first_bracket = text.find("[")
    candidates_indices = [idx for idx in (first_brace, first_bracket) if idx != -1]
    if candidates_indices:
        start_idx = min(candidates_indices)
        try:
            obj, _ = json.JSONDecoder().raw_decode(text[start_idx:])
            if isinstance(obj, (dict, list)):
                return obj
        except Exception:
            pass

    raise ValueError(f"Could not extract valid JSON from response text: {text[:150]}...")


def extract_and_validate_pydantic(text: str, schema: Type[T]) -> T:
    """Extract and validate a Pydantic model from raw AI response text."""
    data = extract_and_parse_json(text)
    if isinstance(data, dict):
        return schema.model_validate(data)
    elif isinstance(data, list):
        return schema.model_validate(data)
    else:
        raise ValueError(
            f"Expected dict or list for schema {schema.__name__}, got {type(data).__name__}"
        )
