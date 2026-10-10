from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_provider_bar_revalidation_2r_v1 as audit,
)


def _dt(minute: int) -> datetime:
    return datetime(2026, 1, 5, 10, minute, tzinfo=UTC)


def _minutes(*values: int) -> set[int]:
    return {audit._minute(_dt(value)) for value in values}


def test_exact_provider_match_accepts_no_tick_calendar_gap() -> None:
    row = audit._compare(
        symbol="AUDJPY",
        session="ASIA",
        operating_date="2026-01-05",
        h1_open=_dt(0),
        entry_at=_dt(3),
        frozen_minutes=_minutes(0, 2, 3),
        provider_minutes=_minutes(0, 2, 3),
        provider_has_more=False,
    )
    assert row.state is audit.ProviderBarState.SUPPORTED_TRUE
    assert row.exact_timestamp_match is True
    assert row.frozen_missing_calendar_minutes == 1
    assert row.provider_missing_calendar_minutes == 1


def test_provider_history_drift_remains_unbound() -> None:
    row = audit._compare(
        symbol="AUDJPY",
        session="ASIA",
        operating_date="2026-01-05",
        h1_open=_dt(0),
        entry_at=_dt(3),
        frozen_minutes=_minutes(0, 2, 3),
        provider_minutes=_minutes(0, 1, 2, 3),
        provider_has_more=False,
    )
    assert row.state is audit.ProviderBarState.UNBOUND
    assert row.exact_timestamp_match is False
    assert row.provider_only_bars == 1


def test_has_more_is_hard_failure() -> None:
    row = audit._compare(
        symbol="NAS100",
        session="NEW_YORK",
        operating_date="2026-01-05",
        h1_open=_dt(0),
        entry_at=_dt(3),
        frozen_minutes=_minutes(0, 1, 2, 3),
        provider_minutes=_minutes(0, 1, 2, 3),
        provider_has_more=True,
    )
    assert row.state is audit.ProviderBarState.SUPPORTED_FALSE


def test_missing_entry_bar_is_hard_failure() -> None:
    row = audit._compare(
        symbol="XAUUSD",
        session="NEW_YORK",
        operating_date="2026-01-05",
        h1_open=_dt(0),
        entry_at=_dt(3),
        frozen_minutes=_minutes(0, 1, 2),
        provider_minutes=_minutes(0, 1, 2),
        provider_has_more=False,
    )
    assert row.state is audit.ProviderBarState.SUPPORTED_FALSE
    assert row.frozen_entry_bar_present is False
    assert row.provider_entry_bar_present is False
