from datetime import UTC, datetime

from qore.infrastructure.trader_lab.cibo_market_atlas_m5_availability_v1 import (
    ProbeWindow,
    first_contiguous_month,
    month_grid,
    year_grid,
)


def _dt(year: int, month: int, day: int = 1) -> datetime:
    return datetime(year, month, day, tzinfo=UTC)


def test_month_grid_spans_calendar_months_without_overlap() -> None:
    windows = month_grid(_dt(2025, 11, 16), _dt(2026, 2, 10))
    assert windows == (
        (_dt(2025, 11), _dt(2025, 12)),
        (_dt(2025, 12), _dt(2026, 1)),
        (_dt(2026, 1), _dt(2026, 2)),
        (_dt(2026, 2), _dt(2026, 2, 10)),
    )


def test_year_grid_spans_calendar_years_without_overlap() -> None:
    windows = year_grid(_dt(2024, 6), _dt(2026, 9, 16))
    assert windows == (
        (_dt(2024, 1), _dt(2025, 1)),
        (_dt(2025, 1), _dt(2026, 1)),
        (_dt(2026, 1), _dt(2026, 9, 16)),
    )


def test_first_contiguous_month_skips_non_contiguous_earlier_history() -> None:
    windows = (
        ProbeWindow(_dt(2010, 1), _dt(2010, 2), True, _dt(2010, 1, 4), _dt(2010, 1, 29), 10),
        ProbeWindow(_dt(2010, 2), _dt(2010, 3), False, None, None, 0),
        ProbeWindow(_dt(2010, 3), _dt(2010, 4), True, _dt(2010, 3, 1), _dt(2010, 3, 31), 10),
        ProbeWindow(_dt(2010, 4), _dt(2010, 5), True, _dt(2010, 4, 1), _dt(2010, 4, 30), 10),
    )
    assert first_contiguous_month(windows) == _dt(2010, 3)


def test_first_contiguous_month_is_none_without_observations() -> None:
    windows = (
        ProbeWindow(_dt(2010, 1), _dt(2010, 2), False, None, None, 0),
        ProbeWindow(_dt(2010, 2), _dt(2010, 3), False, None, None, 0),
    )
    assert first_contiguous_month(windows) is None
