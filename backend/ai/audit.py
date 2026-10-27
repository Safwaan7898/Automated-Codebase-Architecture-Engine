"""AI call logging into ArchLens audit trail."""

from __future__ import annotations

import logging
from typing import Any
from .models import AICallLog

logger = logging.getLogger("archlens.ai.audit")


def log_ai_invocation(
    feature: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    success: bool,
    error: str | None = None,
    cached: bool = False,
    user_id: str = "system",
    user_email: str = "system@archlens.internal",
    user_role: str = "SYSTEM",
) -> AICallLog:
    """Log an AI invocation in the system audit trail without storing raw code/prompts."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    call_log = AICallLog(
        feature=feature,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        cost_usd=cost_usd,
        success=success,
        error=error,
        timestamp=now,
        cached=cached,
    )

    # 1. Log structured telemetry safely
    logger.info(
        "AI Invocation: feature=%s provider=%s tokens=%d cost=$%.6f success=%s cached=%s",
        feature,
        provider,
        call_log.total_tokens,
        cost_usd,
        success,
        cached,
    )

    # 2. Record to auth/store audit log if available
    try:
        from app.auth.store import AuthStore
        store = AuthStore()
        store.add_audit_log(
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            action=f"ai_call:{feature}",
            resource_type="ai_engine",
            resource_id=f"{provider}:{model}",
            details={
                "feature": feature,
                "provider": provider,
                "model": model,
                "tokens": call_log.total_tokens,
                "cost_usd": cost_usd,
                "success": success,
                "cached": cached,
                "error": error,
            },
        )
    except Exception as exc:
        logger.debug("Could not record AI call to DB audit trail: %s", exc)

    return call_log
