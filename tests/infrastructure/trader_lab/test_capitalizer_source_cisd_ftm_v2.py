from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    CapitalizerLiquiditySideTaken,
    assess_failure_to_manipulate,
    detect_cisd,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingOrigin,
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
    confirm_protected_swing,
    detect_candle2_reversal_closure,
)


def _bar(open_: str, high: str, low: str, close: str) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def _bearish_htf_closure():
    return detect_candle2_reversal_closure(
        previous=_bar("100", "102", "98", "101"),
        candle2=_bar("101", "103", "99", "101.5"),
        point_of_interest_present=True,
    )


def test_bearish_cisd_closes_below_first_up_close_candle_open() -> None:
    htf = _bearish_htf_closure()
    assert htf is not None

    observed = detect_cisd(
        causal_series=(
            _bar("100", "101", "99.5", "100.8"),
            _bar("100.8", "102", "100.5", "101.7"),
        ),
        confirmation_bar=_bar("101.5", "101.7", "99", "99.5"),
        direction=CapitalizerSourceDirection.BEARISH,
        important_level_reached=True,
        higher_timeframe_closure=htf,
    )

    assert observed.causal_series_open == Decimal("100")
    assert observed.confirmed is True
    assert "CLOSE_THROUGH_FIRST_CAUSAL_CANDLE_OPEN" in observed.reasons


def test_cisd_is_not_valid_without_aligned_higher_timeframe_closure() -> None:
    observed = detect_cisd(
        causal_series=(
            _bar("100", "101", "99.5", "100.8"),
        ),
        confirmation_bar=_bar("100.5", "100.7", "99", "99.5"),
        direction=CapitalizerSourceDirection.BEARISH,
        important_level_reached=True,
        higher_timeframe_closure=None,
    )

    assert observed.confirmed is False
    assert "HTF_C2_C3_CLOSURE_MISSING_OR_MISALIGNED" in observed.reasons


def test_failure_to_manipulate_requires_failed_reversal_and_new_continuation_structure() -> None:
    bullish_protected_low = confirm_protected_swing(
        direction=CapitalizerSourceDirection.BULLISH,
        swing_price=Decimal("99"),
        origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
        closure_through_causal_series_confirmed=True,
    )
    ftm = assess_failure_to_manipulate(
        taken_side=CapitalizerLiquiditySideTaken.HIGH,
        level_taken=True,
        expected_reversal_cisd=None,
        continuation_protected_swing=bullish_protected_low,
        higher_timeframe_bias=CapitalizerSourceDirection.BULLISH,
    )

    assert ftm.continuation_direction is CapitalizerSourceDirection.BULLISH
    assert ftm.expected_reversal_cisd_confirmed is False
    assert ftm.continuation_protected_swing_confirmed is True
    assert ftm.confirmed is True


def test_failure_to_manipulate_is_false_when_expected_reversal_actually_confirms() -> None:
    htf = _bearish_htf_closure()
    assert htf is not None
    bearish_reversal = detect_cisd(
        causal_series=(
            _bar("100", "101", "99.5", "100.8"),
        ),
        confirmation_bar=_bar("100.5", "100.7", "99", "99.5"),
        direction=CapitalizerSourceDirection.BEARISH,
        important_level_reached=True,
        higher_timeframe_closure=htf,
    )
    bullish_protected_low = confirm_protected_swing(
        direction=CapitalizerSourceDirection.BULLISH,
        swing_price=Decimal("99"),
        origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
        closure_through_causal_series_confirmed=True,
    )

    ftm = assess_failure_to_manipulate(
        taken_side=CapitalizerLiquiditySideTaken.HIGH,
        level_taken=True,
        expected_reversal_cisd=bearish_reversal,
        continuation_protected_swing=bullish_protected_low,
        higher_timeframe_bias=CapitalizerSourceDirection.BULLISH,
    )

    assert ftm.expected_reversal_cisd_confirmed is True
    assert ftm.confirmed is False
