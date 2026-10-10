from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import CapitalizerM1Bar
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_ttrades_cisd_m1_entry_1y_replay_v1 import (
    ENTRY_CLOSE,
    ENTRY_RETEST,
    VARIANTS,
    _detect_cisd_after_signal,
    _entry_for_variant,
)


def _bar(
    minute: int,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> CapitalizerM1Bar:
    opened = datetime(2026, 1, 1, 12, minute, tzinfo=UTC)
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=None,
        digits=5,
    )


def _bullish_cisd_bars() -> tuple[CapitalizerM1Bar, ...]:
    return (
        _bar(0, open_="1.1000", high="1.1010", low="1.0995", close="1.1005"),
        _bar(1, open_="1.1005", high="1.1012", low="1.0990", close="1.1008"),
        _bar(2, open_="1.1008", high="1.1010", low="1.0995", close="1.1000"),
        _bar(3, open_="1.1000", high="1.1002", low="1.0988", close="1.0992"),
        _bar(4, open_="1.0992", high="1.1015", low="1.0990", close="1.1012"),
        _bar(5, open_="1.1012", high="1.1014", low="1.0997", close="1.1004"),
    )


def test_ttrades_variants_are_predeclared() -> None:
    assert VARIANTS == ("CLOSE", "RETEST")
    assert ENTRY_CLOSE != ENTRY_RETEST


def test_bullish_cisd_requires_sweep_and_close_through_down_close_series() -> None:
    bars = _bullish_cisd_bars()
    setup, reason = _detect_cisd_after_signal(
        bars,
        signal_at=bars[0].opened_at,
        side=CapitalizerSide.LONG,
        target=Decimal("1.1100"),
    )
    assert reason == "TTRADES_CISD_CONFIRMED"
    assert setup is not None
    assert setup.swept_level == Decimal("1.0990")
    assert setup.series_open == Decimal("1.1008")
    assert setup.confirmation_index == 4


def test_close_and_retest_entries_use_same_confirmed_cisd() -> None:
    bars = _bullish_cisd_bars()
    setup, _ = _detect_cisd_after_signal(
        bars,
        signal_at=bars[0].opened_at,
        side=CapitalizerSide.LONG,
        target=Decimal("1.1100"),
    )
    assert setup is not None

    close_index, close_price, _ = _entry_for_variant(
        bars,
        setup=setup,
        side=CapitalizerSide.LONG,
        stop=Decimal("1.0950"),
        target=Decimal("1.1100"),
        variant="CLOSE",
    )
    assert close_index == 4
    assert close_price == Decimal("1.1012")

    retest_index, retest_price, _ = _entry_for_variant(
        bars,
        setup=setup,
        side=CapitalizerSide.LONG,
        stop=Decimal("1.0950"),
        target=Decimal("1.1100"),
        variant="RETEST",
    )
    assert retest_index == 5
    assert retest_price == Decimal("1.1010")


def test_ttrades_route_does_not_require_fvg_or_ict_mss() -> None:
    bars = _bullish_cisd_bars()[:-1]
    setup, _ = _detect_cisd_after_signal(
        bars,
        signal_at=bars[0].opened_at,
        side=CapitalizerSide.LONG,
        target=Decimal("1.1100"),
    )
    assert setup is not None
