from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_perception_bar_completeness_audit_2r_v2 as audit,
)


def test_required_opens_are_exact_closed_minutes() -> None:
    start = datetime(2026, 1, 5, 2, 0, tzinfo=UTC)
    entry = datetime(2026, 1, 5, 2, 3, tzinfo=UTC)
    assert audit._required_opens(start, entry) == (
        start,
        start + timedelta(minutes=1),
        start + timedelta(minutes=2),
    )


def test_required_opens_reject_non_positive_window() -> None:
    at = datetime(2026, 1, 5, 2, 0, tzinfo=UTC)
    try:
        audit._required_opens(at, at)
    except ValueError as exc:
        assert "positive minutes" in str(exc)
    else:
        raise AssertionError("zero-length decision window must fail closed")


def test_bar_completeness_row_never_infers_quote_freshness() -> None:
    row = audit.PerceptionBarCompletenessRow(
        symbol="AUDJPY",
        session="ASIA",
        operating_date="2026-01-05",
        entry_at="2026-01-05T02:03:00+00:00",
        h1_open="2026-01-05T02:00:00+00:00",
        expected_m1_bars=3,
        observed_m1_bars=3,
        missing_m1_bars=0,
        bars_complete="SUPPORTED_TRUE",
    )
    assert row.quote_fresh == "UNBOUND"
    assert row.current_trade_outcome_visible_to_binding is False
