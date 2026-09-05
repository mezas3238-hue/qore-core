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
from datetime import UTC, datetime
from hashlib import sha256
from re import compile
from uuid import UUID

from qore.kernel.errors import DomainError
from qore.kernel.temporal import canonical_instant, is_timezone_aware_datetime
from qore.modules.cibo.cognitive_contracts import (
    contains_secret_material as contains_secret_material,
)

_SHA256_HEX = compile(r"[0-9a-f]{64}")

# Provider-neutral identity/version tokens: bounded allowlist of letters, digits,
# dot, underscore and hyphen. Never a free-text prose field.
_SUBJECT_TOKEN = compile(r"[0-9A-Za-z._-]{1,128}")


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


def utc_instant(value: object, *, field: str = "instant") -> datetime:
    """Return the UTC-normalized instant of a timezone-aware ``datetime``.

    ``astimezone(UTC)`` resolves DST fold=0/fold=1 to distinct UTC instants, so
    every material datetime identity/dedup/order/no-postdate comparison must use
    this helper (or ``canonical_instant``) rather than fold-blind wall-clock
    ``<``/``>``/``==``/``-`` operators.
    """
    return require_aware_datetime(value, field=field).astimezone(UTC)


def canonical_material(value: object) -> str:
    """Serialize a bounded set of material to a deterministic canonical string.

    Supported material is a CLOSED allowlist of exact scalar types: ``None``,
    exact ``str``, exact ``bool``, exact ``int``, ``UUID``, timezone-aware
    ``datetime``, ``tuple``, and ``frozenset``. Strings are checked for
    secret-bearing material (fail closed). Any other type — including any
    duck-typed object exposing ``logical_values()`` — is rejected, so a hostile,
    nondeterministic, or secret-bearing object can never inject state or secrets
    into a fingerprint. Value objects must project themselves to scalars via
    their own ``logical_values()`` before being fingerprinted.
    """
    if value is None:
        return "null"
    if type(value) is str:
        if contains_secret_material(value):
            raise CiboCognitiveValidationError(
                "canonical material must not carry secret-bearing material"
            )
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
    raise CiboCognitiveValidationError(
        f"unsupported canonical material of type {type(value).__name__}"
    )


def fingerprint_material(*parts: object) -> CiboCognitiveFingerprint:
    """Compute a deterministic sha256 fingerprint over canonical material."""
    canonical = "\x1f".join(canonical_material(part) for part in parts)
    return CiboCognitiveFingerprint(sha256(canonical.encode("utf-8")).hexdigest())


@dataclass(frozen=True, slots=True)
class TraderSubject:
    """Exact provider-neutral cognitive subject identity for one Trader version.

    The fingerprint is deterministically derived from ``(trader_id,
    trader_version)``, so the same identity under a different version yields a
    different fingerprint and cannot be laundered as the same cognitive subject.
    This value object carries no order, account, credential, execution, Risk,
    promotion, or Production authority field.
    """

    trader_id: str
    trader_version: str
    fingerprint: CiboCognitiveFingerprint

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        trader_id = require_exact_str(self.trader_id, field="trader subject id")
        trader_version = require_exact_str(
            self.trader_version, field="trader subject version"
        )
        if _SUBJECT_TOKEN.fullmatch(trader_id) is None:
            raise CiboCognitiveValidationError(
                "trader subject id must be a non-blank token of letters, digits, "
                "dot, underscore or hyphen"
            )
        if _SUBJECT_TOKEN.fullmatch(trader_version) is None:
            raise CiboCognitiveValidationError(
                "trader subject version must be a non-blank token of letters, "
                "digits, dot, underscore or hyphen"
            )
        if contains_secret_material(trader_id) or contains_secret_material(trader_version):
            raise CiboCognitiveValidationError(
                "trader subject identity must not carry secret-bearing material"
            )
        if type(self.fingerprint) is not CiboCognitiveFingerprint:
            raise CiboCognitiveValidationError(
                "trader subject fingerprint must be a CiboCognitiveFingerprint"
            )
        self.fingerprint.revalidate()
        expected = fingerprint_material((trader_id, trader_version))
        if self.fingerprint != expected:
            raise CiboCognitiveValidationError(
                "trader subject fingerprint does not match its identity/version"
            )

    def logical_values(self) -> tuple[str, str, str]:
        return (self.trader_id, self.trader_version, self.fingerprint.value)

    def sort_key(self) -> tuple[str, str]:
        return (self.trader_id, self.trader_version)
