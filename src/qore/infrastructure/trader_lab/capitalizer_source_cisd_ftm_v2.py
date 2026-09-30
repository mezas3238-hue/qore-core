"""CISD and Failure-to-Manipulate source observations for Capitalizer V2.

Mechanics are encoded from reviewed TTrades source semantics:
- CISD uses the opening price of the first opposing candle in the causal series;
- higher-timeframe Candle 2/Candle 3 context is required for scalp continuation use;
- Failure to Manipulate requires a taken level, failure of the expected reversal CISD,
  and confirmed continuation structure aligned with higher-timeframe direction.

No outcome fitting or numeric optimization is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_source_daily_bias_v2 import (
    CapitalizerDailyBiasObservation,
    CapitalizerDailyBiasResolution,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingObservation,
    CapitalizerSourceBar,
    CapitalizerSourceClosureObservation,
    CapitalizerSourceDirection,
)


class CapitalizerCausalSeriesKind(StrEnum):
    UP_CLOSE_SERIES = "UP_CLOSE_SERIES"
    DOWN_CLOSE_SERIES = "DOWN_CLOSE_SERIES"


@dataclass(frozen=True, slots=True)
class CapitalizerCISDObservation:
    direction: CapitalizerSourceDirection
    causal_series_kind: CapitalizerCausalSeriesKind
    causal_series_open: Decimal
    confirmation_close: Decimal
    important_level_reached: bool
    higher_timeframe_closure_confirmed: bool
    structural_confirmed: bool
    setup_confirmed: bool
    reasons: tuple[str, ...]

    @property
    def confirmed(self) -> bool:
        """Backward-compatible alias for setup eligibility, not raw CISD structure."""
        return self.setup_confirmed


def detect_cisd(
    *,
    causal_series: tuple[CapitalizerSourceBar, ...],
    confirmation_bar: CapitalizerSourceBar,
    direction: CapitalizerSourceDirection,
    important_level_reached: bool,
    higher_timeframe_closure: CapitalizerSourceClosureObservation | None,
) -> CapitalizerCISDObservation:
    """Confirm CISD through the opening price of the first opposing candle series."""

    if not causal_series:
        raise ValueError("CISD requires a non-empty causal candle series")

    if direction is CapitalizerSourceDirection.BEARISH:
        if not all(bar.close > bar.open for bar in causal_series):
            raise ValueError("bearish CISD requires an up-close causal series")
        series_kind = CapitalizerCausalSeriesKind.UP_CLOSE_SERIES
        confirmed_close = confirmation_bar.close < causal_series[0].open
    else:
        if not all(bar.close < bar.open for bar in causal_series):
            raise ValueError("bullish CISD requires a down-close causal series")
        series_kind = CapitalizerCausalSeriesKind.DOWN_CLOSE_SERIES
        confirmed_close = confirmation_bar.close > causal_series[0].open

    htf_confirmed = (
        higher_timeframe_closure is not None
        and higher_timeframe_closure.source_rule_satisfied
        and higher_timeframe_closure.direction is direction
    )
    structural_confirmed = important_level_reached and confirmed_close
    setup_confirmed = structural_confirmed and htf_confirmed

    reasons = (
        f"CAUSAL_SERIES:{series_kind.value}",
        "IMPORTANT_LEVEL_REACHED"
        if important_level_reached
        else "IMPORTANT_LEVEL_NOT_REACHED",
        "HTF_C2_C3_CLOSURE_ALIGNED"
        if htf_confirmed
        else "HTF_C2_C3_CLOSURE_MISSING_OR_MISALIGNED",
        "CLOSE_THROUGH_FIRST_CAUSAL_CANDLE_OPEN"
        if confirmed_close
        else "NO_CLOSE_THROUGH_FIRST_CAUSAL_CANDLE_OPEN",
    )
    return CapitalizerCISDObservation(
        direction=direction,
        causal_series_kind=series_kind,
        causal_series_open=causal_series[0].open,
        confirmation_close=confirmation_bar.close,
        important_level_reached=important_level_reached,
        higher_timeframe_closure_confirmed=htf_confirmed,
        structural_confirmed=structural_confirmed,
        setup_confirmed=setup_confirmed,
        reasons=reasons,
    )


class CapitalizerLiquiditySideTaken(StrEnum):
    HIGH = "HIGH"
    LOW = "LOW"


@dataclass(frozen=True, slots=True)
class CapitalizerFailureToManipulateObservation:
    taken_side: CapitalizerLiquiditySideTaken
    continuation_direction: CapitalizerSourceDirection
    expected_reversal_direction: CapitalizerSourceDirection
    level_taken: bool
    post_sweep_closure_observed: bool
    expected_reversal_cisd_confirmed: bool
    continuation_protected_swing_confirmed: bool
    higher_timeframe_bias_aligned: bool
    confirmed: bool
    reasons: tuple[str, ...]


def assess_failure_to_manipulate(
    *,
    taken_side: CapitalizerLiquiditySideTaken,
    level_taken: bool,
    post_sweep_closure_observed: bool,
    expected_reversal_cisd: CapitalizerCISDObservation | None,
    continuation_protected_swing: CapitalizerProtectedSwingObservation | None,
    daily_bias: CapitalizerDailyBiasObservation,
) -> CapitalizerFailureToManipulateObservation:
    """Confirm continuation only after the expected post-sweep reversal fails."""

    if taken_side is CapitalizerLiquiditySideTaken.HIGH:
        continuation = CapitalizerSourceDirection.BULLISH
        expected_reversal = CapitalizerSourceDirection.BEARISH
    else:
        continuation = CapitalizerSourceDirection.BEARISH
        expected_reversal = CapitalizerSourceDirection.BULLISH

    reversal_confirmed = (
        expected_reversal_cisd is not None
        and expected_reversal_cisd.direction is expected_reversal
        and expected_reversal_cisd.structural_confirmed
    )
    continuation_confirmed = (
        continuation_protected_swing is not None
        and continuation_protected_swing.direction is continuation
        and continuation_protected_swing.confirmed
    )
    htf_aligned = (
        daily_bias.resolution is CapitalizerDailyBiasResolution.CONFIRMED
        and daily_bias.direction is continuation
    )

    confirmed = (
        level_taken
        and post_sweep_closure_observed
        and not reversal_confirmed
        and continuation_confirmed
        and htf_aligned
    )

    return CapitalizerFailureToManipulateObservation(
        taken_side=taken_side,
        continuation_direction=continuation,
        expected_reversal_direction=expected_reversal,
        level_taken=level_taken,
        post_sweep_closure_observed=post_sweep_closure_observed,
        expected_reversal_cisd_confirmed=reversal_confirmed,
        continuation_protected_swing_confirmed=continuation_confirmed,
        higher_timeframe_bias_aligned=htf_aligned,
        confirmed=confirmed,
        reasons=(
            "LIQUIDITY_LEVEL_TAKEN" if level_taken else "LIQUIDITY_LEVEL_NOT_TAKEN",
            "POST_SWEEP_CLOSURE_OBSERVED"
            if post_sweep_closure_observed
            else "POST_SWEEP_CLOSURE_NOT_OBSERVED",
            "EXPECTED_REVERSAL_CISD_CONFIRMED"
            if reversal_confirmed
            else "EXPECTED_REVERSAL_CISD_FAILED_TO_CONFIRM",
            "CONTINUATION_PROTECTED_SWING_CONFIRMED"
            if continuation_confirmed
            else "CONTINUATION_PROTECTED_SWING_NOT_CONFIRMED",
            "HTF_BIAS_ALIGNED_WITH_CONTINUATION"
            if htf_aligned
            else "HTF_BIAS_NOT_ALIGNED_WITH_CONTINUATION",
        ),
    )
