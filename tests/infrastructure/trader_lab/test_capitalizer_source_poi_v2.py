from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
)
from qore.infrastructure.trader_lab.capitalizer_source_poi_v2 import (
    CapitalizerSourcePOIKind,
    any_source_poi_interaction,
    detect_external_liquidity_swing,
    detect_fair_value_gap,
)


def _bar(open_: str, high: str, low: str, close: str) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_bullish_fvg_requires_non_overlap_between_candle_one_high_and_three_low() -> None:
    poi = detect_fair_value_gap(
        candle1=_bar("100", "101", "99", "100.5"),
        candle2=_bar("100.5", "103", "100", "102.5"),
        candle3=_bar("102", "104", "102", "103"),
    )

    assert poi is not None
    assert poi.kind is CapitalizerSourcePOIKind.BULLISH_FVG
    assert poi.lower_price == Decimal("101")
    assert poi.upper_price == Decimal("102")


def test_overlapping_three_candle_structure_is_not_fvg() -> None:
    poi = detect_fair_value_gap(
        candle1=_bar("100", "102", "99", "101"),
        candle2=_bar("101", "103", "100", "102"),
        candle3=_bar("101.5", "104", "101", "103"),
    )

    assert poi is None


def test_external_liquidity_swing_uses_lower_highs_or_higher_lows_on_each_side() -> None:
    high = detect_external_liquidity_swing(
        left=_bar("100", "102", "99", "101"),
        center=_bar("101", "105", "100", "103"),
        right=_bar("103", "104", "101", "102"),
    )
    low = detect_external_liquidity_swing(
        left=_bar("100", "102", "98", "99"),
        center=_bar("99", "101", "95", "97"),
        right=_bar("97", "103", "96", "102"),
    )

    assert high is not None
    assert high.kind is CapitalizerSourcePOIKind.SWING_HIGH
    assert high.lower_price == Decimal("105")
    assert low is not None
    assert low.kind is CapitalizerSourcePOIKind.SWING_LOW
    assert low.lower_price == Decimal("95")


def test_completed_bar_must_trade_into_poi_to_supply_context() -> None:
    poi = detect_fair_value_gap(
        candle1=_bar("100", "101", "99", "100.5"),
        candle2=_bar("100.5", "103", "100", "102.5"),
        candle3=_bar("102", "104", "102", "103"),
    )
    assert poi is not None

    assert any_source_poi_interaction(
        bar=_bar("103", "103.5", "101.5", "102"),
        pois=(poi,),
    ) is True
    assert any_source_poi_interaction(
        bar=_bar("104", "105", "103", "104.5"),
        pois=(poi,),
    ) is False
