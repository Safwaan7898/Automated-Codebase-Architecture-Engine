"""Security rules suite."""

from __future__ import annotations

from diagnostics.rules.security.command_injection import CommandInjectionRule
from diagnostics.rules.security.disabled_tls import DisabledTlsVerificationRule
from diagnostics.rules.security.hardcoded_secrets import HardcodedSecretsRule
from diagnostics.rules.security.insecure_deserialization import InsecureDeserializationRule
from diagnostics.rules.security.path_traversal import PathTraversalRule
from diagnostics.rules.security.sql_injection import SqlConcatenationRule
from diagnostics.rules.security.weak_crypto import WeakCryptoRule

ALL_SECURITY_RULES = [
    SqlConcatenationRule,
    HardcodedSecretsRule,
    WeakCryptoRule,
    InsecureDeserializationRule,
    CommandInjectionRule,
    PathTraversalRule,
    DisabledTlsVerificationRule,
]

__all__ = [
    "ALL_SECURITY_RULES",
    "CommandInjectionRule",
    "DisabledTlsVerificationRule",
    "HardcodedSecretsRule",
    "InsecureDeserializationRule",
    "PathTraversalRule",
    "SqlConcatenationRule",
    "WeakCryptoRule",
]
