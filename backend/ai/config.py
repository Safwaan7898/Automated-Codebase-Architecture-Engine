"""Configuration settings for ArchLens AI engine."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple
from pydantic import BaseModel, Field
import dotenv


# Absolute path to backend directory and default .env file
BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = (BACKEND_DIR / ".env").resolve()

# Provider default models that are verified to exist at providers
BUILTIN_DEFAULT_MODELS: dict[str, str] = {
    "groq": "openai/gpt-oss-20b",
    "nvidia": "google/diffusiongemma-26b-a4b-it",
    "gemini": "gemini-3.1-flash-lite",
    "anthropic": "claude-3-5-sonnet-20241022",
    "openai": "gpt-4o-mini",
    "ollama": "llama3.2",
    "fake": "fake-v1",
}


class ProviderConfig(BaseModel):
    """Configuration for a specific AI provider."""

    name: str
    api_key: str = Field(default="", repr=False)
    model: str = ""
    base_url: str = ""
    trains_on_prompts: bool = False
    rpm_limit: int = 30

    def __repr__(self) -> str:
        return (
            f"ProviderConfig(name={self.name!r}, model={self.model!r}, "
            f"base_url={self.base_url!r}, trains_on_prompts={self.trains_on_prompts!r}, "
            f"rpm_limit={self.rpm_limit!r}, api_key='[REDACTED]')"
        )

    def __str__(self) -> str:
        return self.__repr__()


class AISettings(BaseModel):
    """Runtime configuration for AI features with multi-provider chain support."""

    enabled: bool = Field(default=False)
    # Single-provider backward compatibility
    provider: str = Field(default="fake")
    api_key: str = Field(default="", repr=False)
    model: str = Field(default="")

    # Multi-provider chain support
    provider_order: list[str] = Field(default_factory=lambda: ["groq", "nvidia", "gemini"])
    allow_training_providers: bool = Field(default=False)
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)

    # Metadata about loaded configuration
    loaded_env_path: str | None = None
    env_var_names: list[str] = Field(default_factory=list)
    model_sources: dict[str, str] = Field(default_factory=dict)

    # Global guardrails
    max_tokens_per_analysis: int = Field(default=10000)
    budget_usd: float = Field(default=1.0)
    request_timeout_seconds: float = Field(default=15.0)
    max_retries: int = Field(default=2)
    backoff_factor: float = Field(default=1.5)

    def __repr__(self) -> str:
        return (
            f"AISettings(enabled={self.enabled}, provider_order={self.provider_order}, "
            f"loaded_env_path={self.loaded_env_path!r}, env_var_names={self.env_var_names!r}, "
            f"providers={list(self.providers.keys())}, api_key='[REDACTED]')"
        )

    def __str__(self) -> str:
        return self.__repr__()

    def is_builtin_default(self, provider_name: str) -> bool:
        """Check if provider's model came from built-in default rather than explicit configuration."""
        return self.model_sources.get(provider_name.lower()) == "builtin_default"

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        if self.provider:
            if self.provider not in self.providers:
                self.providers[self.provider] = ProviderConfig(
                    name=self.provider,
                    api_key=self.api_key,
                    model=self.model,
                )
            else:
                if self.api_key and not self.providers[self.provider].api_key:
                    self.providers[self.provider].api_key = self.api_key
                if self.model and not self.providers[self.provider].model:
                    self.providers[self.provider].model = self.model

    @classmethod
    def from_env(cls, env_file: Path | str | None = None) -> AISettings:
        """Load settings from environment variables and backend/.env via an absolute path."""
        resolved_path: Path | None = None
        file_vars: dict[str, str] = {}

        target_path = Path(env_file).resolve() if env_file is not None else DEFAULT_ENV_PATH
        if target_path.is_file():
            resolved_path = target_path
            try:
                raw_vals = dotenv.dotenv_values(target_path)
                file_vars = {k: v for k, v in raw_vals.items() if v is not None}
            except Exception:
                file_vars = {}

        # Export file variables to os.environ if not already present
        # (ensuring real env vars always override file vars)
        for k, v in file_vars.items():
            if k not in os.environ:
                os.environ[k] = v

        def get_val(key: str, default: str = "") -> str:
            # Real environment variables override the file
            val = os.environ.get(key)
            if val is not None and val != "":
                return val.strip()
            return file_vars.get(key, default).strip()

        enabled_str = get_val("ARCHLENS_AI_ENABLED", "false").lower()
        enabled = enabled_str in ("1", "true", "yes", "on")

        order_str = get_val("ARCHLENS_AI_PROVIDER_ORDER", "")
        if order_str:
            provider_order = [p.strip().lower() for p in order_str.split(",") if p.strip()]
        else:
            legacy_provider = get_val("ARCHLENS_AI_PROVIDER", "").lower()
            if legacy_provider:
                provider_order = [legacy_provider]
            else:
                provider_order = ["groq", "nvidia", "gemini"]

        app_env = (os.environ.get("ARCHLENS_ENV") or get_val("ARCHLENS_ENV", "development")).lower()
        if "fake" in provider_order and app_env == "production":
            raise ValueError("Test-mode fake AI provider cannot be enabled when ARCHLENS_ENV is production.")

        allow_training_str = get_val("ARCHLENS_AI_ALLOW_TRAINING_PROVIDERS", "false").lower()
        allow_training = allow_training_str in ("1", "true", "yes", "on")

        def get_rpm(name: str, default_val: int) -> int:
            rpm_str = get_val(f"ARCHLENS_AI_RPM_{name.upper()}", str(default_val))
            try:
                return int(rpm_str)
            except ValueError:
                return default_val

        model_sources: dict[str, str] = {}

        def get_model(name: str, default_val: str) -> str:
            var_name = f"ARCHLENS_AI_MODEL_{name.upper()}"
            val = os.environ.get(var_name)
            if val is not None and val.strip():
                model_sources[name.lower()] = "env_var"
                return val.strip()
            if var_name in file_vars and file_vars[var_name].strip():
                model_sources[name.lower()] = "env_file"
                return file_vars[var_name].strip()
            gen_env = os.environ.get("ARCHLENS_AI_MODEL")
            if gen_env is not None and gen_env.strip():
                model_sources[name.lower()] = "env_var"
                return gen_env.strip()
            if "ARCHLENS_AI_MODEL" in file_vars and file_vars["ARCHLENS_AI_MODEL"].strip():
                model_sources[name.lower()] = "env_file"
                return file_vars["ARCHLENS_AI_MODEL"].strip()
            model_sources[name.lower()] = "builtin_default"
            return default_val

        providers: dict[str, ProviderConfig] = {}

        # Groq (OpenAI-compatible)
        groq_key = get_val("GROQ_API_KEY") or get_val("ARCHLENS_AI_API_KEY")
        providers["groq"] = ProviderConfig(
            name="groq",
            api_key=groq_key,
            model=get_model("groq", BUILTIN_DEFAULT_MODELS["groq"]),
            base_url="https://api.groq.com/openai/v1",
            trains_on_prompts=False,
            rpm_limit=get_rpm("groq", 30),
        )

        # NVIDIA (OpenAI-compatible)
        nvidia_key = get_val("NVIDIA_API_KEY")
        providers["nvidia"] = ProviderConfig(
            name="nvidia",
            api_key=nvidia_key,
            model=get_model("nvidia", BUILTIN_DEFAULT_MODELS["nvidia"]),
            base_url="https://integrate.api.nvidia.com/v1",
            trains_on_prompts=False,
            rpm_limit=get_rpm("nvidia", 40),
        )

        # Gemini (custom adapter, trains_on_prompts=True)
        gemini_key = get_val("GEMINI_API_KEY") or get_val("ARCHLENS_AI_API_KEY")
        providers["gemini"] = ProviderConfig(
            name="gemini",
            api_key=gemini_key,
            model=get_model("gemini", BUILTIN_DEFAULT_MODELS["gemini"]),
            base_url="https://generativelanguage.googleapis.com/v1beta",
            trains_on_prompts=True,
            rpm_limit=get_rpm("gemini", 15),
        )

        # Anthropic (legacy / optional)
        anthropic_key = get_val("ANTHROPIC_API_KEY")
        providers["anthropic"] = ProviderConfig(
            name="anthropic",
            api_key=anthropic_key,
            model=get_model("anthropic", BUILTIN_DEFAULT_MODELS["anthropic"]),
            base_url="https://api.anthropic.com/v1",
            trains_on_prompts=False,
            rpm_limit=get_rpm("anthropic", 20),
        )

        # OpenAI (legacy / optional)
        openai_key = get_val("OPENAI_API_KEY")
        providers["openai"] = ProviderConfig(
            name="openai",
            api_key=openai_key,
            model=get_model("openai", BUILTIN_DEFAULT_MODELS["openai"]),
            base_url="https://api.openai.com/v1",
            trains_on_prompts=False,
            rpm_limit=get_rpm("openai", 60),
        )

        # Fake provider (for tests / offline)
        providers["fake"] = ProviderConfig(
            name="fake",
            api_key="mock-fake-key",
            model=get_model("fake", BUILTIN_DEFAULT_MODELS["fake"]),
            base_url="local://mock",
            trains_on_prompts=False,
            rpm_limit=get_rpm("fake", 10000),
        )

        # Ollama (local server, OpenAI-compatible, optional, no key required)
        ollama_base = get_val("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        if not ollama_base.endswith("/v1"):
            ollama_api_url = f"{ollama_base}/v1"
        else:
            ollama_api_url = ollama_base
        providers["ollama"] = ProviderConfig(
            name="ollama",
            api_key="ollama-local",
            model=get_model("ollama", BUILTIN_DEFAULT_MODELS["ollama"]),
            base_url=ollama_api_url,
            trains_on_prompts=False,
            rpm_limit=get_rpm("ollama", 120),
        )

        try:
            max_tokens = int(get_val("ARCHLENS_AI_MAX_TOKENS_PER_ANALYSIS", "10000"))
        except ValueError:
            max_tokens = 10000

        try:
            budget = float(get_val("ARCHLENS_AI_BUDGET", "1.0"))
        except ValueError:
            budget = 1.0

        return cls(
            enabled=enabled,
            provider=provider_order[0] if provider_order else "fake",
            api_key=get_val("ARCHLENS_AI_API_KEY"),
            model=get_val("ARCHLENS_AI_MODEL"),
            provider_order=provider_order,
            allow_training_providers=allow_training,
            providers=providers,
            loaded_env_path=str(resolved_path) if resolved_path else None,
            env_var_names=sorted(list(file_vars.keys())),
            model_sources=model_sources,
            max_tokens_per_analysis=max_tokens,
            budget_usd=budget,
        )


_GLOBAL_AI_SETTINGS: AISettings | None = None


def get_ai_settings(reload: bool = False, env_file: Path | str | None = None) -> AISettings:
    """Retrieve singleton AISettings instance, optionally reloading from disk/environment."""
    global _GLOBAL_AI_SETTINGS
    if _GLOBAL_AI_SETTINGS is None or reload or env_file is not None:
        _GLOBAL_AI_SETTINGS = AISettings.from_env(env_file=env_file)
    return _GLOBAL_AI_SETTINGS


def estimate_token_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD based on provider and token counts."""
    rates: dict[str, tuple[float, float]] = {
        "groq": (0.05, 0.08),
        "nvidia": (0.10, 0.20),
        "gemini": (0.35, 1.05),
        "anthropic": (3.00, 15.00),
        "openai": (2.50, 10.00),
        "ollama": (0.00, 0.00),
        "fake": (0.00, 0.00),
    }

    input_rate, output_rate = rates.get(provider.lower(), (0.20, 0.50))
    cost = (input_tokens / 1_000_000.0) * input_rate + (output_tokens / 1_000_000.0) * output_rate
    return round(cost, 6)
