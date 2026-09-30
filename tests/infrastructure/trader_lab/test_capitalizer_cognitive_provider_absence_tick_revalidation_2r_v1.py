from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_provider_absence_tick_revalidation_2r_v1 as audit,
)


def _minute(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)


def test_missing_minutes_reconstruct_exact_provider_absences() -> None:
    row = {
        "h1_open": "2025-10-22T00:00:00+00:00",
        "entry_at": "2025-10-22T00:05:00+00:00",
        "missing_calendar_minutes": 2,
    }
    observed = {
        int(_minute("2025-10-22T00:00:00+00:00").timestamp() // 60),
        int(_minute("2025-10-22T00:03:00+00:00").timestamp() // 60),
        int(_minute("2025-10-22T00:04:00+00:00").timestamp() // 60),
        int(_minute("2025-10-22T00:05:00+00:00").timestamp() // 60),
    }
    assert audit._missing_minutes(row, observed=observed) == (
        _minute("2025-10-22T00:01:00+00:00"),
        _minute("2025-10-22T00:02:00+00:00"),
    )


def test_missing_entry_minute_is_not_reclassifiable() -> None:
    row = {
        "h1_open": "2025-10-22T00:00:00+00:00",
        "entry_at": "2025-10-22T00:02:00+00:00",
        "missing_calendar_minutes": 1,
    }
    observed = {
        int(_minute("2025-10-22T00:00:00+00:00").timestamp() // 60),
        int(_minute("2025-10-22T00:01:00+00:00").timestamp() // 60),
    }
    try:
        audit._missing_minutes(row, observed=observed)
    except ValueError as exc:
        assert "entry minute" in str(exc)
    else:
        raise AssertionError("missing entry bar must fail closed")


def test_no_tick_evidence_is_not_outcome_aware() -> None:
    row = audit.MissingMinuteTickEvidence(
        symbol="AUDJPY",
        entry_at="2025-10-22T00:55:00+00:00",
        minute="2025-10-22T00:01:00+00:00",
        bid_ticks=0,
        ask_ticks=0,
        bid_has_more=False,
        ask_has_more=False,
        provider_no_ticks=True,
        contradiction_ticks_without_trendbar=False,
    )
    assert row.current_trade_outcome_visible_to_audit is False
    assert row.provider_no_ticks is True
