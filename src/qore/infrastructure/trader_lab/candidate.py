"""Trader Lab candidate identity and exact binding contracts.

The Trader Lab is a governed qualification component. It binds one exact Trader
candidate to the existing frozen research strategy/run/config identity and
derives an immutable fingerprint that invalidates any prior eligibility chain
whenever candidate identity, version, or configuration changes.

This module contains no concrete Trader methodology, no execution authority, and
no Production inference.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from re import fullmatch
from uuid import UUID

from qore.infrastructure.research_strategy_freeze import ResearchRunStrategyBinding
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class TraderLabError(InfrastructureError):
    """Root error for the Trader Lab governed qualification component."""

    __slots__ = ()


class TraderLabValidationError(TraderLabError):
    """Violation of a Trader Lab invariant."""

    __slots__ = ()


def _validate_token(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._/+:-]*",
        value,
    ) is None:
        raise TraderLabValidationError(f"{field_name} must use canonical token syntax")


def _validate_sha256(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or fullmatch(r"[0-9a-f]{64}", value) is None:
        raise TraderLabValidationError(
            f"{field_name} must be 64 lowercase hex characters"
        )


@dataclass(frozen=True, slots=True)
class TraderLabCandidateId:
    """Opaque immutable identity of one Trader Lab candidate (e.g. VT-01..VT-31)."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise TraderLabValidationError("candidate id must be a UUID")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class TraderLabCandidateVersion:
    """Explicit immutable candidate version token.

    A new version produces a new fingerprint and therefore a new eligibility
    chain; a suspended/degraded/rejected candidate can only resume through a new
    version, never by mutating the old chain.
    """

    value: str

    def __post_init__(self) -> None:
        _validate_token(self.value, field_name="candidate version")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class TraderLabCandidateFingerprint:
    """Canonical SHA-256 digest of the complete candidate binding."""

    value: str

    def __post_init__(self) -> None:
        _validate_sha256(self.value, field_name="candidate fingerprint")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def compute_trader_lab_candidate_fingerprint(
    *,
    candidate_id: TraderLabCandidateId,
    version: TraderLabCandidateVersion,
    strategy_binding: ResearchRunStrategyBinding,
) -> TraderLabCandidateFingerprint:
    """Hash exact candidate identity, version, and frozen strategy configuration."""

    if not isinstance(candidate_id, TraderLabCandidateId):
        raise TraderLabValidationError("candidate_id must be TraderLabCandidateId")
    if not isinstance(version, TraderLabCandidateVersion):
        raise TraderLabValidationError("version must be TraderLabCandidateVersion")
    if not isinstance(strategy_binding, ResearchRunStrategyBinding):
        raise TraderLabValidationError(
            "strategy_binding must be ResearchRunStrategyBinding"
        )
    canonical = {
        "schema": "qore.trader_lab.candidate.v1",
        "candidate_id": str(candidate_id.value),
        "version": version.value,
        "strategy_binding_fingerprint": strategy_binding.binding_fingerprint.value,
        "strategy_content_digest": strategy_binding.manifest.content_digest.value,
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return TraderLabCandidateFingerprint(sha256(encoded).hexdigest())


@dataclass(frozen=True, slots=True)
class TraderLabCandidateBinding:
    """Exact Trader candidate identity/version/configuration/fingerprint binding.

    The configuration axis is the existing ``ResearchRunStrategyBinding``, which
    already proves exact frozen strategy content bound to one research run. The
    Lab adds candidate identity and a re-qualification version on top without
    reimplementing any freeze, replay, or run machinery.
    """

    candidate_id: TraderLabCandidateId
    version: TraderLabCandidateVersion
    strategy_binding: ResearchRunStrategyBinding
    fingerprint: TraderLabCandidateFingerprint

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, TraderLabCandidateId):
            raise TraderLabValidationError("candidate_id must be TraderLabCandidateId")
        if not isinstance(self.version, TraderLabCandidateVersion):
            raise TraderLabValidationError("version must be TraderLabCandidateVersion")
        if not isinstance(self.strategy_binding, ResearchRunStrategyBinding):
            raise TraderLabValidationError(
                "strategy_binding must be ResearchRunStrategyBinding"
            )
        if not isinstance(self.fingerprint, TraderLabCandidateFingerprint):
            raise TraderLabValidationError(
                "fingerprint must be TraderLabCandidateFingerprint"
            )
        expected = compute_trader_lab_candidate_fingerprint(
            candidate_id=self.candidate_id,
            version=self.version,
            strategy_binding=self.strategy_binding,
        )
        if self.fingerprint != expected:
            raise TraderLabValidationError(
                "candidate fingerprint must match the exact binding"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.candidate_id.logical_values(),
            self.version.logical_values(),
            self.strategy_binding.logical_values(),
            self.fingerprint.logical_values(),
        )


def build_trader_lab_candidate_binding(
    *,
    candidate_id: TraderLabCandidateId,
    version: TraderLabCandidateVersion,
    strategy_binding: ResearchRunStrategyBinding,
) -> Result[TraderLabCandidateBinding, TraderLabError]:
    """Build an exact candidate binding without executing or evaluating anything."""

    try:
        fingerprint = compute_trader_lab_candidate_fingerprint(
            candidate_id=candidate_id,
            version=version,
            strategy_binding=strategy_binding,
        )
        return Success(
            TraderLabCandidateBinding(
                candidate_id=candidate_id,
                version=version,
                strategy_binding=strategy_binding,
                fingerprint=fingerprint,
            )
        )
    except TraderLabError as error:
        return Failure(error)
