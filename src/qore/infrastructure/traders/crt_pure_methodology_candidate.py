"""Research-only methodology candidate for CRT PURE.

This module captures the current source reconstruction as a deterministic candidate.
It is intentionally NOT executable. Candidate semantics may be promoted only when
the corresponding concepts close through the approved primary-source registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.traders.crt_pure_source_registry import CrtPureConceptId


class CrtPureCandidateDirection(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"


class CrtPureRangeOutcome(StrEnum):
    TURTLE_SOUP = "TURTLE_SOUP"
    BREAKOUT = "BREAKOUT"
    UNRESOLVED = "UNRESOLVED"


class CrtPureCandidatePhase(StrEnum):
    CANDLE_1_RANGE = "CANDLE_1_RANGE"
    CANDLE_2_MANIPULATION = "CANDLE_2_MANIPULATION"
    CANDLE_3_DISTRIBUTION = "CANDLE_3_DISTRIBUTION"


@dataclass(frozen=True, slots=True)
class CrtPureCandidateSemantics:
    """Deterministic research candidate, not Strategy Identity."""

    every_candle_is_range: bool = True
    candle_1_role: CrtPureCandidatePhase = CrtPureCandidatePhase.CANDLE_1_RANGE
    candle_2_role: CrtPureCandidatePhase = CrtPureCandidatePhase.CANDLE_2_MANIPULATION
    candle_3_role: CrtPureCandidatePhase = CrtPureCandidatePhase.CANDLE_3_DISTRIBUTION
    turtle_soup_requires_penetration: bool = True
    turtle_soup_requires_return_into_range: bool = True
    first_destination_is_range_50_percent: bool = True
    extension_destination_is_opposite_range_edge: bool = True
    force_trade_when_turtle_soup_missing: bool = False
    fixed_timeframe_alignment: bool = False
    executable: bool = False

    def __post_init__(self) -> None:
        if self.executable:
            raise ValueError("source candidate cannot be executable before primary closure")
        if self.force_trade_when_turtle_soup_missing:
            raise ValueError("CRT candidate must fail closed when turtle soup is absent")
        if self.fixed_timeframe_alignment:
            raise ValueError("current source reconstruction rejects universal fixed TF alignment")


CRT_PURE_METHOD_CANDIDATE = CrtPureCandidateSemantics()


CANDIDATE_SOURCE_DEPENDENCIES: tuple[CrtPureConceptId, ...] = (
    CrtPureConceptId.REFERENCE_RANGE,
    CrtPureConceptId.CRH_CRL,
    CrtPureConceptId.LIQUIDATION_SWEEP,
    CrtPureConceptId.RECLAIM_CLOSE_BACK_INSIDE,
    CrtPureConceptId.CANDLE_1_2_3,
    CrtPureConceptId.TIMEFRAME_HIERARCHY,
    CrtPureConceptId.ENTRY_FAMILIES,
    CrtPureConceptId.STRUCTURAL_DESTINATION,
    CrtPureConceptId.INVALIDATION,
)


def candidate_execution_authorized() -> bool:
    """Candidate is research scaffolding only until primary source closure."""

    return False


def classify_range_outcome(
    *,
    reference_high: float,
    reference_low: float,
    observed_high: float,
    observed_low: float,
    observed_close: float,
) -> CrtPureRangeOutcome:
    """Classify the current reconstructed wick/close distinction."""

    if reference_low >= reference_high:
        raise ValueError("reference range must have positive width")

    swept_high = observed_high > reference_high
    swept_low = observed_low < reference_low
    closes_above = observed_close > reference_high
    closes_below = observed_close < reference_low
    closes_inside = reference_low <= observed_close <= reference_high

    if closes_above or closes_below:
        return CrtPureRangeOutcome.BREAKOUT

    if closes_inside and swept_high != swept_low:
        return CrtPureRangeOutcome.TURTLE_SOUP

    return CrtPureRangeOutcome.UNRESOLVED


def candidate_direction_from_turtle_soup(
    *,
    reference_high: float,
    reference_low: float,
    observed_high: float,
    observed_low: float,
    observed_close: float,
) -> CrtPureCandidateDirection | None:
    outcome = classify_range_outcome(
        reference_high=reference_high,
        reference_low=reference_low,
        observed_high=observed_high,
        observed_low=observed_low,
        observed_close=observed_close,
    )
    if outcome is not CrtPureRangeOutcome.TURTLE_SOUP:
        return None
    if observed_high > reference_high:
        return CrtPureCandidateDirection.BEARISH
    if observed_low < reference_low:
        return CrtPureCandidateDirection.BULLISH
    return None


def range_midpoint(reference_high: float, reference_low: float) -> float:
    if reference_low >= reference_high:
        raise ValueError("reference range must have positive width")
    return reference_low + ((reference_high - reference_low) / 2.0)
