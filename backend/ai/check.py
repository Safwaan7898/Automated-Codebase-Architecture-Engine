"""CLI utility to verify configured AI providers, model IDs, and connectivity.

Run via:
    python -m ai.check
    python -m ai.check --list-models
"""

from __future__ import annotations

import argparse
import difflib
import os
import re
import sys
import time
from typing import Any, List, Tuple

import httpx

from .config import AISettings, ProviderConfig, BUILTIN_DEFAULT_MODELS
from .privacy import redact_secrets


def _sanitize_message(text: str, keys: list[str]) -> str:
    """Scrub any accidental API keys or authorization tokens from display text."""
    redacted = redact_secrets(text)
    for key in keys:
        if key and len(key) >= 4:
            redacted = redacted.replace(key, "[REDACTED_KEY]")
    # Scrub URL query params with key=...
    redacted = re.sub(r"([?&]key=)[^&\s]+", r"\1[REDACTED_KEY]", redacted)
    # Scrub Bearer tokens
    redacted = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", r"\1[REDACTED_KEY]", redacted)
    return redacted


def _filter_chat_models(provider_name: str, models: list[str]) -> list[str]:
    """Filter candidate models down to chat-capable generation models."""
    p = provider_name.lower()
    if p == "groq":
        # Exclude audio and guardrail models
        return [
            m for m in models
            if not m.startswith("whisper") and "prompt-guard" not in m
        ]
    elif p == "gemini":
        # Keep models with 'gemini' and exclude embeddings/aqa
        filtered = []
        for m in models:
            m_clean = m.replace("models/", "")
            if "gemini" in m_clean.lower() and "embedding" not in m_clean.lower():
                filtered.append(m)
        return filtered
    elif p == "nvidia":
        # All models from NVIDIA integrate API are completions/chat models
        return models
    elif p == "fake":
        return ["fake-v1", "fake-v2", "fake-test"]
    return models


def _fetch_models_and_probe(
    provider_name: str,
    cfg: ProviderConfig,
) -> tuple[bool, int, float, str, list[str]]:
    """Fetch available model IDs and send a real 1-token chat request probe.

    Returns:
        (success, http_status, latency_ms, error_detail, available_models)
    """
    keys_to_scrub = [cfg.api_key]
    timeout = httpx.Timeout(40.0, connect=15.0)

    # 1. Fake Provider
    if provider_name == "fake":
        models = ["fake-v1", "fake-v2", "fake-test"]
        target_model = cfg.model or "fake-v1"
        if target_model not in models:
            return False, 404, 0.0, f"Model '{target_model}' not found in available models", models
        time.sleep(0.01)
        return True, 200, 10.0, "", models

    # 2. Ollama Local Provider
    if provider_name == "ollama":
        base_url = (cfg.base_url or "http://localhost:11434").rstrip("/")
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(f"{base_url}/api/tags")
                status = resp.status_code
                if status != 200:
                    return False, status, 0.0, f"Failed to fetch model tags (HTTP {status})", []
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                normalized_models = set(models)
                for m in models:
                    if ":" in m:
                        normalized_models.add(m.split(":")[0])
                all_models = sorted(list(normalized_models))

                target_model = cfg.model
                if target_model not in normalized_models:
                    return False, 404, 0.0, f"Configured model '{target_model}' not found in Ollama repository", all_models

                probe_url = f"{base_url}/v1/chat/completions" if not base_url.endswith("/v1") else f"{base_url}/chat/completions"
                t0 = time.perf_counter()
                probe_resp = client.post(
                    probe_url,
                    json={
                        "model": target_model,
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 1,
                    },
                )
                latency_ms = (time.perf_counter() - t0) * 1000.0
                if probe_resp.status_code in (200, 201):
                    return True, probe_resp.status_code, round(latency_ms, 2), "", all_models
                else:
                    return False, probe_resp.status_code, round(latency_ms, 2), probe_resp.text, all_models
        except Exception as exc:
            return False, 0, 0.0, _sanitize_message(str(exc), keys_to_scrub), []

    # 3. Gemini Provider
    if provider_name == "gemini":
        base_url = "https://generativelanguage.googleapis.com/v1beta"
        headers = {"Content-Type": "application/json"}
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(f"{base_url}/models?key={cfg.api_key}", headers=headers)
                if resp.status_code != 200:
                    return False, resp.status_code, 0.0, f"HTTP {resp.status_code}: {resp.text}", []
                data = resp.json()
                models_raw = [m.get("name", "") for m in data.get("models", [])]
                all_models = set()
                for m in models_raw:
                    all_models.add(m)
                    if m.startswith("models/"):
                        all_models.add(m[len("models/"):])
                sorted_models = sorted(list(all_models))

                target_model = cfg.model or BUILTIN_DEFAULT_MODELS["gemini"]
                if target_model not in all_models:
                    return False, 404, 0.0, f"Configured model '{target_model}' not found in Gemini API", sorted_models

                clean_model_id = target_model[len("models/"): ] if target_model.startswith("models/") else target_model
                probe_url = f"{base_url}/models/{clean_model_id}:generateContent?key={cfg.api_key}"
                t0 = time.perf_counter()
                probe_resp = client.post(
                    probe_url,
                    headers=headers,
                    json={
                        "contents": [{"parts": [{"text": "ping"}]}],
                        "generationConfig": {"maxOutputTokens": 1},
                    },
                )
                latency_ms = (time.perf_counter() - t0) * 1000.0
                if probe_resp.status_code == 200:
                    return True, 200, round(latency_ms, 2), "", sorted_models
                else:
                    return False, probe_resp.status_code, round(latency_ms, 2), probe_resp.text, sorted_models
        except Exception as exc:
            return False, 0, 0.0, _sanitize_message(str(exc), keys_to_scrub), []

    # 4. OpenAI-Compatible Providers (Groq, NVIDIA, OpenAI)
    base_url = cfg.base_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            models = []
            try:
                resp = client.get(f"{base_url}/models", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    models = sorted([m.get("id", "") for m in data.get("data", []) if m.get("id")])
            except Exception:
                models = []

            target_model = cfg.model
            if models and target_model not in models:
                return False, 404, 0.0, f"Configured model '{target_model}' not found in {provider_name} models list", models

            t0 = time.perf_counter()
            probe_resp = client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json={
                    "model": target_model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                },
            )
            latency_ms = (time.perf_counter() - t0) * 1000.0
            if probe_resp.status_code in (200, 201):
                return True, probe_resp.status_code, round(latency_ms, 2), "", models
            else:
                return False, probe_resp.status_code, round(latency_ms, 2), probe_resp.text, models
    except Exception as exc:
        return False, 0, 0.0, _sanitize_message(str(exc), keys_to_scrub), []


