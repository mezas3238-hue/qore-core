import pytest

from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CRT_PURE_METHOD_CANDIDATE,
    CrtPureCandidateDirection,
    CrtPureRangeOutcome,
    candidate_direction_from_turtle_soup,
    candidate_execution_authorized,
    classify_range_outcome,
    range_midpoint,
)


def test_candidate_is_explicitly_non_executable() -> None:
    assert CRT_PURE_METHOD_CANDIDATE.executable is False
    assert candidate_execution_authorized() is False
    assert CRT_PURE_METHOD_CANDIDATE.force_trade_when_turtle_soup_missing is False
    assert CRT_PURE_METHOD_CANDIDATE.fixed_timeframe_alignment is False


def test_high_sweep_reclaim_is_bearish_turtle_soup_candidate() -> None:
    outcome = classify_range_outcome(
        reference_high=101.0,
        reference_low=99.0,
        observed_high=101.5,
        observed_low=99.5,
        observed_close=100.5,
    )
    assert outcome is CrtPureRangeOutcome.TURTLE_SOUP
    assert candidate_direction_from_turtle_soup(
        reference_high=101.0,
        reference_low=99.0,
        observed_high=101.5,
        observed_low=99.5,
        observed_close=100.5,
    ) is CrtPureCandidateDirection.BEARISH


def test_low_sweep_reclaim_is_bullish_turtle_soup_candidate() -> None:
    outcome = classify_range_outcome(
        reference_high=101.0,
        reference_low=99.0,
        observed_high=100.5,
        observed_low=98.5,
        observed_close=99.5,
    )
    assert outcome is CrtPureRangeOutcome.TURTLE_SOUP
    assert candidate_direction_from_turtle_soup(
        reference_high=101.0,
        reference_low=99.0,
        observed_high=100.5,
        observed_low=98.5,
        observed_close=99.5,
    ) is CrtPureCandidateDirection.BULLISH


def test_close_outside_is_breakout_not_forced_reversal() -> None:
    assert classify_range_outcome(
        reference_high=101.0,
        reference_low=99.0,
        observed_high=102.0,
        observed_low=100.0,
        observed_close=101.5,
    ) is CrtPureRangeOutcome.BREAKOUT


def test_two_sided_sweep_remains_unresolved() -> None:
    assert classify_range_outcome(
        reference_high=101.0,
        reference_low=99.0,
        observed_high=102.0,
        observed_low=98.0,
        observed_close=100.0,
    ) is CrtPureRangeOutcome.UNRESOLVED


def test_midpoint_is_exact_range_50_percent() -> None:
    assert range_midpoint(110.0, 90.0) == 100.0


def test_invalid_range_fails_closed() -> None:
    with pytest.raises(ValueError, match="positive width"):
        classify_range_outcome(
            reference_high=100.0,
            reference_low=100.0,
            observed_high=101.0,
            observed_low=99.0,
            observed_close=100.0,
        )
