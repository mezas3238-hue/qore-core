"""Source-native Failure-to-Manipulate primitive for Capitalizer V48.

This primitive implements only the TTrades FTM structural identity:
level taken -> expected reversal fails to confirm -> continuation/protected swing confirms
-> continuation aligns with a higher-timeframe directional reason.

It deliberately does not inherit the V2 daily-bias object, M3 displacement, ICT FVG,
M1 MSS/FVG/OB superintersection, target uniqueness, outcomes, capital or execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)

IDENTITY = "QORE_CAPITALIZER_V48_SOURCE_NATIVE_FTM"


class V48FTMTakenSide(StrEnum):
    HIGH = "HIGH"
    LOW = "LOW"


class V48FTMDecision(StrEnum):
    CONTINUATION_CONFIRMED = "CONTINUATION_CONFIRMED"
    WAIT = "WAIT"


@dataclass(frozen=True, slots=True)
class V48SourceNativeFTMObservation:
    identity: str
    taken_side: V48FTMTakenSide
    continuation_direction: CapitalizerSourceDirection
    expected_reversal_direction: CapitalizerSourceDirection
    level_taken: bool
    post_sweep_closure_observed: bool
    expected_reversal_cisd_confirmed: bool
    continuation_protected_swing_confirmed: bool
    higher_timeframe_direction: CapitalizerSourceDirection | None
    higher_timeframe_bias_aligned: bool
    decision: V48FTMDecision
    outcome_used: bool = False
    target_used: bool = False
    m3_displacement_required: bool = False
    ict_fvg_required: bool = False
    m1_mss_required: bool = False
    m1_fvg_required: bool = False
    m1_order_block_required: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 FTM identity is frozen")
        if self.outcome_used or self.target_used:
            raise ValueError("V48 FTM primitive must remain pre-economic")
        if (
            self.m3_displacement_required
            or self.ict_fvg_required
            or self.m1_mss_required
            or self.m1_fvg_required
            or self.m1_order_block_required
        ):
            raise ValueError("V48 FTM cannot inherit unrelated V47 hard gates")

        confirmed = self.decision is V48FTMDecision.CONTINUATION_CONFIRMED
        expected_confirmed = (
            self.level_taken
            and self.post_sweep_closure_observed
            and not self.expected_reversal_cisd_confirmed
            and self.continuation_protected_swing_confirmed
            and self.higher_timeframe_bias_aligned
        )
        if confirmed != expected_confirmed:
            raise ValueError("V48 FTM decision/payload mismatch")


def assess_source_native_ftm(
    *,
    taken_side: V48FTMTakenSide,
    level_taken: bool,
    post_sweep_closure_observed: bool,
    expected_reversal_cisd_confirmed: bool,
    continuation_protected_swing_confirmed: bool,
    higher_timeframe_direction: CapitalizerSourceDirection | None,
) -> V48SourceNativeFTMObservation:
    """Assess FTM without importing the old route-specific daily-bias contract."""

    if taken_side is V48FTMTakenSide.HIGH:
        continuation = CapitalizerSourceDirection.BULLISH
        expected_reversal = CapitalizerSourceDirection.BEARISH
    else:
        continuation = CapitalizerSourceDirection.BEARISH
        expected_reversal = CapitalizerSourceDirection.BULLISH

    htf_aligned = higher_timeframe_direction is continuation
    confirmed = (
        level_taken
        and post_sweep_closure_observed
        and not expected_reversal_cisd_confirmed
        and continuation_protected_swing_confirmed
        and htf_aligned
    )

    return V48SourceNativeFTMObservation(
        identity=IDENTITY,
        taken_side=taken_side,
        continuation_direction=continuation,
        expected_reversal_direction=expected_reversal,
        level_taken=level_taken,
        post_sweep_closure_observed=post_sweep_closure_observed,
        expected_reversal_cisd_confirmed=expected_reversal_cisd_confirmed,
        continuation_protected_swing_confirmed=continuation_protected_swing_confirmed,
        higher_timeframe_direction=higher_timeframe_direction,
        higher_timeframe_bias_aligned=htf_aligned,
        decision=(
            V48FTMDecision.CONTINUATION_CONFIRMED
            if confirmed
            else V48FTMDecision.WAIT
        ),
    )
