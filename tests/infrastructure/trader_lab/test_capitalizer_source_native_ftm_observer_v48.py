from qore.infrastructure.trader_lab.capitalizer_source_native_ftm_observer_v48 import (
    V48FTMFacts,
    V48FTMState,
    V48FTMTakenSide,
    observe_source_native_ftm,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)


def test_high_taken_can_confirm_bullish_ftm_without_ict_or_ob_gates() -> None:
    result = observe_source_native_ftm(
        V48FTMFacts(
            taken_side=V48FTMTakenSide.HIGH,
            level_taken=True,
            post_sweep_closure_observed=True,
            expected_reversal_structure_confirmed=False,
            continuation_structure_confirmed=True,
            continuation_protected_swing_confirmed=True,
            htf_bias_direction=CapitalizerSourceDirection.BULLISH,
        )
    )
    assert result.state is V48FTMState.CONFIRMED
    assert result.continuation_direction is CapitalizerSourceDirection.BULLISH
    assert result.expected_reversal_direction is CapitalizerSourceDirection.BEARISH
    assert result.entry_authority is False
    assert result.execution_authority is False
    assert result.capital_authority is False


def test_expected_reversal_confirmation_blocks_ftm() -> None:
    result = observe_source_native_ftm(
        V48FTMFacts(
            taken_side=V48FTMTakenSide.LOW,
            level_taken=True,
            post_sweep_closure_observed=True,
            expected_reversal_structure_confirmed=True,
            continuation_structure_confirmed=True,
            continuation_protected_swing_confirmed=True,
            htf_bias_direction=CapitalizerSourceDirection.BEARISH,
        )
    )
    assert result.state is V48FTMState.WAIT
    assert result.expected_reversal_failed_to_confirm is False


def test_htf_bias_must_align_with_continuation() -> None:
    result = observe_source_native_ftm(
        V48FTMFacts(
            taken_side=V48FTMTakenSide.HIGH,
            level_taken=True,
            post_sweep_closure_observed=True,
            expected_reversal_structure_confirmed=False,
            continuation_structure_confirmed=True,
            continuation_protected_swing_confirmed=True,
            htf_bias_direction=CapitalizerSourceDirection.BEARISH,
        )
    )
    assert result.state is V48FTMState.WAIT
    assert result.htf_bias_aligned is False



def test_ftm_observer_does_not_inherit_v47_superintersection() -> None:
    facts = V48FTMFacts(
        taken_side=V48FTMTakenSide.HIGH,
        level_taken=True,
        post_sweep_closure_observed=True,
        expected_reversal_structure_confirmed=False,
        continuation_structure_confirmed=True,
        continuation_protected_swing_confirmed=True,
        htf_bias_direction=CapitalizerSourceDirection.BULLISH,
    )
    assert facts.ict_mss_required is False
    assert facts.ict_fvg_required is False
    assert facts.m1_order_block_required is False
    assert facts.outcome_used is False
