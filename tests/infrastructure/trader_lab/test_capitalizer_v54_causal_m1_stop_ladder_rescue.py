from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import CapitalizerM1Bar
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_v54_causal_m1_stop_ladder_rescue import (
    _choose_rescue,
    _confirmed_execution_pivots,
)


def test_stop_ladder_uses_newest_eligible_deeper_pivot() -> None:
    at = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    pivots = (
        (at, Decimal("95")),
        (at.replace(minute=1), Decimal("99.5")),
        (at.replace(minute=2), Decimal("99.8")),
    )
    rescue = _choose_rescue(
        pivots,
        entry_price=Decimal("100"),
        thesis_stop_price=Decimal("94"),
        recent_range_ticks=Decimal("10"),
        tick=Decimal("0.01"),
        target_prices=(Decimal("104"), Decimal("106")),
    )
    assert rescue is not None
    _, stop, noise, target, reward_r = rescue
    # Latest 99.8 stop is only 2x local noise and must be skipped.
    # The immediately older 99.5 causal pivot is 5x noise and is admissible.
    assert stop == Decimal("99.5")
    assert noise == Decimal("5")
    assert target == Decimal("104")
    assert reward_r == Decimal("8")


def test_stop_ladder_never_uses_thesis_scale_or_wider_pivot() -> None:
    at = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    rescue = _choose_rescue(
        ((at, Decimal("93")),),
        entry_price=Decimal("100"),
        thesis_stop_price=Decimal("94"),
        recent_range_ticks=Decimal("10"),
        tick=Decimal("0.01"),
        target_prices=(Decimal("110"),),
    )
    assert rescue is None


def _bar(
    minute: int,
    *,
    high: str,
    low: str,
    close: str = "100",
) -> CapitalizerM1Bar:
    opened = datetime(2026, 1, 5, 12, minute, tzinfo=UTC)
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=opened,
        closed_at=opened.replace(minute=minute + 1),
        open=Decimal("100"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=1,
        digits=2,
    )


def test_confirmed_stop_pivot_must_remain_intact_until_entry() -> None:
    bars = (
        _bar(0, high="101", low="100"),
        _bar(1, high="100.5", low="99"),
        _bar(2, high="101", low="100"),
        _bar(3, high="100.2", low="98.9"),
        _bar(4, high="101", low="99.6"),
    )
    pivots = _confirmed_execution_pivots(
        bars,
        side=CapitalizerSide.LONG,
        setup_confirmed_at=bars[0].opened_at,
        decision_at=bars[-1].closed_at,
        entry_price=Decimal("100.5"),
    )
    # The 99 pivot was confirmed by minute 2 but breached at minute 3,
    # so it no longer exists as an execution invalidation at entry.
    assert all(price != Decimal("99") for _, price in pivots)
