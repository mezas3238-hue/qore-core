"""Fractal H1 -> M15 -> M1 source alignment for QORE Capitalizer V2.

This module composes already-confirmed source observations. It does not infer daily bias,
optimize thresholds, or grant execution/capital authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    CapitalizerCISDObservation,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingObservation,
    CapitalizerSourceClosureObservation,
    CapitalizerSourceDirection,
)


@dataclass(frozen=True, slots=True)
class CapitalizerFractalAlignmentObservation:
    direction: CapitalizerSourceDirection
    higher_timeframe_bias_aligned: bool
    h1_closure_confirmed: bool
    m15_cisd_confirmed: bool
    m1_protected_swing_confirmed: bool
    confirmed: bool
    reasons: tuple[str, ...]
    numeric_score_used: bool = False
    grants_entry_authority: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.numeric_score_used:
            raise ValueError("fractal source alignment cannot use numeric scoring")
        if self.grants_entry_authority:
            raise ValueError("fractal alignment alone cannot grant entry authority")
        if self.grants_capital_authority:
            raise ValueError("fractal alignment cannot grant capital authority")


def assess_fractal_alignment(
    *,
    higher_timeframe_bias: CapitalizerSourceDirection,
    h1_closure: CapitalizerSourceClosureObservation | None,
    m15_cisd: CapitalizerCISDObservation | None,
    m1_protected_swing: CapitalizerProtectedSwingObservation | None,
) -> CapitalizerFractalAlignmentObservation:
    """Require directionally aligned confirmation at every source timeframe layer."""

    h1_confirmed = (
        h1_closure is not None
        and h1_closure.source_rule_satisfied
        and h1_closure.direction is higher_timeframe_bias
    )
    m15_confirmed = (
        m15_cisd is not None
        and m15_cisd.confirmed
        and m15_cisd.direction is higher_timeframe_bias
    )
    m1_confirmed = (
        m1_protected_swing is not None
        and m1_protected_swing.confirmed
        and m1_protected_swing.direction is higher_timeframe_bias
    )
    confirmed = h1_confirmed and m15_confirmed and m1_confirmed

    return CapitalizerFractalAlignmentObservation(
        direction=higher_timeframe_bias,
        higher_timeframe_bias_aligned=True,
        h1_closure_confirmed=h1_confirmed,
        m15_cisd_confirmed=m15_confirmed,
        m1_protected_swing_confirmed=m1_confirmed,
        confirmed=confirmed,
        reasons=(
            "HTF_DIRECTION_PRESENT",
            "H1_C2_C3_ALIGNED" if h1_confirmed else "H1_C2_C3_NOT_ALIGNED",
            "M15_CISD_ALIGNED" if m15_confirmed else "M15_CISD_NOT_ALIGNED",
            "M1_PROTECTED_SWING_ALIGNED"
            if m1_confirmed
            else "M1_PROTECTED_SWING_NOT_ALIGNED",
        ),
    )
