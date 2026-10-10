"""Source-native Failure-to-Manipulate observation for Capitalizer V48.

This module preserves the TTrades FTM identity without inheriting V47's full ICT/M1
superintersection. It is pre-economic and does not create an entry price, stop, target,
or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)

IDENTITY = "QORE_CAPITALIZER_V48_SOURCE_NATIVE_FTM_OBSERVER"


class V48FTMTakenSide(StrEnum):
    HIGH = "HIGH"
    LOW = "LOW"


class V48FTMState(StrEnum):
    CONFIRMED = "CONFIRMED"
    WAIT = "WAIT"


@dataclass(frozen=True, slots=True)
class V48FTMFacts:
    taken_side: V48FTMTakenSide
    level_taken: bool
    post_sweep_closure_observed: bool
    expected_reversal_structure_confirmed: bool
    continuation_structure_confirmed: bool
    continuation_protected_swing_confirmed: bool
    htf_bias_direction: CapitalizerSourceDirection | None
    outcome_used: bool = False
    ict_mss_required: bool = False
    ict_fvg_required: bool = False
    m1_order_block_required: bool = False

    def __post_init__(self) -> None:
        if self.outcome_used:
            raise ValueError("FTM observation cannot use terminal outcomes")
        if self.ict_mss_required or self.ict_fvg_required or self.m1_order_block_required:
            raise ValueError("V48 FTM core cannot inherit unrelated global hard gates")


@dataclass(frozen=True, slots=True)
class V48FTMObservation:
    identity: str
    state: V48FTMState
    taken_side: V48FTMTakenSide
    continuation_direction: CapitalizerSourceDirection
    expected_reversal_direction: CapitalizerSourceDirection
    htf_bias_aligned: bool
    expected_reversal_failed_to_confirm: bool
    continuation_structure_confirmed: bool
    continuation_protected_swing_confirmed: bool
    reasons: tuple[str, ...]
    entry_authority: bool = False
    execution_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 FTM observer identity is frozen")
        if not self.reasons:
            raise ValueError("FTM observation requires explicit reasons")
        if self.entry_authority or self.execution_authority or self.capital_authority:
            raise ValueError("FTM observation alone grants no trading/capital authority")

    @property
    def confirmed(self) -> bool:
        return self.state is V48FTMState.CONFIRMED


def observe_source_native_ftm(facts: V48FTMFacts) -> V48FTMObservation:
    """Confirm FTM only after reversal failure and HTF-aligned continuation."""

    if facts.taken_side is V48FTMTakenSide.HIGH:
        continuation = CapitalizerSourceDirection.BULLISH
        expected_reversal = CapitalizerSourceDirection.BEARISH
    else:
        continuation = CapitalizerSourceDirection.BEARISH
        expected_reversal = CapitalizerSourceDirection.BULLISH

    htf_aligned = facts.htf_bias_direction is continuation
    reversal_failed = not facts.expected_reversal_structure_confirmed
    confirmed = (
        facts.level_taken
        and facts.post_sweep_closure_observed
        and reversal_failed
        and facts.continuation_structure_confirmed
        and facts.continuation_protected_swing_confirmed
        and htf_aligned
    )

    reasons = (
        "LIQUIDITY_LEVEL_TAKEN" if facts.level_taken else "LIQUIDITY_LEVEL_NOT_TAKEN",
        (
            "POST_SWEEP_CLOSURE_OBSERVED"
            if facts.post_sweep_closure_observed
            else "POST_SWEEP_CLOSURE_NOT_OBSERVED"
        ),
        (
            "EXPECTED_REVERSAL_FAILED_TO_CONFIRM"
            if reversal_failed
            else "EXPECTED_REVERSAL_CONFIRMED"
        ),
        (
            "CONTINUATION_STRUCTURE_CONFIRMED"
            if facts.continuation_structure_confirmed
            else "CONTINUATION_STRUCTURE_NOT_CONFIRMED"
        ),
        (
            "CONTINUATION_PROTECTED_SWING_CONFIRMED"
            if facts.continuation_protected_swing_confirmed
            else "CONTINUATION_PROTECTED_SWING_NOT_CONFIRMED"
        ),
        "HTF_BIAS_ALIGNED" if htf_aligned else "HTF_BIAS_NOT_ALIGNED",
    )
    return V48FTMObservation(
        identity=IDENTITY,
        state=V48FTMState.CONFIRMED if confirmed else V48FTMState.WAIT,
        taken_side=facts.taken_side,
        continuation_direction=continuation,
        expected_reversal_direction=expected_reversal,
        htf_bias_aligned=htf_aligned,
        expected_reversal_failed_to_confirm=reversal_failed,
        continuation_structure_confirmed=facts.continuation_structure_confirmed,
        continuation_protected_swing_confirmed=facts.continuation_protected_swing_confirmed,
        reasons=reasons,
    )
