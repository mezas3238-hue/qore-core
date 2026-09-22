from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    ReferenceKind,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
)


def _series(
    rows: tuple[tuple[int, int, int, int], ...],
) -> tuple[ReplayBar, ...]:
    base = datetime(2026, 1, 2, 10, 0, tzinfo=UTC)
    output: list[ReplayBar] = []
    for index, (opened, high, low, closed) in enumerate(rows):
        start = base + timedelta(minutes=15 * index)
        for offset in (0, 5, 10):
            output.append(
                ReplayBar(
                    opened_at=start + timedelta(minutes=offset),
                    open_price=opened if offset == 0 else closed,
                    high_price=high,
                    low_price=low,
                    close_price=closed,
                )
            )
    return tuple(output)


def test_wrong_direction_wick_raid_does_not_destroy_unmitigated_old_high() -> None:
    rows = _series(
        (
            (100, 102, 99, 101),
            (101, 106, 100, 105),
            (105, 103, 98, 100),
            # Wick raids 106 but closes down; no OLD_HIGH event and no body close above.
            (107, 108, 99, 101),
            # Later up-close raid can still use the same structurally unmitigated high.
            (101, 109, 100, 108),
        )
    )
    m15 = aggregate_complete_m15(rows)
    events = build_close_unmitigated_breach_groups(m15)
    base = datetime(2026, 1, 2, 10, 0, tzinfo=UTC)
    assert base + timedelta(minutes=45) not in events
    event = events[base + timedelta(minutes=60)][0]
    assert event.kind is ReferenceKind.OLD_HIGH
    assert event.references[0].price == 106


def test_body_close_above_old_high_mitigates_before_model1_event() -> None:
    rows = _series(
        (
            (100, 102, 99, 101),
            (101, 106, 100, 105),
            (105, 103, 98, 100),
            # Body close above 106 invalidates the old high.
            (104, 108, 103, 107),
            # Cannot revive it later.
            (107, 109, 105, 108),
        )
    )
    m15 = aggregate_complete_m15(rows)
    events = build_close_unmitigated_breach_groups(m15)
    base = datetime(2026, 1, 2, 10, 0, tzinfo=UTC)
    assert base + timedelta(minutes=45) not in events
    assert base + timedelta(minutes=60) not in events
