from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import CapitalizerM1Bar
from qore.infrastructure.trader_lab.capitalizer_crt_h1_m3_m1_ote_1y_v5 import (
    IDENTITY,
    MATRIX_IDENTITY,
    OTEZone,
    _rejection,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide


def _bar(
    *,
    open_price: str,
    high: str,
    low: str,
    close: str,
) -> CapitalizerM1Bar:
    now = datetime(2026, 9, 22, 13, 0, tzinfo=UTC)
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=now,
        closed_at=now,
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=None,
        digits=5,
    )


def test_v5_identity_is_separate() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_CRT_H1_M3_M1_OTE_1Y_V5"
    assert MATRIX_IDENTITY == "QORE_CAPITALIZER_NINE_MARKET_CRT_H1_M3_M1_OTE_1Y_V5"


def test_long_rejection_requires_bullish_body_and_lower_wick() -> None:
    bar = _bar(
        open_price="1.1000",
        high="1.1020",
        low="1.0980",
        close="1.1010",
    )
    assert _rejection(bar, side=CapitalizerSide.LONG) is True


def test_short_rejection_requires_bearish_body_and_upper_wick() -> None:
    bar = _bar(
        open_price="1.1010",
        high="1.1030",
        low="1.0990",
        close="1.1000",
    )
    assert _rejection(bar, side=CapitalizerSide.SHORT) is True


def test_ote_zone_contains_sweet_spot() -> None:
    zone = OTEZone(
        impulse_start=Decimal("100"),
        impulse_end=Decimal("110"),
        level_050=Decimal("105"),
        level_062=Decimal("103.8"),
        level_0705=Decimal("102.95"),
        level_079=Decimal("102.1"),
        zone_low=Decimal("102.1"),
        zone_high=Decimal("103.8"),
    )
    assert zone.zone_low < zone.level_0705 < zone.zone_high
