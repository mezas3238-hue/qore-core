"""Structural extraction helpers for source-faithful Capitalizer observations.

This module removes manual stop/target injection for the baseline source route:
- a confirmed CISD yields the protected swing extreme that produced the shift;
- the prior completed daily high/low yields a structural liquidity target only while untouched
  at the decision point.

No post-decision outcomes are used.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    CapitalizerCISDObservation,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingObservation,
    CapitalizerProtectedSwingOrigin,
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
    CapitalizerStructuralTargetObservation,
    assess_structural_target,
)


def protected_swing_from_cisd(
    *,
    cisd: CapitalizerCISDObservation,
    causal_series: tuple[CapitalizerSourceBar, ...],
    confirmation_bar: CapitalizerSourceBar,
    origin: CapitalizerProtectedSwingOrigin,
) -> CapitalizerProtectedSwingObservation:
    """Extract the swing extreme only after the source CISD is confirmed."""

    if not cisd.confirmed:
        raise ValueError("protected swing extraction requires confirmed CISD")
    if not causal_series:
        raise ValueError("protected swing extraction requires causal series")

    bars = (*causal_series, confirmation_bar)
    if cisd.direction is CapitalizerSourceDirection.BULLISH:
        swing_price = min(bar.low for bar in bars)
    else:
        swing_price = max(bar.high for bar in bars)

    return CapitalizerProtectedSwingObservation(
        direction=cisd.direction,
        swing_price=swing_price,
        origin=origin,
        closure_through_causal_series_confirmed=True,
        confirmed=True,
        reasons=(
            f"ORIGIN:{origin.value}",
            "PROTECTED_SWING_EXTRACTED_FROM_CONFIRMED_CISD",
            "CAUSAL_SERIES_CLOSURE_CONFIRMED",
        ),
    )


@dataclass(frozen=True, slots=True)
class CapitalizerPreviousDayTargetExtraction:
    direction: CapitalizerSourceDirection
    prior_day_level: Decimal
    touched_before_decision: bool
    observation: CapitalizerStructuralTargetObservation


def extract_previous_day_liquidity_target(
    *,
    previous_daily_bar: CapitalizerSourceBar,
    bars_since_current_day_open: tuple[CapitalizerSourceBar, ...],
    direction: CapitalizerSourceDirection,
    entry_price: Decimal,
) -> CapitalizerPreviousDayTargetExtraction:
    """Build the ICT prior-day directional liquidity objective causally."""

    if direction is CapitalizerSourceDirection.BULLISH:
        target_price = previous_daily_bar.high
        touched = any(bar.high >= target_price for bar in bars_since_current_day_open)
    else:
        target_price = previous_daily_bar.low
        touched = any(bar.low <= target_price for bar in bars_since_current_day_open)

    observation = assess_structural_target(
        direction=direction,
        entry_price=entry_price,
        target_price=target_price,
        untouched=not touched,
        higher_timeframe=True,
    )
    return CapitalizerPreviousDayTargetExtraction(
        direction=direction,
        prior_day_level=target_price,
        touched_before_decision=touched,
        observation=observation,
    )
