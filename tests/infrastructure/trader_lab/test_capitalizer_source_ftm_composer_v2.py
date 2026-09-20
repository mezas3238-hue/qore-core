from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_source_daily_bias_v2 import derive_daily_bias
from qore.infrastructure.trader_lab.capitalizer_source_ftm_composer_v2 import (
    compose_failure_to_manipulate,
)
from qore.infrastructure.trader_lab.capitalizer_source_liquidity_take_v2 import (
    detect_liquidity_take,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingOrigin,
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
    confirm_protected_swing,
    detect_candle2_reversal_closure,
)
from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    CapitalizerLiquiditySideTaken,
)


def _bar(open_: str, high: str, low: str, close: str) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def _bullish_daily_bias():
    closure = detect_candle2_reversal_closure(
        previous=_bar("100", "102", "98", "99"),
        candle2=_bar("99", "101", "97", "99.5"),
        point_of_interest_present=True,
    )
    assert closure is not None
    return derive_daily_bias(closure)


def test_high_take_is_detected_from_closed_bar_and_composes_bullish_ftm() -> None:
    take = detect_liquidity_take(
        reference_side=CapitalizerLiquiditySideTaken.HIGH,
        reference_price=Decimal("101"),
        closed_bar=_bar("100.5", "102", "100", "101.5"),
    )
    protected = confirm_protected_swing(
        direction=CapitalizerSourceDirection.BULLISH,
        swing_price=Decimal("100"),
        origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
        closure_through_causal_series_confirmed=True,
    )

    ftm = compose_failure_to_manipulate(
        liquidity_take=take,
        expected_reversal_cisd=None,
        continuation_protected_swing=protected,
        daily_bias=_bullish_daily_bias(),
    )

    assert take.level_taken is True
    assert ftm.level_taken is True
    assert ftm.post_sweep_closure_observed is True
    assert ftm.expected_reversal_cisd_confirmed is False
    assert ftm.confirmed is True


def test_equal_high_is_not_a_strict_liquidity_take() -> None:
    take = detect_liquidity_take(
        reference_side=CapitalizerLiquiditySideTaken.HIGH,
        reference_price=Decimal("101"),
        closed_bar=_bar("100", "101", "99", "100.5"),
    )

    assert take.level_taken is False
