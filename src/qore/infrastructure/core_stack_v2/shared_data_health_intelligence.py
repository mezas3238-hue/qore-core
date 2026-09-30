"""Shared data-health and information-freshness cognition.

Deterministic safety layer that distinguishes market absence from data failure.
It grants no Trader, CIBO, Risk or Execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SharedDataHealthState(StrEnum):
    HEALTHY = "HEALTHY"
    MARKET_CLOSED = "MARKET_CLOSED"
    MISSING = "MISSING"
    STALE_UNEXPECTED = "STALE_UNEXPECTED"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    FUTURE_EVIDENCE = "FUTURE_EVIDENCE"
    DUPLICATE = "DUPLICATE"
    ROLL_AMBIGUITY = "ROLL_AMBIGUITY"
    IDENTITY_AMBIGUITY = "IDENTITY_AMBIGUITY"
    PROVIDER_ANOMALY = "PROVIDER_ANOMALY"
    INSUFFICIENT = "INSUFFICIENT"


class SharedFreshnessState(StrEnum):
    FRESH = "FRESH"
    AGING = "AGING"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    CLOSED_MARKET_AGING = "CLOSED_MARKET_AGING"
    INSUFFICIENT = "INSUFFICIENT"


class SharedDataChangeInterpretation(StrEnum):
    MARKET_OBSERVABLE = "MARKET_OBSERVABLE"
    EXPECTED_MARKET_CLOSED_ABSENCE = "EXPECTED_MARKET_CLOSED_ABSENCE"
    DATA_FEED_CHANGE = "DATA_FEED_CHANGE"
    IDENTITY_OR_ROLL_UNCERTAINTY = "IDENTITY_OR_ROLL_UNCERTAINTY"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class SharedDataHealthObservation:
    instrument_key: str
    observed_at: datetime | None
    available_at: datetime | None
    decision_time: datetime
    previous_observed_at: datetime | None
    expected_cadence_ms: int
    validity_horizon_ms: int
    decay_horizon_ms: int
    market_open: bool
    missing: bool
    duplicate: bool
    sequence_monotonic: bool
    canonical_identity_verified: bool
    roll_identity_unambiguous: bool
    provider_healthy: bool
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.instrument_key.strip():
            raise ValueError("instrument_key must be non-empty")
        for name in ("decision_time",):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        for name in ("observed_at", "available_at", "previous_observed_at"):
            value = getattr(self, name)
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValueError(f"{name} must be timezone-aware when present")
        for name in (
            "expected_cadence_ms",
            "validity_horizon_ms",
            "decay_horizon_ms",
        ):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be positive int")
        if not (
            self.expected_cadence_ms
            <= self.validity_horizon_ms
            <= self.decay_horizon_ms
        ):
            raise ValueError(
                "expected cadence <= validity horizon <= decay horizon required"
            )
        if (
            not self.provenance_refs
            or self.provenance_refs != tuple(sorted(set(self.provenance_refs)))
        ):
            raise ValueError("provenance_refs must be non-empty, unique and canonical")


@dataclass(frozen=True, slots=True)
class SharedDataHealthAssessment:
    instrument_key: str
    state: SharedDataHealthState
    freshness: SharedFreshnessState
    interpretation: SharedDataChangeInterpretation
    evidence_age_ms: int | None
    new_market_change_inference_allowed: bool
    historical_context_usable: bool
    uncertainty_floor_bps: int
    reason_codes: tuple[str, ...]
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.evidence_age_ms is not None and self.evidence_age_ms < 0:
            raise ValueError("evidence_age_ms cannot be negative")
        if not 0 <= self.uncertainty_floor_bps <= 10_000:
            raise ValueError("uncertainty_floor_bps must be within 0..10000")
        if not self.reason_codes:
            raise ValueError("data-health assessment requires reason codes")
        if (
            self.execution_authority
            or self.risk_authority
            or self.sizing_authority
            or self.capital_authority
        ):
            raise ValueError("data-health cognition carries no downstream authority")


def _age_ms(observation: SharedDataHealthObservation) -> int | None:
    if observation.available_at is None:
        return None
    return int(
        (observation.decision_time - observation.available_at).total_seconds()
        * 1000
    )


def _freshness(
    *,
    age_ms: int | None,
    observation: SharedDataHealthObservation,
) -> SharedFreshnessState:
    if age_ms is None:
        return SharedFreshnessState.INSUFFICIENT
    if not observation.market_open and age_ms > observation.expected_cadence_ms:
        if age_ms <= observation.decay_horizon_ms:
            return SharedFreshnessState.CLOSED_MARKET_AGING
        return SharedFreshnessState.EXPIRED
    if age_ms <= observation.expected_cadence_ms:
        return SharedFreshnessState.FRESH
    if age_ms <= observation.validity_horizon_ms:
        return SharedFreshnessState.AGING
    if age_ms <= observation.decay_horizon_ms:
        return SharedFreshnessState.STALE
    return SharedFreshnessState.EXPIRED


def assess_shared_data_health(
    observation: SharedDataHealthObservation,
) -> SharedDataHealthAssessment:
    """Classify data health strictly from evidence available at decision time."""

    age_ms = _age_ms(observation)
    freshness = _freshness(age_ms=age_ms, observation=observation)

    state: SharedDataHealthState
    interpretation: SharedDataChangeInterpretation
    reasons: list[str]
    new_inference = False
    context_usable = False
    uncertainty = 10_000

    if not observation.canonical_identity_verified:
        state = SharedDataHealthState.IDENTITY_AMBIGUITY
        interpretation = SharedDataChangeInterpretation.IDENTITY_OR_ROLL_UNCERTAINTY
        reasons = ["CANONICAL_IDENTITY_UNVERIFIED"]
    elif not observation.roll_identity_unambiguous:
        state = SharedDataHealthState.ROLL_AMBIGUITY
        interpretation = SharedDataChangeInterpretation.IDENTITY_OR_ROLL_UNCERTAINTY
        reasons = ["ROLL_OR_CONTRACT_IDENTITY_AMBIGUOUS"]
    elif not observation.provider_healthy:
        state = SharedDataHealthState.PROVIDER_ANOMALY
        interpretation = SharedDataChangeInterpretation.DATA_FEED_CHANGE
        reasons = ["PROVIDER_HEALTH_ANOMALY"]
    elif observation.missing or observation.available_at is None or observation.observed_at is None:
        if not observation.market_open:
            state = SharedDataHealthState.MARKET_CLOSED
            interpretation = (
                SharedDataChangeInterpretation.EXPECTED_MARKET_CLOSED_ABSENCE
            )
            reasons = ["MARKET_CLOSED_NO_NEW_OBSERVATION"]
            uncertainty = 5_000
        else:
            state = SharedDataHealthState.MISSING
            interpretation = SharedDataChangeInterpretation.DATA_FEED_CHANGE
            reasons = ["EXPECTED_OPEN_MARKET_DATA_MISSING"]
    elif (
        observation.observed_at > observation.decision_time
        or observation.available_at > observation.decision_time
    ):
        state = SharedDataHealthState.FUTURE_EVIDENCE
        interpretation = SharedDataChangeInterpretation.DATA_FEED_CHANGE
        reasons = ["FUTURE_EVIDENCE_REJECTED"]
    elif observation.duplicate:
        state = SharedDataHealthState.DUPLICATE
        interpretation = SharedDataChangeInterpretation.DATA_FEED_CHANGE
        reasons = ["DUPLICATE_OBSERVATION"]
    elif (
        not observation.sequence_monotonic
        or (
            observation.previous_observed_at is not None
            and observation.observed_at <= observation.previous_observed_at
        )
    ):
        state = SharedDataHealthState.OUT_OF_ORDER
        interpretation = SharedDataChangeInterpretation.DATA_FEED_CHANGE
        reasons = ["OUT_OF_ORDER_OBSERVATION"]
    elif not observation.market_open:
        state = SharedDataHealthState.MARKET_CLOSED
        interpretation = SharedDataChangeInterpretation.EXPECTED_MARKET_CLOSED_ABSENCE
        reasons = ["MARKET_CLOSED_STALENESS_NOT_MARKET_EVENT"]
        context_usable = freshness is not SharedFreshnessState.EXPIRED
        uncertainty = 3_500 if context_usable else 8_000
    elif freshness in {
        SharedFreshnessState.STALE,
        SharedFreshnessState.EXPIRED,
    }:
        state = SharedDataHealthState.STALE_UNEXPECTED
        interpretation = SharedDataChangeInterpretation.DATA_FEED_CHANGE
        reasons = ["OPEN_MARKET_DATA_STALE"]
        uncertainty = 8_000 if freshness is SharedFreshnessState.STALE else 10_000
    elif freshness is SharedFreshnessState.INSUFFICIENT:
        state = SharedDataHealthState.INSUFFICIENT
        interpretation = SharedDataChangeInterpretation.INSUFFICIENT
        reasons = ["FRESHNESS_UNRESOLVED"]
    else:
        state = SharedDataHealthState.HEALTHY
        interpretation = SharedDataChangeInterpretation.MARKET_OBSERVABLE
        reasons = ["DATA_HEALTHY_AND_CAUSAL"]
        new_inference = True
        context_usable = True
        uncertainty = 0 if freshness is SharedFreshnessState.FRESH else 1_500

    return SharedDataHealthAssessment(
        instrument_key=observation.instrument_key,
        state=state,
        freshness=freshness,
        interpretation=interpretation,
        evidence_age_ms=age_ms,
        new_market_change_inference_allowed=new_inference,
        historical_context_usable=context_usable,
        uncertainty_floor_bps=uncertainty,
        reason_codes=tuple(reasons),
    )
