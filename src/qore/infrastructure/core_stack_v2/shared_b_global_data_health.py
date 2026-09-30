"""Architect-B global data-health expansion.

This additive boundary preserves the proven X15/X16 contract while modeling
provider/feed failure, partial degradation, impossible/crossed observations,
unknown market state and stale relational evidence as distinct epistemic facts.
It carries no trading, capital, Risk or Execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Final

_MAX_BPS: Final = 10_000


class SharedBGlobalDataState(StrEnum):
    HEALTHY = "HEALTHY"
    MARKET_CLOSED = "MARKET_CLOSED"
    MARKET_STATE_UNKNOWN = "MARKET_STATE_UNKNOWN"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    FEED_UNAVAILABLE = "FEED_UNAVAILABLE"
    PROVIDER_DEGRADED = "PROVIDER_DEGRADED"
    PARTIAL_DEGRADATION = "PARTIAL_DEGRADATION"
    CROSSED_QUOTE = "CROSSED_QUOTE"
    IMPOSSIBLE_VALUE = "IMPOSSIBLE_VALUE"
    MISSING = "MISSING"
    STALE_UNEXPECTED = "STALE_UNEXPECTED"
    STALE_RELATION = "STALE_RELATION"
    FUTURE_EVIDENCE = "FUTURE_EVIDENCE"
    DUPLICATE = "DUPLICATE"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    IDENTITY_AMBIGUITY = "IDENTITY_AMBIGUITY"
    ROLL_AMBIGUITY = "ROLL_AMBIGUITY"
    INSUFFICIENT = "INSUFFICIENT"


class SharedBGlobalInterpretation(StrEnum):
    MARKET_OBSERVABLE = "MARKET_OBSERVABLE"
    EXPECTED_MARKET_CLOSED_ABSENCE = "EXPECTED_MARKET_CLOSED_ABSENCE"
    DATA_PLANE_FAILURE = "DATA_PLANE_FAILURE"
    DATA_QUALITY_FAILURE = "DATA_QUALITY_FAILURE"
    IDENTITY_UNCERTAINTY = "IDENTITY_UNCERTAINTY"
    RELATIONAL_EVIDENCE_DEGRADED = "RELATIONAL_EVIDENCE_DEGRADED"
    MARKET_STATE_UNKNOWN = "MARKET_STATE_UNKNOWN"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class SharedBGlobalDataObservation:
    instrument_key: str
    decision_time: datetime
    provider_event_at: datetime | None
    retrieved_at: datetime | None
    previous_provider_event_at: datetime | None
    expected_cadence_ms: int
    validity_horizon_ms: int
    decay_horizon_ms: int
    canonical_market_open: bool | None
    provider_available: bool
    feed_available: bool
    provider_degraded: bool
    partial_degradation: bool
    missing: bool
    duplicate: bool
    sequence_monotonic: bool
    crossed_quote: bool
    impossible_value: bool
    canonical_identity_verified: bool
    roll_identity_unambiguous: bool
    relation_evidence_age_ms: int | None
    relation_validity_horizon_ms: int | None
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.instrument_key.strip():
            raise ValueError("instrument_key must be non-empty")
        if self.decision_time.tzinfo is None or self.decision_time.utcoffset() is None:
            raise ValueError("decision_time must be timezone-aware")
        for name in (
            "provider_event_at",
            "retrieved_at",
            "previous_provider_event_at",
        ):
            value = getattr(self, name)
            if value is not None and (
                value.tzinfo is None or value.utcoffset() is None
            ):
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
        if self.canonical_market_open not in (True, False, None):
            raise ValueError("canonical_market_open must be bool or None")
        for name in (
            "provider_available",
            "feed_available",
            "provider_degraded",
            "partial_degradation",
            "missing",
            "duplicate",
            "sequence_monotonic",
            "crossed_quote",
            "impossible_value",
            "canonical_identity_verified",
            "roll_identity_unambiguous",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be bool")
        if (
            self.relation_evidence_age_ms is None
            and self.relation_validity_horizon_ms is not None
        ):
            raise ValueError(
                "relation validity horizon requires relation evidence age"
            )
        if self.relation_evidence_age_ms is not None:
            if type(self.relation_evidence_age_ms) is not int or self.relation_evidence_age_ms < 0:
                raise ValueError("relation_evidence_age_ms must be non-negative int")
            if (
                type(self.relation_validity_horizon_ms) is not int
                or self.relation_validity_horizon_ms <= 0
            ):
                raise ValueError(
                    "relation_validity_horizon_ms must be positive int"
                )
        if (
            not self.provenance_refs
            or self.provenance_refs != tuple(sorted(set(self.provenance_refs)))
        ):
            raise ValueError(
                "provenance_refs must be non-empty, unique and canonical"
            )


@dataclass(frozen=True, slots=True)
class SharedBGlobalDataAssessment:
    instrument_key: str
    state: SharedBGlobalDataState
    interpretation: SharedBGlobalInterpretation
    evidence_age_ms: int | None
    provider_event_age_ms: int | None
    transport_age_ms: int | None
    market_plane_known: bool
    provider_plane_available: bool
    feed_plane_available: bool
    new_market_change_inference_allowed: bool
    relational_claim_allowed: bool
    historical_context_usable: bool
    uncertainty_floor_bps: int
    reason_codes: tuple[str, ...]
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "evidence_age_ms",
            "provider_event_age_ms",
            "transport_age_ms",
        ):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"{name} cannot be negative")
        if not 0 <= self.uncertainty_floor_bps <= _MAX_BPS:
            raise ValueError("uncertainty_floor_bps outside 0..10000")
        if (
            not self.reason_codes
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
        ):
            raise ValueError("reason_codes must be non-empty, unique and canonical")
        if (
            self.execution_authority
            or self.risk_authority
            or self.sizing_authority
            or self.capital_authority
        ):
            raise ValueError("global data health carries no downstream authority")


def _age_ms(
    decision_time: datetime,
    observed_at: datetime | None,
) -> int | None:
    if observed_at is None:
        return None
    return int((decision_time - observed_at).total_seconds() * 1000)


def assess_shared_b_global_data_health(
    observation: SharedBGlobalDataObservation,
) -> SharedBGlobalDataAssessment:
    """Fail closed across distinct market, provider, feed and relation planes."""

    provider_event_age_ms = _age_ms(
        observation.decision_time,
        observation.provider_event_at,
    )
    transport_age_ms = _age_ms(
        observation.decision_time,
        observation.retrieved_at,
    )
    state = SharedBGlobalDataState.INSUFFICIENT
    interpretation = SharedBGlobalInterpretation.INSUFFICIENT
    reasons: list[str] = []
    new_inference = False
    relation_claim = False
    context_usable = False
    uncertainty = _MAX_BPS

    if not observation.canonical_identity_verified:
        state = SharedBGlobalDataState.IDENTITY_AMBIGUITY
        interpretation = SharedBGlobalInterpretation.IDENTITY_UNCERTAINTY
        reasons = ["CANONICAL_IDENTITY_UNVERIFIED"]
    elif not observation.roll_identity_unambiguous:
        state = SharedBGlobalDataState.ROLL_AMBIGUITY
        interpretation = SharedBGlobalInterpretation.IDENTITY_UNCERTAINTY
        reasons = ["ROLL_OR_CONTRACT_IDENTITY_AMBIGUOUS"]
    elif (
        observation.provider_event_at is not None
        and observation.provider_event_at > observation.decision_time
    ) or (
        observation.retrieved_at is not None
        and observation.retrieved_at > observation.decision_time
    ) or (
        provider_event_age_ms is not None
        and provider_event_age_ms < 0
    ) or (
        transport_age_ms is not None
        and transport_age_ms < 0
    ):
        state = SharedBGlobalDataState.FUTURE_EVIDENCE
        interpretation = SharedBGlobalInterpretation.DATA_QUALITY_FAILURE
        reasons = ["FUTURE_EVIDENCE_REJECTED"]
    elif observation.impossible_value:
        state = SharedBGlobalDataState.IMPOSSIBLE_VALUE
        interpretation = SharedBGlobalInterpretation.DATA_QUALITY_FAILURE
        reasons = ["IMPOSSIBLE_MARKET_VALUE"]
    elif observation.crossed_quote:
        state = SharedBGlobalDataState.CROSSED_QUOTE
        interpretation = SharedBGlobalInterpretation.DATA_QUALITY_FAILURE
        reasons = ["CROSSED_QUOTE_REJECTED"]
    elif not observation.provider_available:
        state = SharedBGlobalDataState.PROVIDER_UNAVAILABLE
        interpretation = SharedBGlobalInterpretation.DATA_PLANE_FAILURE
        reasons = ["PROVIDER_UNAVAILABLE"]
    elif not observation.feed_available:
        state = SharedBGlobalDataState.FEED_UNAVAILABLE
        interpretation = SharedBGlobalInterpretation.DATA_PLANE_FAILURE
        reasons = ["FEED_UNAVAILABLE"]
    elif observation.provider_degraded:
        state = SharedBGlobalDataState.PROVIDER_DEGRADED
        interpretation = SharedBGlobalInterpretation.DATA_PLANE_FAILURE
        reasons = ["PROVIDER_DEGRADED"]
    elif observation.partial_degradation:
        state = SharedBGlobalDataState.PARTIAL_DEGRADATION
        interpretation = SharedBGlobalInterpretation.DATA_PLANE_FAILURE
        reasons = ["PARTIAL_DATA_DEGRADATION"]
    elif observation.duplicate:
        state = SharedBGlobalDataState.DUPLICATE
        interpretation = SharedBGlobalInterpretation.DATA_QUALITY_FAILURE
        reasons = ["DUPLICATE_OBSERVATION"]
    elif not observation.sequence_monotonic or (
        observation.previous_provider_event_at is not None
        and observation.provider_event_at is not None
        and observation.provider_event_at <= observation.previous_provider_event_at
    ):
        state = SharedBGlobalDataState.OUT_OF_ORDER
        interpretation = SharedBGlobalInterpretation.DATA_QUALITY_FAILURE
        reasons = ["OUT_OF_ORDER_OBSERVATION"]
    elif observation.canonical_market_open is None:
        state = SharedBGlobalDataState.MARKET_STATE_UNKNOWN
        interpretation = SharedBGlobalInterpretation.MARKET_STATE_UNKNOWN
        reasons = ["CANONICAL_MARKET_STATE_UNKNOWN"]
    elif (
        observation.missing
        or observation.provider_event_at is None
        or observation.retrieved_at is None
    ):
        if observation.canonical_market_open is False:
            state = SharedBGlobalDataState.MARKET_CLOSED
            interpretation = (
                SharedBGlobalInterpretation.EXPECTED_MARKET_CLOSED_ABSENCE
            )
            reasons = ["MARKET_CLOSED_NO_NEW_OBSERVATION"]
            uncertainty = 5_000
        else:
            state = SharedBGlobalDataState.MISSING
            interpretation = SharedBGlobalInterpretation.DATA_PLANE_FAILURE
            reasons = ["OPEN_MARKET_DATA_MISSING"]
    elif observation.canonical_market_open is False:
        state = SharedBGlobalDataState.MARKET_CLOSED
        interpretation = SharedBGlobalInterpretation.EXPECTED_MARKET_CLOSED_ABSENCE
        reasons = ["MARKET_CLOSED_STALENESS_NOT_FEED_FAILURE"]
        context_usable = (
            provider_event_age_ms is not None
            and provider_event_age_ms <= observation.decay_horizon_ms
        )
        uncertainty = 3_500 if context_usable else 8_000
    elif provider_event_age_ms is None or transport_age_ms is None:
        state = SharedBGlobalDataState.INSUFFICIENT
        interpretation = SharedBGlobalInterpretation.INSUFFICIENT
        reasons = ["EVIDENCE_AGE_UNRESOLVED"]
    elif provider_event_age_ms > observation.validity_horizon_ms:
        state = SharedBGlobalDataState.STALE_UNEXPECTED
        interpretation = SharedBGlobalInterpretation.DATA_PLANE_FAILURE
        reasons = ["MARKET_EVENT_STALE"]
        uncertainty = (
            8_000
            if provider_event_age_ms <= observation.decay_horizon_ms
            else 10_000
        )
    elif transport_age_ms > observation.validity_horizon_ms:
        state = SharedBGlobalDataState.STALE_UNEXPECTED
        interpretation = SharedBGlobalInterpretation.DATA_PLANE_FAILURE
        reasons = ["TRANSPORT_EVIDENCE_STALE"]
        uncertainty = (
            8_000
            if transport_age_ms <= observation.decay_horizon_ms
            else 10_000
        )
    else:
        relation_stale = (
            observation.relation_evidence_age_ms is not None
            and observation.relation_validity_horizon_ms is not None
            and observation.relation_evidence_age_ms
            > observation.relation_validity_horizon_ms
        )
        if relation_stale:
            state = SharedBGlobalDataState.STALE_RELATION
            interpretation = (
                SharedBGlobalInterpretation.RELATIONAL_EVIDENCE_DEGRADED
            )
            reasons = ["RELATIONAL_EVIDENCE_STALE"]
            new_inference = True
            context_usable = True
            uncertainty = 2_500
        else:
            state = SharedBGlobalDataState.HEALTHY
            interpretation = SharedBGlobalInterpretation.MARKET_OBSERVABLE
            reasons = ["DATA_HEALTHY_AND_CAUSAL"]
            new_inference = True
            relation_claim = True
            context_usable = True
            uncertainty = (
                0
                if (
                    provider_event_age_ms <= observation.expected_cadence_ms
                    and transport_age_ms <= observation.expected_cadence_ms
                )
                else 1_500
            )

    return SharedBGlobalDataAssessment(
        instrument_key=observation.instrument_key,
        state=state,
        interpretation=interpretation,
        evidence_age_ms=(
            None
            if provider_event_age_ms is None or provider_event_age_ms < 0
            else provider_event_age_ms
        ),
        provider_event_age_ms=(
            None
            if provider_event_age_ms is None or provider_event_age_ms < 0
            else provider_event_age_ms
        ),
        transport_age_ms=(
            None
            if transport_age_ms is None or transport_age_ms < 0
            else transport_age_ms
        ),
        market_plane_known=observation.canonical_market_open is not None,
        provider_plane_available=observation.provider_available,
        feed_plane_available=observation.feed_available,
        new_market_change_inference_allowed=new_inference,
        relational_claim_allowed=relation_claim,
        historical_context_usable=context_usable,
        uncertainty_floor_bps=uncertainty,
        reason_codes=tuple(sorted(set(reasons))),
    )
