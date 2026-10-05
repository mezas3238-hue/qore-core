"""Architect-B generalized cross-asset structural-divergence inputs.

This module creates descriptive, point-in-time structural comparison inputs.
It never declares SMT/divergence, causation, opportunity, BUY/SELL, trade
priority or capital priority. Non-comparable markets fail closed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class SharedBStructuralDirection(StrEnum):
    UP = "UP"
    DOWN = "DOWN"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


class SharedBStructuralInputStatus(StrEnum):
    COMPARABLE = "COMPARABLE"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class SharedBStructuralObservation:
    observation_id: str
    canonical_observation_key: str
    asset_family: str
    horizon: str
    observed_at: datetime
    evidence_cutoff_at: datetime
    direction: SharedBStructuralDirection
    relative_position_bps: int | None
    displacement_bps: int | None
    volatility_bps: int | None
    canonical_identity_verified: bool
    market_state_known: bool
    market_open: bool | None
    freshness_passed: bool
    data_health_passed: bool
    provenance_refs: tuple[str, ...]
    target_or_outcome_used: bool = False
    pnl_used: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "observation_id",
            "canonical_observation_key",
            "asset_family",
            "horizon",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        for name in ("observed_at", "evidence_cutoff_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.evidence_cutoff_at > self.observed_at:
            raise ValueError("future structural evidence is forbidden")
        if not isinstance(self.direction, SharedBStructuralDirection):
            raise ValueError("direction invalid")
        for name in (
            "relative_position_bps",
            "displacement_bps",
            "volatility_bps",
        ):
            value = getattr(self, name)
            if value is not None and (
                type(value) is not int or not 0 <= value <= 10_000
            ):
                raise ValueError(f"{name} outside 0..10000")
        if not self.market_state_known and self.market_open is not None:
            raise ValueError(
                "unknown market state cannot carry market_open value"
            )
        if self.market_state_known and type(self.market_open) is not bool:
            raise ValueError(
                "known market state requires boolean market_open"
            )
        if (
            not self.provenance_refs
            or self.provenance_refs != tuple(sorted(set(self.provenance_refs)))
        ):
            raise ValueError(
                "provenance_refs must be non-empty, unique and canonical"
            )
        if (
            self.target_or_outcome_used
            or self.pnl_used
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
            or self.capital_authority
        ):
            raise ValueError(
                "structural observation carries forbidden evidence/authority"
            )


@dataclass(frozen=True, slots=True)
class SharedBCrossAssetStructuralInput:
    comparison_id: str
    source: SharedBStructuralObservation
    target: SharedBStructuralObservation
    as_of: datetime
    evidence_cutoff_at: datetime
    status: SharedBStructuralInputStatus
    temporal_skew_ms: int | None
    source_direction: SharedBStructuralDirection | None
    target_direction: SharedBStructuralDirection | None
    source_relative_position_bps: int | None
    target_relative_position_bps: int | None
    reason_codes: tuple[str, ...]
    divergence_declared: bool = False
    causality_declared: bool = False
    opportunity_declared: bool = False
    trade_priority_authority: bool = False
    capital_priority_authority: bool = False

    def __post_init__(self) -> None:
        if not self.comparison_id.strip():
            raise ValueError("comparison_id must be non-empty")
        if self.source.observation_id == self.target.observation_id:
            raise ValueError("structural comparison requires two observations")
        if self.source.horizon != self.target.horizon:
            raise ValueError("structural comparison horizon mismatch")
        for name in ("as_of", "evidence_cutoff_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.evidence_cutoff_at > self.as_of:
            raise ValueError("comparison evidence cutoff is future")
        if self.status is not SharedBStructuralInputStatus.COMPARABLE:
            if any(
                value is not None
                for value in (
                    self.temporal_skew_ms,
                    self.source_direction,
                    self.target_direction,
                    self.source_relative_position_bps,
                    self.target_relative_position_bps,
                )
            ):
                raise ValueError(
                    "non-comparable input cannot expose comparison metrics"
                )
        if (
            not self.reason_codes
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
        ):
            raise ValueError("reason_codes must be non-empty and canonical")
        if (
            self.divergence_declared
            or self.causality_declared
            or self.opportunity_declared
            or self.trade_priority_authority
            or self.capital_priority_authority
        ):
            raise ValueError(
                "B structural input cannot make cognitive/economic claims"
            )

    def fingerprint(self) -> str:
        payload = {
            "comparison_id": self.comparison_id,
            "source_id": self.source.observation_id,
            "target_id": self.target.observation_id,
            "source_key": self.source.canonical_observation_key,
            "target_key": self.target.canonical_observation_key,
            "horizon": self.source.horizon,
            "as_of": self.as_of.astimezone(UTC).isoformat(
                timespec="microseconds"
            ),
            "evidence_cutoff_at": self.evidence_cutoff_at.astimezone(
                UTC
            ).isoformat(timespec="microseconds"),
            "status": self.status.value,
            "temporal_skew_ms": self.temporal_skew_ms,
            "source_direction": (
                None
                if self.source_direction is None
                else self.source_direction.value
            ),
            "target_direction": (
                None
                if self.target_direction is None
                else self.target_direction.value
            ),
            "source_relative_position_bps": self.source_relative_position_bps,
            "target_relative_position_bps": self.target_relative_position_bps,
            "reason_codes": self.reason_codes,
        }
        return hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest()


def build_cross_asset_structural_input(
    *,
    comparison_id: str,
    source: SharedBStructuralObservation,
    target: SharedBStructuralObservation,
    as_of: datetime,
    maximum_temporal_skew_ms: int,
) -> SharedBCrossAssetStructuralInput:
    """Build comparison input only when causal temporal comparability is proven."""

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    if type(maximum_temporal_skew_ms) is not int or maximum_temporal_skew_ms < 0:
        raise ValueError("maximum_temporal_skew_ms must be non-negative int")
    if source.observed_at > as_of or target.observed_at > as_of:
        raise ValueError("future structural observation is forbidden at as_of")
    cutoff = max(source.evidence_cutoff_at, target.evidence_cutoff_at)
    if cutoff > as_of:
        raise ValueError("future structural evidence is forbidden at as_of")

    blockers: list[str] = []
    if not source.canonical_identity_verified:
        blockers.append("SOURCE_IDENTITY_UNVERIFIED")
    if not target.canonical_identity_verified:
        blockers.append("TARGET_IDENTITY_UNVERIFIED")
    if not source.market_state_known:
        blockers.append("SOURCE_MARKET_STATE_UNKNOWN")
    if not target.market_state_known:
        blockers.append("TARGET_MARKET_STATE_UNKNOWN")
    if source.market_state_known and source.market_open is False:
        blockers.append("SOURCE_MARKET_CLOSED")
    if target.market_state_known and target.market_open is False:
        blockers.append("TARGET_MARKET_CLOSED")
    if not source.freshness_passed:
        blockers.append("SOURCE_STALE")
    if not target.freshness_passed:
        blockers.append("TARGET_STALE")
    if not source.data_health_passed:
        blockers.append("SOURCE_DATA_HEALTH_FAILED")
    if not target.data_health_passed:
        blockers.append("TARGET_DATA_HEALTH_FAILED")
    if (
        source.direction is SharedBStructuralDirection.UNKNOWN
        or target.direction is SharedBStructuralDirection.UNKNOWN
        or source.relative_position_bps is None
        or target.relative_position_bps is None
    ):
        blockers.append("STRUCTURAL_STATE_INSUFFICIENT")

    skew_ms = abs(
        int(
            (source.observed_at - target.observed_at).total_seconds()
            * 1000
        )
    )
    if skew_ms > maximum_temporal_skew_ms:
        blockers.append("TEMPORAL_SKEW_EXCEEDS_POLICY")

    if blockers:
        not_comparable_codes = {
            "SOURCE_MARKET_CLOSED",
            "TARGET_MARKET_CLOSED",
            "SOURCE_STALE",
            "TARGET_STALE",
            "SOURCE_DATA_HEALTH_FAILED",
            "TARGET_DATA_HEALTH_FAILED",
            "TEMPORAL_SKEW_EXCEEDS_POLICY",
        }
        status = (
            SharedBStructuralInputStatus.NOT_COMPARABLE
            if not_comparable_codes.intersection(blockers)
            else SharedBStructuralInputStatus.INSUFFICIENT
        )
        return SharedBCrossAssetStructuralInput(
            comparison_id=comparison_id,
            source=source,
            target=target,
            as_of=as_of,
            evidence_cutoff_at=cutoff,
            status=status,
            temporal_skew_ms=None,
            source_direction=None,
            target_direction=None,
            source_relative_position_bps=None,
            target_relative_position_bps=None,
            reason_codes=tuple(sorted(set(blockers))),
        )

    return SharedBCrossAssetStructuralInput(
        comparison_id=comparison_id,
        source=source,
        target=target,
        as_of=as_of,
        evidence_cutoff_at=cutoff,
        status=SharedBStructuralInputStatus.COMPARABLE,
        temporal_skew_ms=skew_ms,
        source_direction=source.direction,
        target_direction=target.direction,
        source_relative_position_bps=source.relative_position_bps,
        target_relative_position_bps=target.relative_position_bps,
        reason_codes=("CAUSAL_TEMPORAL_COMPARABILITY_PASS",),
    )
