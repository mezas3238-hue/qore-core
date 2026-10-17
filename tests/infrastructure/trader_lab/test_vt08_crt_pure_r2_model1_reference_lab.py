from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    ReferenceKind,
    ReferencePolicy,
    aggregate_complete_m15,
    build_first_breach_groups,
)


def _m5(minute: int, opened: int, high: int, low: int, closed: int) -> ReplayBar:
    return ReplayBar(
        opened_at=datetime(2026, 1, 2, 10, minute, tzinfo=UTC),
        open_price=opened,
        high_price=high,
        low_price=low,
        close_price=closed,
    )


def test_complete_m15_requires_exact_three_m5_bars() -> None:
    rows = (
        _m5(0, 100, 102, 99, 101),
        _m5(5, 101, 103, 100, 102),
        _m5(10, 102, 104, 101, 103),
        _m5(15, 103, 105, 102, 104),
        _m5(25, 104, 106, 103, 105),
    )
    m15 = aggregate_complete_m15(rows)
    assert len(m15) == 1
    assert m15[0].open_price == 100
    assert m15[0].high_price == 104
    assert m15[0].low_price == 99
    assert m15[0].close_price == 103


def test_first_breach_deduplicates_multiple_active_old_highs() -> None:
    base = datetime(2026, 1, 2, 10, 0, tzinfo=UTC)
    prices = (
        (100, 102, 99, 101),
        (101, 106, 100, 105),
        (105, 103, 98, 100),
        (100, 105, 99, 104),
        (104, 107, 103, 106),
    )
    rows = []
    for index, (opened, high, low, closed) in enumerate(prices):
        start = base + timedelta(minutes=15 * index)
        for offset in (0, 5, 10):
            rows.append(
                ReplayBar(
                    opened_at=start + timedelta(minutes=offset),
                    open_price=opened if offset == 0 else closed,
                    high_price=high,
                    low_price=low,
                    close_price=closed,
                )
            )
    m15 = aggregate_complete_m15(tuple(rows))
    groups = build_first_breach_groups(
        m15,
        ReferencePolicy.UNTOUCHED_SWING_STRENGTH_1,
    )
    event = groups[base + timedelta(minutes=60)][0]
    assert event.kind is ReferenceKind.OLD_HIGH
    assert event.source_candle.up_close is True
    assert len(event.references) == 1


def test_non_directional_first_breach_consumes_level_without_model1_event() -> None:
    base = datetime(2026, 1, 2, 10, 0, tzinfo=UTC)
    prices = (
        (100, 102, 99, 101),
        (101, 106, 100, 105),
        (105, 103, 98, 100),
        (107, 108, 99, 101),
        (101, 109, 100, 108),
    )
    rows = []
    for index, (opened, high, low, closed) in enumerate(prices):
        start = base + timedelta(minutes=15 * index)
        for offset in (0, 5, 10):
            rows.append(
                ReplayBar(
                    opened_at=start + timedelta(minutes=offset),
                    open_price=opened if offset == 0 else closed,
                    high_price=high,
                    low_price=low,
                    close_price=closed,
                )
            )
    m15 = aggregate_complete_m15(tuple(rows))
    groups = build_first_breach_groups(
        m15,
        ReferencePolicy.UNTOUCHED_SWING_STRENGTH_1,
    )
    assert base + timedelta(minutes=45) not in groups
    assert base + timedelta(minutes=60) not in groups
