from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import (
    _CHUNK_DAYS,
    _HISTORICAL_PAGE_COUNT,
    _REQUIRED_COVERAGE_DAYS,
    _coverage_payload,
    _validate_two_year_coverage,
)
from qore.infrastructure.ctrader_demo_lab_probe import (
    CTraderDemoLabClosedTrendbar,
    CTraderDemoLabProbeError,
)

_CHECKED_AT = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)


def _bar(period: str, opened_at: datetime, seconds: int) -> CTraderDemoLabClosedTrendbar:
    return CTraderDemoLabClosedTrendbar(
        period=period,
        opened_at=opened_at,
        closed_at=opened_at + timedelta(seconds=seconds),
        open="1.10000",
        high="1.10100",
        low="1.09900",
        close="1.10050",
    )


def _boundary_bars(*, age: timedelta) -> tuple[CTraderDemoLabClosedTrendbar, ...]:
    periods = (("M5", 300), ("M15", 900), ("H4", 14_400))
    bars: list[CTraderDemoLabClosedTrendbar] = []
    for period, seconds in periods:
        bars.extend(
            (
                _bar(period, _CHECKED_AT - age, seconds),
                _bar(period, _CHECKED_AT - timedelta(seconds=seconds), seconds),
            )
        )
    return tuple(sorted(bars, key=lambda item: (item.period, item.opened_at)))


def test_collection_window_cannot_hit_m5_page_ceiling() -> None:
    assert _CHUNK_DAYS * 24 * 60 // 5 < _HISTORICAL_PAGE_COUNT


def test_exact_730_day_boundary_is_required_without_720_day_tolerance() -> None:
    requested = _CHECKED_AT - timedelta(days=760)
    _validate_two_year_coverage(
        _boundary_bars(age=timedelta(days=_REQUIRED_COVERAGE_DAYS)),
        requested_opened_at=requested,
        checked_at=_CHECKED_AT,
    )

    with pytest.raises(CTraderDemoLabProbeError, match="less than 730"):
        _validate_two_year_coverage(
            _boundary_bars(
                age=timedelta(days=_REQUIRED_COVERAGE_DAYS, microseconds=-1)
            ),
            requested_opened_at=requested,
            checked_at=_CHECKED_AT,
        )


def test_coverage_rejects_history_outside_requested_boundary() -> None:
    with pytest.raises(CTraderDemoLabProbeError, match="predates"):
        _validate_two_year_coverage(
            _boundary_bars(age=timedelta(days=761)),
            requested_opened_at=_CHECKED_AT - timedelta(days=760),
            checked_at=_CHECKED_AT,
        )


def test_coverage_payload_records_exact_seconds_not_only_floor_days() -> None:
    bars = _boundary_bars(age=timedelta(days=730, hours=2))
    payload = _coverage_payload(bars)

    assert payload["M5"]["span_seconds"] == 730 * 86_400 + 2 * 3_600
    assert payload["M5"]["span_days"] == 730
    assert payload["M5"]["observed_gap_count"] == 1
    assert payload["M5"]["observed_gap_seconds"] == 730 * 86_400 + 2 * 3_600 - 600
    assert "market closures" in str(payload["M5"]["gap_policy"])
