from decimal import Decimal
from types import SimpleNamespace

from qore.infrastructure.cibo_ctrader_demo_empirical_slippage import (
    decode_ctrader_tick_series,
    signed_slippage,
)


def test_tick_series_decodes_newest_first_delta_timestamps() -> None:
    rows = (
        SimpleNamespace(timestamp=1_000_000, tick=110_000),
        SimpleNamespace(timestamp=250, tick=109_990),
        SimpleNamespace(timestamp=500, tick=109_980),
    )

    decoded = decode_ctrader_tick_series(rows)

    assert decoded == (
        (1_000_000, Decimal("1.1")),
        (999_750, Decimal("1.0999")),
        (999_250, Decimal("1.0998")),
    )


def test_buy_and_sell_slippage_sign_is_adverse_positive() -> None:
    buy = signed_slippage(
        side="BUY",
        quote_price=Decimal("100"),
        fill_price=Decimal("100.1"),
    )
    sell = signed_slippage(
        side="SELL",
        quote_price=Decimal("100"),
        fill_price=Decimal("99.9"),
    )
    favorable = signed_slippage(
        side="BUY",
        quote_price=Decimal("100"),
        fill_price=Decimal("99.9"),
    )

    assert buy[0] == Decimal("0.1")
    assert buy[1] == Decimal("10")
    assert buy[2] == Decimal("10")
    assert sell[0] == Decimal("0.1")
    assert sell[1] == Decimal("10")
    assert sell[2] == Decimal("10")
    assert favorable[1] == Decimal("-10")
    assert favorable[2] == Decimal("0")


def test_tick_lookbacks_are_bounded_and_widen_only() -> None:
    from qore.infrastructure import cibo_ctrader_demo_empirical_slippage as module

    assert module._TICK_LOOKBACK_WINDOWS_MS == (300_000, 900_000, 3_600_000)
    assert module._HISTORICAL_REQUEST_PAUSE_SECONDS >= 0.2
    assert module._HISTORICAL_REQUEST_PAUSE_SECONDS < 1
