from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.trader_lab.turtle_soup_candidate_r1_collection_windows import (
    build_overlapped_collection_windows,
)


def test_d1_windows_overlap_by_one_full_bar_and_recover_crossing_bar() -> None:
    opened = datetime(2023, 9, 17, 21, tzinfo=UTC)
    checked = opened + timedelta(days=200)
    bar_span = timedelta(days=1)
    windows = build_overlapped_collection_windows(
        opened_at=opened,
        checked_at=checked,
        chunk_span=timedelta(days=90),
        bar_span=bar_span,
    )

    first_open, first_end = windows[0]
    second_open, second_end = windows[1]
    assert first_open == opened
    assert second_open == first_end - bar_span
    assert second_end > first_end

    crossing_open = first_end - timedelta(hours=12)
    crossing_close = crossing_open + bar_span
    assert crossing_open >= second_open
    assert crossing_close <= second_end
    assert crossing_close > first_end


def test_m15_windows_overlap_by_one_full_bar_and_recover_crossing_bar() -> None:
    opened = datetime(2023, 9, 17, 21, tzinfo=UTC)
    checked = opened + timedelta(days=40)
    bar_span = timedelta(minutes=15)
    windows = build_overlapped_collection_windows(
        opened_at=opened,
        checked_at=checked,
        chunk_span=timedelta(days=14),
        bar_span=bar_span,
    )

    first_end = windows[0][1]
    second_open, second_end = windows[1]
    assert second_open == first_end - bar_span

    crossing_open = first_end - timedelta(minutes=5)
    crossing_close = crossing_open + bar_span
    assert crossing_open >= second_open
    assert crossing_close <= second_end
    assert crossing_close > first_end


def test_windows_end_exactly_at_checked_at_and_advance_strictly() -> None:
    opened = datetime(2026, 1, 1, tzinfo=UTC)
    checked = datetime(2026, 3, 20, 12, 34, tzinfo=UTC)
    windows = build_overlapped_collection_windows(
        opened_at=opened,
        checked_at=checked,
        chunk_span=timedelta(days=14),
        bar_span=timedelta(minutes=15),
    )
    assert windows[-1][1] == checked
    assert all(
        right[0] > left[0]
        for left, right in zip(windows, windows[1:], strict=False)
    )


@pytest.mark.parametrize(
    ("opened", "checked", "chunk_span", "bar_span"),
    (
        (
            datetime(2026, 1, 1),
            datetime(2026, 2, 1, tzinfo=UTC),
            timedelta(days=14),
            timedelta(minutes=15),
        ),
        (
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 1, 1, tzinfo=UTC),
            timedelta(days=14),
            timedelta(minutes=15),
        ),
        (
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 2, 1, tzinfo=UTC),
            timedelta(0),
            timedelta(minutes=15),
        ),
        (
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 2, 1, tzinfo=UTC),
            timedelta(days=1),
            timedelta(days=1),
        ),
    ),
)
def test_invalid_window_contracts_fail_closed(
    opened: datetime,
    checked: datetime,
    chunk_span: timedelta,
    bar_span: timedelta,
) -> None:
    with pytest.raises(CTraderDemoLabProbeError):
        build_overlapped_collection_windows(
            opened_at=opened,
            checked_at=checked,
            chunk_span=chunk_span,
            bar_span=bar_span,
        )
