"""Shared deterministic primitives for the CIBO Cognitive Superarchitecture.

This module provides the provider-neutral, fail-closed value objects and helpers
shared by every cognitive substrate lane: an explicit error hierarchy, a
deterministic sha256 fingerprint, canonical material serialization, exact-type
validators, and a bounded secret-material detector.

Architecture laws honoured here:

- deterministic canonical ordering and fingerprints;
- exact runtime types (``bool != int``, no subclass laundering);
- secret-bearing strings fail closed;
- no ambient time, RNG, network, retry, sleep, threads, or global mutable state.

This module is a *complementary* cognitive substrate. It does not re-declare any
Batch 006 epistemic-state, reasoning-mode, memory, council, or recommendation
ownership. Integration with Batch 006 happens later at the Cognitive Integration
Gate through reference/fingerprint seams only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from re import IGNORECASE, Pattern, compile
from uuid import UUID

from qore.kernel.errors import DomainError
from qore.kernel.temporal import canonical_instant, is_timezone_aware_datetime

_SHA256_HEX = compile(r"[0-9a-f]{64}")

# Bounded, deterministic secret-material patterns. These are structural markers
# that unambiguously indicate credential-like material; they are never used to
# rewrite text, only to reject it (fail closed).
_SECRET_PATTERNS: tuple[Pattern[str], ...] = (
    compile(r"-----BEGIN [A-Z ]*(?:PRIVATE KEY|SECRET|ENCRYPTED PRIVATE KEY)-----"),
    compile(r"\bsk-[A-Za-z0-9_-]{8,}"),
    compile(r"\bAKIA[0-9A-Z]{16}\b"),
    compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}", IGNORECASE),
    compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}"),
    compile(r"//[^/@\s:]+:[^/@\s]+@"),
    compile(
        r"(?i)\b(?:password|passwd|api[_-]?key|access[_-]?key|secret[_-]?key|"
        r"client[_-]?secret|private[_-]?key|credential|authorization)\s*[=:]\s*\S+"
    ),
)


class CiboCognitiveError(DomainError):
    """Base error for the CIBO Cognitive Superarchitecture substrate."""

    __slots__ = ()


class CiboCognitiveValidationError(CiboCognitiveError):
    """Explicit violation of a cognitive substrate invariant."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class CiboCognitiveFingerprint:
    """Deterministic sha256 fingerprint over canonical logical material."""

    value: str

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.value) is not str or _SHA256_HEX.fullmatch(self.value) is None:
            raise CiboCognitiveValidationError(
                "cognitive fingerprint must be an exact str of 64 lowercase hex characters"
            )

    def logical_values(self) -> tuple[str, str]:
        return ("sha256", self.value)


def require_exact_str(value: object, *, field: str) -> str:
    """Return ``value`` only when it is an exact ``str`` (no str subclass)."""
    if type(value) is not str:
        raise CiboCognitiveValidationError(
            f"{field} must be an exact str, not {type(value).__name__}"
        )
    return value


def require_exact_int(value: object, *, field: str) -> int:
    """Return ``value`` only when it is an exact ``int`` (``bool`` excluded)."""
    if type(value) is not int:
        raise CiboCognitiveValidationError(
            f"{field} must be an exact int, not {type(value).__name__}"
        )
    return value


def require_aware_datetime(value: object, *, field: str) -> datetime:
    """Return ``value`` only when it is a timezone-aware ``datetime``."""
    if type(value) is not datetime or not is_timezone_aware_datetime(value):
        raise CiboCognitiveValidationError(
            f"{field} must be a timezone-aware datetime"
        )
    return value


def canonical_material(value: object) -> str:
    """Serialize a bounded set of material to a deterministic canonical string.

    Supported material: ``None``, exact ``str``, exact ``bool``, exact ``int``,
    ``UUID``, timezone-aware ``datetime``, ``tuple``, ``frozenset``, and objects
    exposing ``logical_values()``. Anything else fails closed rather than being
    serialized ambiguously.
    """
    if value is None:
        return "null"
    if type(value) is str:
        return json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) is int:
        return str(value)
    if type(value) is UUID:
        return str(value)
    if type(value) is datetime:
        return canonical_instant(require_aware_datetime(value, field="fingerprint material"))
    if type(value) is tuple:
        return "[" + ",".join(canonical_material(item) for item in value) + "]"
    if type(value) is frozenset:
        return "{" + ",".join(sorted(canonical_material(item) for item in value)) + "}"
    logical = getattr(value, "logical_values", None)
    if callable(logical):
        return canonical_material(logical())
    raise CiboCognitiveValidationError(
        f"unsupported canonical material of type {type(value).__name__}"
    )


def fingerprint_material(*parts: object) -> CiboCognitiveFingerprint:
    """Compute a deterministic sha256 fingerprint over canonical material."""
    canonical = "\x1f".join(canonical_material(part) for part in parts)
    return CiboCognitiveFingerprint(sha256(canonical.encode("utf-8")).hexdigest())


def contains_secret_material(text: str) -> bool:
    """Return whether ``text`` carries structural secret-bearing material."""
    require_exact_str(text, field="secret detection input")
    return any(pattern.search(text) is not None for pattern in _SECRET_PATTERNS)
