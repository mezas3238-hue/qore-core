from qore.infrastructure.trader_lab.capitalizer_source_native_ftm_v48 import (
    V48FTMDecision,
    V48FTMTakenSide,
    assess_source_native_ftm,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)


def test_taken_high_without_bearish_reversal_can_confirm_bullish_ftm() -> None:
    result = assess_source_native_ftm(
        taken_side=V48FTMTakenSide.HIGH,
        level_taken=True,
        post_sweep_closure_observed=True,
        expected_reversal_cisd_confirmed=False,
        continuation_protected_swing_confirmed=True,
        higher_timeframe_direction=CapitalizerSourceDirection.BULLISH,
    )
    assert result.decision is V48FTMDecision.CONTINUATION_CONFIRMED
    assert result.continuation_direction is CapitalizerSourceDirection.BULLISH
    assert result.expected_reversal_direction is CapitalizerSourceDirection.BEARISH


def test_taken_low_without_bullish_reversal_can_confirm_bearish_ftm() -> None:
    result = assess_source_native_ftm(
        taken_side=V48FTMTakenSide.LOW,
        level_taken=True,
        post_sweep_closure_observed=True,
        expected_reversal_cisd_confirmed=False,
        continuation_protected_swing_confirmed=True,
        higher_timeframe_direction=CapitalizerSourceDirection.BEARISH,
    )
    assert result.decision is V48FTMDecision.CONTINUATION_CONFIRMED


def test_confirmed_expected_reversal_prevents_ftm_continuation() -> None:
    result = assess_source_native_ftm(
        taken_side=V48FTMTakenSide.HIGH,
        level_taken=True,
        post_sweep_closure_observed=True,
        expected_reversal_cisd_confirmed=True,
        continuation_protected_swing_confirmed=True,
        higher_timeframe_direction=CapitalizerSourceDirection.BULLISH,
    )
    assert result.decision is V48FTMDecision.WAIT


def test_ftm_requires_higher_timeframe_directional_reason() -> None:
    result = assess_source_native_ftm(
        taken_side=V48FTMTakenSide.HIGH,
        level_taken=True,
        post_sweep_closure_observed=True,
        expected_reversal_cisd_confirmed=False,
        continuation_protected_swing_confirmed=True,
        higher_timeframe_direction=None,
    )
    assert result.decision is V48FTMDecision.WAIT
    assert result.higher_timeframe_bias_aligned is False


def test_ftm_v48_does_not_inherit_v47_superintersection() -> None:
    result = assess_source_native_ftm(
        taken_side=V48FTMTakenSide.HIGH,
        level_taken=True,
        post_sweep_closure_observed=True,
        expected_reversal_cisd_confirmed=False,
        continuation_protected_swing_confirmed=True,
        higher_timeframe_direction=CapitalizerSourceDirection.BULLISH,
    )
    assert result.m3_displacement_required is False
    assert result.ict_fvg_required is False
    assert result.m1_mss_required is False
    assert result.m1_fvg_required is False
    assert result.m1_order_block_required is False
    assert result.outcome_used is False
    assert result.target_used is False
