"""Pure-method causal regression fixtures; not claims of market profitability."""

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_three_source_insidebar_replay import (
    compare_three_sources_inside_bar_context,
    count_inside_m15_bars,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


BASE = datetime(2026, 1, 2, 8, 0, tzinfo=UTC)


def _bar(index: int, high: int, low: int) -> M15Bar:
    return M15Bar(
        opened_at=BASE + timedelta(minutes=15 * index),
        open_price=100,
        high_price=high,
        low_price=low,
        close_price=100,
    )


def test_inside_c1_context_known_at_c1_close_before_c2() -> None:
    bars = (
        _bar(0, 112, 92),
        _bar(1, 110, 94),
        _bar(2, 108, 96),
        _bar(3, 115, 90),
    )
    observed = count_inside_m15_bars(
        bars,
        c1_opened_at=BASE,
        c1_closed_at=BASE + timedelta(hours=1),
    )
    assert observed.complete_c1_m15 is True
    assert observed.inside_bar_count == 2
    assert observed.inside_bar_context is True
    assert observed.observed_at == (BASE + timedelta(hours=1)).isoformat()


def test_no_inside_bars_means_absent_not_unknown() -> None:
    bars = (
        _bar(0, 111, 91),
        _bar(1, 112, 90),
        _bar(2, 113, 89),
        _bar(3, 114, 88),
    )
    observed = count_inside_m15_bars(
        bars,
        c1_opened_at=BASE,
        c1_closed_at=BASE + timedelta(hours=1),
    )
    assert observed.complete_c1_m15
    assert not observed.inside_bar_context
    assert observed.inside_bar_count == 0


def test_missing_m15_is_unknown_not_negative_context() -> None:
    bars = (_bar(0, 112, 92), _bar(1, 110, 94), _bar(3, 115, 90))
    observed = count_inside_m15_bars(
        bars,
        c1_opened_at=BASE,
        c1_closed_at=BASE + timedelta(hours=1),
    )
    assert observed.complete_c1_m15 is False
    assert observed.inside_bar_context is False
    assert observed.inside_bar_count == 0


def test_equal_high_or_equal_low_does_not_count_as_strict_inside() -> None:
    bars = (
        _bar(0, 110, 90),
        _bar(1, 110, 91),
        _bar(2, 110, 90),
        _bar(3, 111, 89),
    )
    observed = count_inside_m15_bars(
        bars,
        c1_opened_at=BASE,
        c1_closed_at=BASE + timedelta(hours=1),
    )
    assert observed.complete_c1_m15 is True
    assert observed.inside_bar_count == 0


def test_btcusd_frozen_before_any_market_data_access() -> None:
    with pytest.raises(ValueError, match="BTCUSD freeze"):
        compare_three_sources_inside_bar_context(CrtPureMarket.BTCUSD, ())


def test_zero_duration_c1_is_rejected() -> None:
    with pytest.raises(ValueError, match="positive duration"):
        count_inside_m15_bars((), c1_opened_at=BASE, c1_closed_at=BASE)
