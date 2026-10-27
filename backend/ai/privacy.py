"""Privacy and secret redaction engine for AI prompts."""

from __future__ import annotations

import re

# Compiled regex patterns for detecting secrets
SECRET_PATTERNS = [
    # AWS Access Key ID
    (re.compile(r"(?i)\b(AKIA|ABIA|ACCA)[0-9A-Z]{16}\b"), "[REDACTED_SECRET: AWS_KEY_ID]"),
    # AWS Secret Key
    (re.compile(r"(?i)(aws_secret_access_key|aws_secret_key)\s*[:=]\s*['\"]?([a-zA-Z0-9/+=]{40})['\"]?"), r"\1='[REDACTED_SECRET: AWS_SECRET_KEY]'"),
    # Generic Private Key blocks
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"), "[REDACTED_SECRET: PRIVATE_KEY]"),
    # GitHub / GitLab / Slack personal access tokens
    (re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,255}\b"), "[REDACTED_SECRET: GITHUB_TOKEN]"),
    (re.compile(r"\bglpat-[0-9a-zA-Z\-_]{20,}\b"), "[REDACTED_SECRET: GITLAB_TOKEN]"),
    (re.compile(r"\bxox[baprs]-[0-9a-zA-Z]{10,48}\b"), "[REDACTED_SECRET: SLACK_TOKEN]"),
    # JWT tokens
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9._-]{10,}\.[A-Za-z0-9._-]{10,}\b"), "[REDACTED_SECRET: JWT_TOKEN]"),
    # Database connection strings with passwords
    (re.compile(r"(?i)(postgres|mysql|mongodb(?:\+srv)?|redis|amqp)://([^:]+):([^@]+)@"), r"\1://\2:[REDACTED_SECRET: PASSWORD]@"),
    # Generic password / secret assignments
    (re.compile(r"(?i)(password|passwd|secret|api_key|apikey|auth_token)\s*[:=]\s*['\"][^\s'\"\n]{8,}['\"]"), r"\1='[REDACTED_SECRET]'"),
]


def redact_secrets(text: str) -> str:
    """Scrub sensitive credentials, tokens, and private keys from prompt text."""
    if not text:
        return ""

    sanitized = text
    for pattern, replacement in SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    return sanitized
