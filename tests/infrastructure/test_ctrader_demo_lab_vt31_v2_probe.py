from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.ctrader_demo_lab_probe import (
    CTraderDemoLabClosedTrendbar,
    CTraderDemoLabProbeError,
)
from qore.infrastructure.ctrader_demo_lab_vt31_v2_probe import (
    _REQUIRED_COVERAGE_DAYS,
    _coverage_payload,
    _validate_m1_coverage,
)

_CHECKED_AT = datetime(2026, 9, 11, 12, 0, tzinfo=UTC)


def _bar(opened_at: datetime, *, period: str = "M1") -> CTraderDemoLabClosedTrendbar:
    return CTraderDemoLabClosedTrendbar(
        period=period,
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=1),
        open="100.0",
        high="101.0",
        low="99.0",
        close="100.5",
    )


def _boundary_bars(*, age: timedelta) -> tuple[CTraderDemoLabClosedTrendbar, ...]:
    return (
        _bar(_CHECKED_AT - age),
        _bar(_CHECKED_AT - timedelta(minutes=1)),
    )


def test_exact_two_year_m1_span_is_required() -> None:
    requested = _CHECKED_AT - timedelta(days=760)
    _validate_m1_coverage(
        _boundary_bars(age=timedelta(days=_REQUIRED_COVERAGE_DAYS)),
        requested_opened_at=requested,
        checked_at=_CHECKED_AT,
    )

    with pytest.raises(CTraderDemoLabProbeError, match="less than 730"):
        _validate_m1_coverage(
            _boundary_bars(
                age=timedelta(days=_REQUIRED_COVERAGE_DAYS, microseconds=-1)
            ),
            requested_opened_at=requested,
            checked_at=_CHECKED_AT,
        )


def test_m1_contract_rejects_wrong_period_and_duplicates() -> None:
    requested = _CHECKED_AT - timedelta(days=760)
    with pytest.raises(CTraderDemoLabProbeError, match="only M1"):
        _validate_m1_coverage(
            (
                _bar(_CHECKED_AT - timedelta(days=730), period="M5"),
                _bar(_CHECKED_AT - timedelta(minutes=1)),
            ),
            requested_opened_at=requested,
            checked_at=_CHECKED_AT,
        )

    first = _bar(_CHECKED_AT - timedelta(days=730))
    with pytest.raises(CTraderDemoLabProbeError, match="duplicate"):
        _validate_m1_coverage(
            (first, first, _bar(_CHECKED_AT - timedelta(minutes=1))),
            requested_opened_at=requested,
            checked_at=_CHECKED_AT,
        )


def test_m1_contract_rejects_future_and_stale_boundary() -> None:
    requested = _CHECKED_AT - timedelta(days=760)
    with pytest.raises(CTraderDemoLabProbeError, match="closed bars"):
        _validate_m1_coverage(
            (
                _bar(_CHECKED_AT - timedelta(days=730)),
                _bar(_CHECKED_AT),
            ),
            requested_opened_at=requested,
            checked_at=_CHECKED_AT,
        )

    with pytest.raises(CTraderDemoLabProbeError, match="stale"):
        _validate_m1_coverage(
            (
                _bar(_CHECKED_AT - timedelta(days=742)),
                _bar(_CHECKED_AT - timedelta(days=11)),
            ),
            requested_opened_at=requested,
            checked_at=_CHECKED_AT,
        )


def test_coverage_payload_records_provider_gaps_without_inventing_candles() -> None:
    bars = (
        _bar(_CHECKED_AT - timedelta(minutes=3)),
        _bar(_CHECKED_AT - timedelta(minutes=1)),
    )

    payload = _coverage_payload(bars)

    assert payload["bar_count"] == 2
    assert payload["observed_gap_count"] == 1
    assert payload["observed_gap_seconds"] == 60
    assert "not invented" in str(payload["gap_policy"])
