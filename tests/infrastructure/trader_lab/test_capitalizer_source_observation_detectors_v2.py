from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingOrigin,
    CapitalizerSourceBar,
    CapitalizerSourceClosureKind,
    CapitalizerSourceDirection,
    assess_structural_target,
    confirm_protected_swing,
    detect_candle2_reversal_closure,
    detect_candle3_confirmation,
)


def _bar(open_: str, high: str, low: str, close: str) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_candle2_bullish_requires_sweep_close_inside_and_poi() -> None:
    previous = _bar("100", "102", "98", "101")
    candle2 = _bar("100", "101", "97", "99")

    observed = detect_candle2_reversal_closure(
        previous=previous,
        candle2=candle2,
        point_of_interest_present=True,
    )

    assert observed is not None
    assert observed.kind is CapitalizerSourceClosureKind.CANDLE2_REVERSAL
    assert observed.direction is CapitalizerSourceDirection.BULLISH
    assert observed.source_rule_satisfied is True

    without_poi = detect_candle2_reversal_closure(
        previous=previous,
        candle2=candle2,
        point_of_interest_present=False,
    )
    assert without_poi is not None
    assert without_poi.source_rule_satisfied is False


def test_candle3_confirmation_requires_candle2_failure_and_no_range_sweep() -> None:
    candle2 = _bar("100", "102", "98", "99")
    candle3 = _bar("99", "101.5", "98.5", "100.5")

    observed = detect_candle3_confirmation(
        candle2=candle2,
        candle3=candle3,
        point_of_interest_present=True,
        candle2_reversal_already_confirmed=False,
    )

    assert observed is not None
    assert observed.kind is CapitalizerSourceClosureKind.CANDLE3_CONFIRMATION
    assert observed.direction is CapitalizerSourceDirection.BULLISH
    assert observed.source_rule_satisfied is True

    assert (
        detect_candle3_confirmation(
            candle2=candle2,
            candle3=candle3,
            point_of_interest_present=True,
            candle2_reversal_already_confirmed=True,
        )
        is None
    )


def test_protected_swing_is_not_confirmed_without_causal_series_closure() -> None:
    pending = confirm_protected_swing(
        direction=CapitalizerSourceDirection.BULLISH,
        swing_price=Decimal("99"),
        origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
        closure_through_causal_series_confirmed=False,
    )
    confirmed = confirm_protected_swing(
        direction=CapitalizerSourceDirection.BULLISH,
        swing_price=Decimal("99"),
        origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
        closure_through_causal_series_confirmed=True,
    )

    assert pending.confirmed is False
    assert confirmed.confirmed is True


def test_structural_target_must_be_untouched_htf_and_directionally_valid() -> None:
    valid = assess_structural_target(
        direction=CapitalizerSourceDirection.BULLISH,
        entry_price=Decimal("100"),
        target_price=Decimal("105"),
        untouched=True,
        higher_timeframe=True,
    )
    consumed = assess_structural_target(
        direction=CapitalizerSourceDirection.BULLISH,
        entry_price=Decimal("100"),
        target_price=Decimal("105"),
        untouched=False,
        higher_timeframe=True,
    )
    wrong_side = assess_structural_target(
        direction=CapitalizerSourceDirection.BULLISH,
        entry_price=Decimal("100"),
        target_price=Decimal("95"),
        untouched=True,
        higher_timeframe=True,
    )

    assert valid.valid is True
    assert consumed.valid is False
    assert wrong_side.valid is False
