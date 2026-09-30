from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_historical_bar_completeness_audit_2r_v1 as audit,
)


def _dt(minute: int) -> datetime:
    return datetime(2026, 1, 5, 10, minute, tzinfo=UTC)


def test_complete_span_is_supported_true() -> None:
    row = audit._classify(
        symbol="NAS100",
        session="NEW_YORK",
        operating_date="2026-01-05",
        h1_open=_dt(0),
        entry_at=_dt(3),
        observed_minutes={audit._minute(_dt(i)) for i in range(4)},
    )
    assert row.state is audit.BarCompletenessState.SUPPORTED_TRUE
    assert row.expected_minutes == 4
    assert row.observed_minutes == 4
    assert row.missing_calendar_minutes == 0
    assert row.entry_bar_present is True


def test_internal_provider_absence_remains_unbound() -> None:
    observed = {
        audit._minute(_dt(0)),
        audit._minute(_dt(2)),
        audit._minute(_dt(3)),
    }
    row = audit._classify(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        h1_open=_dt(0),
        entry_at=_dt(3),
        observed_minutes=observed,
    )
    assert row.state is audit.BarCompletenessState.UNBOUND
    assert row.missing_calendar_minutes == 1
    assert row.entry_bar_present is True


def test_missing_native_entry_bar_is_supported_false() -> None:
    observed = {
        audit._minute(_dt(0)),
        audit._minute(_dt(1)),
        audit._minute(_dt(2)),
    }
    row = audit._classify(
        symbol="XAUUSD",
        session="NEW_YORK",
        operating_date="2026-01-05",
        h1_open=_dt(0),
        entry_at=_dt(3),
        observed_minutes=observed,
    )
    assert row.state is audit.BarCompletenessState.SUPPORTED_FALSE
    assert row.entry_bar_present is False
    assert row.missing_calendar_minutes == 1