def main(argv: list[str] | None = None) -> int:
    """Run model verification and connectivity probe for configured AI providers."""
    parser = argparse.ArgumentParser(description="ArchLens AI Provider & Model Verification")
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Print chat-capable model IDs per provider, mark the configured one",
    )
    args = parser.parse_args(argv)

    settings = AISettings.from_env()

    env_path_str = settings.loaded_env_path if settings.loaded_env_path else "none found"
    var_names = sorted(settings.env_var_names)
    key_providers = ["groq", "nvidia", "gemini"]
    keys_present = sum(
        1 for p in key_providers if settings.providers.get(p) and settings.providers[p].api_key
    )

    print("=" * 70)
    print("ArchLens AI Provider & Model Verification (ai.check)")
    print(f".env loaded: {env_path_str}")
    print(f"Variable names in .env: {var_names}")
    print(f"Keys present: {keys_present}/3")
    print(f"Enabled in environment: {settings.enabled}")
    print(f"Configured Provider Chain: {' -> '.join(settings.provider_order)}")
    print("=" * 70)

    has_error = False
    active_providers_checked = 0

    for provider_name in settings.provider_order:
        cfg = settings.providers.get(provider_name)
        if not cfg:
            cfg = ProviderConfig(name=provider_name)

        keys_to_scrub = [cfg.api_key]
        print(f"\n[{provider_name.upper()}] Effective Model: '{cfg.model}'")

        # Warning when model is built-in default
        if settings.is_builtin_default(provider_name):
            print(f"  [WARNING] Model '{cfg.model}' is using built-in default ID (not explicitly configured in .env or environment).")

        # Warning when model is a '-latest' alias
        if "-latest" in cfg.model:
            print(f"  [WARNING] Model '{cfg.model}' uses a '-latest' alias; recommended to pin to a concrete version.")

        # Skip providers with no key, unless fake or ollama
        if provider_name not in ("fake", "ollama") and not cfg.api_key:
            print("  STATUS: SKIPPED (No API key provided in environment)")
            continue

        active_providers_checked += 1
        success, status, latency_ms, error_detail, available_models = _fetch_models_and_probe(
            provider_name, cfg
        )

        if args.list_models and available_models:
            chat_models = _filter_chat_models(provider_name, available_models)
            print("  Chat-Capable Models:")
            for m in chat_models:
                is_configured = (
                    m == cfg.model
                    or (provider_name == "gemini" and (m == f"models/{cfg.model}" or m.replace("models/", "") == cfg.model))
                )
                marker = "* [CONFIGURED]" if is_configured else " "
                print(f"    {marker:14} {m}")

        if success:
            print(f"  STATUS:  OK (HTTP {status})")
            print(f"  LATENCY: {latency_ms} ms")
            print(f"  MODELS:  Verified '{cfg.model}' present among {len(available_models)} available models")
        else:
            has_error = True
            print(f"  STATUS:  FAIL (HTTP {status})")
            if latency_ms > 0:
                print(f"  LATENCY: {latency_ms} ms")
            sanitized_err = _sanitize_message(error_detail, keys_to_scrub)
            print(f"  ERROR:   {sanitized_err}")

            if available_models:
                closest = difflib.get_close_matches(cfg.model, available_models, n=5, cutoff=0.2)
                if not closest:
                    closest = available_models[:5]
                print(f"  CLOSEST AVAILABLE MODEL IDs:")
                for candidate in closest:
                    print(f"    - {candidate}")
            else:
                print("  (No model list could be retrieved from provider endpoint)")

    print("\n" + "=" * 70)
    if active_providers_checked == 0:
        print("RESULT: No active providers with API keys were tested.")
        print("To test live providers, set GROQ_API_KEY, NVIDIA_API_KEY, or GEMINI_API_KEY.")
        return 0

    if has_error:
        print("RESULT: One or more configured providers FAILED check.")
        return 1
    else:
        print("RESULT: All checked providers PASSED verification.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
