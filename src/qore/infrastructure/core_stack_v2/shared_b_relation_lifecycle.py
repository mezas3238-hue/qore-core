"""Architect-B relational lifecycle and lead/lag observability.

This module records descriptive, point-in-time relation lifecycle evidence.
It does not discover profitable relations, infer causation, generate signals,
or grant Trader/Risk/Execution/capital authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final

_MAX_BPS: Final = 10_000


class SharedBRelationLifecycleState(StrEnum):
    UNKNOWN = "UNKNOWN"
    INSUFFICIENT = "INSUFFICIENT"
    EMERGING = "EMERGING"
    STABLE = "STABLE"
    STRENGTHENING = "STRENGTHENING"
    WEAKENING = "WEAKENING"
    BREAKING = "BREAKING"
    DECOUPLED = "DECOUPLED"


class SharedBLeadLagState(StrEnum):
    UNKNOWN = "UNKNOWN"
    INSUFFICIENT = "INSUFFICIENT"
    ALIGNED_NO_LEADER = "ALIGNED_NO_LEADER"
    SOURCE_LEADS = "SOURCE_LEADS"
    TARGET_LEADS = "TARGET_LEADS"
    LEADER_REVERSAL = "LEADER_REVERSAL"


class SharedBRelationComparability(StrEnum):
    COMPARABLE = "COMPARABLE"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class SharedBRelationObservation:
    relation_id: str
    source_instrument_key: str
    target_instrument_key: str
    horizon: str
    observed_at: datetime
    evidence_cutoff_at: datetime
    comparability: SharedBRelationComparability
    strength_bps: int | None
    confidence_bps: int
    stability_bps: int | None
    lag_ms: int | None
    leader_instrument_key: str | None
    relationship_half_life_ms: int | None
    provenance_refs: tuple[str, ...]
    target_or_outcome_used: bool = False
    future_market_used: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "relation_id",
            "source_instrument_key",
            "target_instrument_key",
            "horizon",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if self.source_instrument_key == self.target_instrument_key:
            raise ValueError("relation endpoints must differ")
        for name in ("observed_at", "evidence_cutoff_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.evidence_cutoff_at > self.observed_at:
            raise ValueError("future relation evidence is forbidden")
        if not isinstance(self.comparability, SharedBRelationComparability):
            raise ValueError("comparability must be SharedBRelationComparability")
        if not 0 <= self.confidence_bps <= _MAX_BPS:
            raise ValueError("confidence_bps outside 0..10000")
        for name in ("strength_bps", "stability_bps"):
            value = getattr(self, name)
            if value is not None and (
                type(value) is not int or not 0 <= value <= _MAX_BPS
            ):
                raise ValueError(f"{name} outside 0..10000")
        if self.lag_ms is not None and (
            type(self.lag_ms) is not int or self.lag_ms < 0
        ):
            raise ValueError("lag_ms must be non-negative int")
        if self.relationship_half_life_ms is not None and (
            type(self.relationship_half_life_ms) is not int
            or self.relationship_half_life_ms <= 0
        ):
            raise ValueError("relationship_half_life_ms must be positive int")
        if self.leader_instrument_key is not None and self.leader_instrument_key not in {
            self.source_instrument_key,
            self.target_instrument_key,
        }:
            raise ValueError("leader must be one relation endpoint")
        if (self.lag_ms is None) != (self.leader_instrument_key is None):
            raise ValueError("lead/lag requires both leader and lag or neither")
        if self.comparability is not SharedBRelationComparability.COMPARABLE:
            if any(
                value is not None
                for value in (
                    self.strength_bps,
                    self.stability_bps,
                    self.lag_ms,
                    self.leader_instrument_key,
                    self.relationship_half_life_ms,
                )
            ):
                raise ValueError(
                    "non-comparable relation cannot carry relation metrics"
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
            or self.future_market_used
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
            or self.capital_authority
        ):
            raise ValueError("relation observation carries forbidden authority")


@dataclass(frozen=True, slots=True)
class SharedBRelationLifecyclePoint:
    relation_id: str
    observed_at: datetime
    evidence_cutoff_at: datetime
    state: SharedBRelationLifecycleState
    lead_lag_state: SharedBLeadLagState
    leader_instrument_key: str | None
    lag_ms: int | None
    relation_age_ms: int | None
    relationship_half_life_ms: int | None
    strength_bps: int | None
    stability_bps: int | None
    confidence_bps: int
    transition_reason_codes: tuple[str, ...]
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        if (
            self.evidence_cutoff_at.tzinfo is None
            or self.evidence_cutoff_at.utcoffset() is None
        ):
            raise ValueError("evidence_cutoff_at must be timezone-aware")
        if self.evidence_cutoff_at > self.observed_at:
            raise ValueError("future lifecycle evidence is forbidden")
        if self.relation_age_ms is not None and self.relation_age_ms < 0:
            raise ValueError("relation_age_ms cannot be negative")
        if (
            not self.transition_reason_codes
            or self.transition_reason_codes
            != tuple(sorted(set(self.transition_reason_codes)))
        ):
            raise ValueError(
                "transition reason codes must be non-empty and canonical"
            )
        if (
            not self.provenance_refs
            or self.provenance_refs != tuple(sorted(set(self.provenance_refs)))
        ):
            raise ValueError("lifecycle provenance must be non-empty and canonical")


@dataclass(frozen=True, slots=True)
class SharedBRelationLifecycleTrack:
    relation_id: str
    source_instrument_key: str
    target_instrument_key: str
    horizon: str
    points: tuple[SharedBRelationLifecyclePoint, ...]
    target_or_outcome_used: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if not self.relation_id.strip() or not self.horizon.strip():
            raise ValueError("track identity/horizon must be explicit")
        if self.source_instrument_key == self.target_instrument_key:
            raise ValueError("track endpoints must differ")
        if not self.points:
            raise ValueError("lifecycle track requires points")
        if any(point.relation_id != self.relation_id for point in self.points):
            raise ValueError("lifecycle point relation identity drift")
        times = tuple(point.observed_at for point in self.points)
        if times != tuple(sorted(times)) or len(times) != len(set(times)):
            raise ValueError("lifecycle points must be strictly chronological")
        if (
            self.target_or_outcome_used
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
            or self.capital_authority
        ):
            raise ValueError("relation lifecycle carries forbidden authority")

    def fingerprint(self) -> str:
        payload = {
            "relation_id": self.relation_id,
            "source": self.source_instrument_key,
            "target": self.target_instrument_key,
            "horizon": self.horizon,
            "points": [
                {
                    "observed_at": point.observed_at.astimezone(UTC).isoformat(
                        timespec="microseconds"
                    ),
                    "evidence_cutoff_at": point.evidence_cutoff_at.astimezone(
                        UTC
                    ).isoformat(timespec="microseconds"),
                    "state": point.state.value,
                    "lead_lag_state": point.lead_lag_state.value,
                    "leader": point.leader_instrument_key,
                    "lag_ms": point.lag_ms,
                    "relation_age_ms": point.relation_age_ms,
                    "relationship_half_life_ms": point.relationship_half_life_ms,
                    "strength_bps": point.strength_bps,
                    "stability_bps": point.stability_bps,
                    "confidence_bps": point.confidence_bps,
                    "reason_codes": point.transition_reason_codes,
                    "provenance_refs": point.provenance_refs,
                }
                for point in self.points
            ],
        }
        return hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest()


def _lifecycle_state(
    current: SharedBRelationObservation,
    previous: SharedBRelationLifecyclePoint | None,
) -> tuple[SharedBRelationLifecycleState, tuple[str, ...]]:
    if current.comparability is SharedBRelationComparability.NOT_COMPARABLE:
        return SharedBRelationLifecycleState.INSUFFICIENT, (
            "MARKETS_NOT_COMPARABLE",
        )
    if current.comparability is SharedBRelationComparability.INSUFFICIENT:
        return SharedBRelationLifecycleState.INSUFFICIENT, (
            "COMPARABILITY_INSUFFICIENT",
        )
    if current.strength_bps is None or current.stability_bps is None:
        return SharedBRelationLifecycleState.INSUFFICIENT, (
            "RELATION_METRICS_INSUFFICIENT",
        )
    if current.confidence_bps < 5_000:
        return SharedBRelationLifecycleState.UNKNOWN, (
            "RELATION_CONFIDENCE_LOW",
        )

    strength = current.strength_bps
    stability = current.stability_bps
    if strength < 1_500:
        state = SharedBRelationLifecycleState.DECOUPLED
        reason = "RELATION_STRENGTH_MINIMAL"
    elif stability < 2_500:
        state = SharedBRelationLifecycleState.BREAKING
        reason = "RELATION_STABILITY_COLLAPSED"
    elif previous is None or previous.strength_bps is None:
        state = SharedBRelationLifecycleState.EMERGING
        reason = "FIRST_COMPARABLE_RELATION_OBSERVATION"
    else:
        delta = strength - previous.strength_bps
        if delta >= 1_000:
            state = SharedBRelationLifecycleState.STRENGTHENING
            reason = "RELATION_STRENGTH_INCREASED"
        elif delta <= -1_000:
            state = SharedBRelationLifecycleState.WEAKENING
            reason = "RELATION_STRENGTH_DECREASED"
        else:
            state = SharedBRelationLifecycleState.STABLE
            reason = "RELATION_WITHIN_STABILITY_BAND"
    return state, (reason,)


def _lead_lag_state(
    current: SharedBRelationObservation,
    previous: SharedBRelationLifecyclePoint | None,
) -> tuple[SharedBLeadLagState, tuple[str, ...]]:
    if current.comparability is not SharedBRelationComparability.COMPARABLE:
        return SharedBLeadLagState.INSUFFICIENT, ("LEAD_LAG_NOT_COMPARABLE",)
    if current.leader_instrument_key is None or current.lag_ms is None:
        return SharedBLeadLagState.ALIGNED_NO_LEADER, ("NO_STABLE_LEADER_OBSERVED",)
    if (
        previous is not None
        and previous.leader_instrument_key is not None
        and previous.leader_instrument_key != current.leader_instrument_key
    ):
        return SharedBLeadLagState.LEADER_REVERSAL, ("LEADER_IDENTITY_CHANGED",)
    if current.leader_instrument_key == current.source_instrument_key:
        return SharedBLeadLagState.SOURCE_LEADS, ("SOURCE_TEMPORALLY_PRECEDES_TARGET",)
    return SharedBLeadLagState.TARGET_LEADS, ("TARGET_TEMPORALLY_PRECEDES_SOURCE",)


def append_relation_observation(
    *,
    observation: SharedBRelationObservation,
    previous_track: SharedBRelationLifecycleTrack | None = None,
) -> SharedBRelationLifecycleTrack:
    """Append one point-in-time observation without hindsight rewriting."""

    previous_point: SharedBRelationLifecyclePoint | None = None
    relation_started_at = observation.observed_at
    points: tuple[SharedBRelationLifecyclePoint, ...] = ()

    if previous_track is not None:
        if (
            previous_track.relation_id != observation.relation_id
            or previous_track.source_instrument_key
            != observation.source_instrument_key
            or previous_track.target_instrument_key
            != observation.target_instrument_key
            or previous_track.horizon != observation.horizon
        ):
            raise ValueError("relation lifecycle identity drift")
        previous_point = previous_track.points[-1]
        if observation.observed_at <= previous_point.observed_at:
            raise ValueError("relation lifecycle cannot append past/future-overlap")
        relation_started_at = previous_track.points[0].observed_at
        points = previous_track.points

    lifecycle, lifecycle_reasons = _lifecycle_state(
        observation,
        previous_point,
    )
    lead_lag, lead_reasons = _lead_lag_state(observation, previous_point)
    age_ms = int(
        (observation.observed_at - relation_started_at).total_seconds() * 1000
    )

    point = SharedBRelationLifecyclePoint(
        relation_id=observation.relation_id,
        observed_at=observation.observed_at,
        evidence_cutoff_at=observation.evidence_cutoff_at,
        state=lifecycle,
        lead_lag_state=lead_lag,
        leader_instrument_key=observation.leader_instrument_key,
        lag_ms=observation.lag_ms,
        relation_age_ms=age_ms,
        relationship_half_life_ms=observation.relationship_half_life_ms,
        strength_bps=observation.strength_bps,
        stability_bps=observation.stability_bps,
        confidence_bps=observation.confidence_bps,
        transition_reason_codes=tuple(
            sorted(set(lifecycle_reasons + lead_reasons))
        ),
        provenance_refs=observation.provenance_refs,
    )
    return SharedBRelationLifecycleTrack(
        relation_id=observation.relation_id,
        source_instrument_key=observation.source_instrument_key,
        target_instrument_key=observation.target_instrument_key,
        horizon=observation.horizon,
        points=points + (point,),
    )
