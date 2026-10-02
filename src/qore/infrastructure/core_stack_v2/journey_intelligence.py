"""Universal Shared position-journey intelligence.

This module interprets the current causal market state for an already-open
position. It does not mutate targets, stops, orders or risk. It emits a
contextual journey disposition that a trader-specific adapter may translate
without rewriting the trader methodology.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class JourneyDisposition(StrEnum):
    EXTEND = "EXTEND"
    HOLD = "HOLD"
    DEFEND = "DEFEND"
    EXIT_RISK_WARNING = "EXIT_RISK_WARNING"
    INSUFFICIENT = "INSUFFICIENT"


def _iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat()


def _check_bps(*values: int) -> None:
    if any(not 0 <= value <= 10_000 for value in values):
        raise ValueError("journey basis points must be within 0..10000")


@dataclass(frozen=True, slots=True)
class PositionJourneyEvidence:
    trader_id: str
    market: str
    side: str
    opened_at: datetime
    as_of: datetime
    data_integrity_bps: int
    regime_stability_bps: int
    expansion_bps: int
    displacement_bps: int
    momentum_bps: int
    liquidity_capacity_bps: int
    cross_market_confirmation_bps: int
    exhaustion_bps: int
    opposite_displacement_bps: int
    contradiction_bps: int
    anomaly_bps: int
    uncertainty_bps: int

    def __post_init__(self) -> None:
        if not self.trader_id or not self.market:
            raise ValueError("trader_id and market must be non-empty")
        if self.side not in {"LONG", "SHORT"}:
            raise ValueError("side must be LONG or SHORT")
        _iso(self.opened_at)
        _iso(self.as_of)
        if self.opened_at > self.as_of:
            raise ValueError("position cannot open in the future")
        _check_bps(
            self.data_integrity_bps,
            self.regime_stability_bps,
            self.expansion_bps,
            self.displacement_bps,
            self.momentum_bps,
            self.liquidity_capacity_bps,
            self.cross_market_confirmation_bps,
            self.exhaustion_bps,
            self.opposite_displacement_bps,
            self.contradiction_bps,
            self.anomaly_bps,
            self.uncertainty_bps,
        )


@dataclass(frozen=True, slots=True)
class JourneyAssessment:
    trader_id: str
    market: str
    as_of: datetime
    disposition: JourneyDisposition
    continuation_support_bps: int
    deterioration_bps: int
    extension_capacity_bps: int
    reasons: tuple[str, ...]
    target_mutation_authority: bool = False
    stop_mutation_authority: bool = False
    stop_widening_allowed: bool = False
    order_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        _iso(self.as_of)
        _check_bps(
            self.continuation_support_bps,
            self.deterioration_bps,
            self.extension_capacity_bps,
        )
        if (
            self.target_mutation_authority
            or self.stop_mutation_authority
            or self.stop_widening_allowed
            or self.order_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise ValueError("Shared journey intelligence cannot carry trading authority")


def assess_position_journey(evidence: PositionJourneyEvidence) -> JourneyAssessment:
    if evidence.data_integrity_bps < 7_500:
        return JourneyAssessment(
            trader_id=evidence.trader_id,
            market=evidence.market,
            as_of=evidence.as_of,
            disposition=JourneyDisposition.INSUFFICIENT,
            continuation_support_bps=0,
            deterioration_bps=0,
            extension_capacity_bps=0,
            reasons=("DATA_INTEGRITY_INSUFFICIENT",),
        )

    continuation_support = (
        evidence.regime_stability_bps
        + evidence.expansion_bps
        + evidence.displacement_bps
        + evidence.momentum_bps
        + evidence.cross_market_confirmation_bps
        + (10_000 - evidence.uncertainty_bps)
    ) // 6

    extension_capacity = (
        evidence.liquidity_capacity_bps
        + evidence.expansion_bps
        + evidence.displacement_bps
        + evidence.momentum_bps
        + evidence.cross_market_confirmation_bps
        + (10_000 - evidence.exhaustion_bps)
    ) // 6

    deterioration = (
        evidence.exhaustion_bps
        + evidence.opposite_displacement_bps
        + evidence.contradiction_bps
        + evidence.anomaly_bps
        + evidence.uncertainty_bps
        + (10_000 - evidence.regime_stability_bps)
    ) // 6

    reasons: list[str] = []
    if evidence.anomaly_bps >= 8_000 and evidence.opposite_displacement_bps >= 7_000:
        disposition = JourneyDisposition.EXIT_RISK_WARNING
        reasons.extend(("SEVERE_ANOMALY", "OPPOSITE_DISPLACEMENT_STRONG"))
    elif deterioration >= 6_500:
        disposition = JourneyDisposition.DEFEND
        reasons.append("CAUSAL_POSITION_DETERIORATION")
    elif (
        extension_capacity >= 7_000
        and continuation_support >= 6_500
        and deterioration <= 3_500
    ):
        disposition = JourneyDisposition.EXTEND
        reasons.append("EXTENSION_CAPACITY_SUPPORTED")
    else:
        disposition = JourneyDisposition.HOLD
        reasons.append("ORIGINAL_JOURNEY_REMAINS_PREFERRED")

    if evidence.exhaustion_bps >= 6_500:
        reasons.append("EXHAUSTION_RISING")
    if evidence.cross_market_confirmation_bps <= 3_000:
        reasons.append("CROSS_MARKET_CONFIRMATION_WEAK")
    if evidence.liquidity_capacity_bps <= 3_000:
        reasons.append("REMAINING_LIQUIDITY_CAPACITY_LOW")
    if evidence.uncertainty_bps >= 6_500:
        reasons.append("UNCERTAINTY_HIGH")

    return JourneyAssessment(
        trader_id=evidence.trader_id,
        market=evidence.market,
        as_of=evidence.as_of,
        disposition=disposition,
        continuation_support_bps=continuation_support,
        deterioration_bps=deterioration,
        extension_capacity_bps=extension_capacity,
        reasons=tuple(reasons),
    )
