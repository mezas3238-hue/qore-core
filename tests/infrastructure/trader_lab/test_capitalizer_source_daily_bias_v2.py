from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_source_daily_bias_v2 import (
    CapitalizerDailyBiasResolution,
    derive_daily_bias,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
    detect_candle2_reversal_closure,
)


def _bar(open_: str, high: str, low: str, close: str) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_daily_bias_resolves_only_from_valid_htf_closure_at_poi() -> None:
    closure = detect_candle2_reversal_closure(
        previous=_bar("100", "102", "98", "99"),
        candle2=_bar("99", "101", "97", "99.5"),
        point_of_interest_present=True,
    )
    assert closure is not None

    bias = derive_daily_bias(closure)

    assert bias.resolution is CapitalizerDailyBiasResolution.CONFIRMED
    assert bias.direction is CapitalizerSourceDirection.BULLISH
    assert bias.lower_timeframe_created_bias is False
    assert bias.numeric_indicator_used is False
    assert bias.grants_entry_authority is False


def test_daily_bias_stays_unresolved_when_closure_lacks_poi() -> None:
    closure = detect_candle2_reversal_closure(
        previous=_bar("100", "102", "98", "99"),
        candle2=_bar("99", "101", "97", "99.5"),
        point_of_interest_present=False,
    )
    assert closure is not None

    bias = derive_daily_bias(closure)

    assert bias.resolution is CapitalizerDailyBiasResolution.UNRESOLVED
    assert bias.direction is None
