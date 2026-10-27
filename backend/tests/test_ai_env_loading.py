"""Offline tests for .env loading, environment variable overriding, and secret redaction."""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from ai.config import AISettings, ProviderConfig, BUILTIN_DEFAULT_MODELS
from ai.check import _sanitize_message


def test_env_loading_from_two_different_working_directories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure .env file is loaded accurately regardless of current working directory."""
    # Isolate environment
    for key in list(os.environ.keys()):
        if key.startswith("ARCHLENS_AI_") or key.endswith("_API_KEY"):
            monkeypatch.delenv(key, raising=False)

    temp_env_file = tmp_path / "custom.env"
    temp_env_file.write_text(
        "ARCHLENS_AI_ENABLED=true\n"
        "ARCHLENS_AI_PROVIDER_ORDER=groq,fake\n"
        "ARCHLENS_AI_MODEL_GROQ=offline-custom-groq-model\n"
        "GROQ_API_KEY=test-offline-groq-key\n",
        encoding="utf-8",
    )

    other_dir = tmp_path / "subdir"
    other_dir.mkdir()

    # 1. Load while working directory is tmp_path
    monkeypatch.chdir(tmp_path)
    settings_1 = AISettings.from_env(env_file=temp_env_file)
    assert settings_1.enabled is True
    assert settings_1.provider_order == ["groq", "fake"]
    assert settings_1.providers["groq"].model == "offline-custom-groq-model"
    assert settings_1.providers["groq"].api_key == "test-offline-groq-key"

    # 2. Load while working directory is other_dir
    monkeypatch.chdir(other_dir)
    settings_2 = AISettings.from_env(env_file=temp_env_file)
    assert settings_2.enabled is True
    assert settings_2.provider_order == ["groq", "fake"]
    assert settings_2.providers["groq"].model == "offline-custom-groq-model"
    assert settings_2.providers["groq"].api_key == "test-offline-groq-key"


def test_environment_variable_overrides_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that real environment variables override values from the .env file."""
    # Clean env
    for key in list(os.environ.keys()):
        if key.startswith("ARCHLENS_AI_") or key.endswith("_API_KEY"):
            monkeypatch.delenv(key, raising=False)

    temp_env_file = tmp_path / "test.env"
    temp_env_file.write_text(
        "ARCHLENS_AI_ENABLED=false\nARCHLENS_AI_MODEL_GROQ=model-from-file\nGROQ_API_KEY=key-from-file\n",
        encoding="utf-8",
    )

    # Set real environment variable overrides
    monkeypatch.setenv("ARCHLENS_AI_ENABLED", "true")
    monkeypatch.setenv("ARCHLENS_AI_MODEL_GROQ", "model-from-real-env")
    monkeypatch.setenv("GROQ_API_KEY", "key-from-real-env")

    settings = AISettings.from_env(env_file=temp_env_file)

    assert settings.enabled is True
    assert settings.providers["groq"].model == "model-from-real-env"
    assert settings.providers["groq"].api_key == "key-from-real-env"
    assert settings.model_sources.get("groq") == "env_var"


def test_no_secret_keys_in_output_log_or_exceptions() -> None:
    """Verify that API keys never appear in string representations, reprs, or sanitized error text."""
    secret_key = "mock_test_super_secret_token_abcdef123456"

    cfg = ProviderConfig(name="groq", api_key=secret_key, model="test-model")
    settings = AISettings(
        enabled=True,
        provider="groq",
        api_key=secret_key,
        providers={"groq": cfg},
    )

    # 1. repr and str check
    assert secret_key not in repr(cfg)
    assert secret_key not in str(cfg)
    assert secret_key not in repr(settings)
    assert secret_key not in str(settings)
    assert "[REDACTED]" in repr(cfg)

    # 2. Sanitizer check for exceptions and messages
    raw_error_message = f"Error from upstream provider: invalid credentials for key {secret_key}"
    sanitized = _sanitize_message(raw_error_message, [secret_key])
    assert secret_key not in sanitized
    assert "[REDACTED_KEY]" in sanitized or "[REDACTED" in sanitized


def test_builtin_default_model_and_alias_warnings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify detection of built-in default models and -latest aliases."""
    for key in list(os.environ.keys()):
        if key.startswith("ARCHLENS_AI_") or key.endswith("_API_KEY"):
            monkeypatch.delenv(key, raising=False)

    temp_env_file = tmp_path / "warning.env"
    temp_env_file.write_text(
        "ARCHLENS_AI_MODEL_GEMINI=gemini-flash-latest\n",
        encoding="utf-8",
    )

    settings = AISettings.from_env(env_file=temp_env_file)

    # Groq was not specified in .env, so it should be identified as built-in default
    assert settings.is_builtin_default("groq") is True
    assert settings.providers["groq"].model == BUILTIN_DEFAULT_MODELS["groq"]

    # Gemini was specified with -latest
    assert settings.is_builtin_default("gemini") is False
    assert "-latest" in settings.providers["gemini"].model
