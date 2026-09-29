from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab import (
    capitalizer_cross_market_event_time_m1_coverage_census_v1 as census,
)


def _dt(minute: int, second: int = 0) -> datetime:
    return datetime(2024, 1, 1, 12, minute, second, tzinfo=UTC)


def test_event_time_age_uses_latest_completed_bar_only() -> None:
    completed = (_dt(0), _dt(1), _dt(3))
    entrants = (_dt(1, 30), _dt(4))

    result = census.summarize_event_time_ages(
        entrant_times=entrants,
        completed_bar_times=completed,
    )

    assert result.entrant_count == 2
    assert result.prior_bar_count == 2
    assert result.missing_prior_bar_count == 0
    assert result.p50_age_seconds == 30
    assert result.p95_age_seconds == 60
    assert result.p99_age_seconds == 60
    assert result.max_age_seconds == 60
    assert result.within_60s == 2
    assert result.all_entrants_have_prior_bar is True
    assert result.future_bar_used is False


def test_event_time_age_records_missing_prior_history() -> None:
    completed = (_dt(2),)
    entrants = (_dt(1), _dt(3))

    result = census.summarize_event_time_ages(
        entrant_times=entrants,
        completed_bar_times=completed,
    )

    assert result.entrant_count == 2
    assert result.prior_bar_count == 1
    assert result.missing_prior_bar_count == 1
    assert result.max_age_seconds == 60
    assert result.all_entrants_have_prior_bar is False


def test_event_time_age_does_not_treat_descriptive_threshold_as_gate() -> None:
    completed = (_dt(0),)
    entrants = (_dt(20),)

    result = census.summarize_event_time_ages(
        entrant_times=entrants,
        completed_bar_times=completed,
    )

    assert result.max_age_seconds == 20 * 60
    assert result.within_60s == 0
    assert result.within_300s == 0
    assert result.within_900s == 0
    assert result.prior_bar_count == 1


def test_event_time_age_rejects_unsorted_inputs() -> None:
    try:
        census.summarize_event_time_ages(
            entrant_times=(_dt(2), _dt(1)),
            completed_bar_times=(_dt(0),),
        )
    except ValueError as exc:
        assert "entrant_times must be sorted" in str(exc)
    else:
        raise AssertionError("expected sorted entrant failure")


def test_event_time_age_accepts_exact_entry_close_without_future_use() -> None:
    close = _dt(5)
    result = census.summarize_event_time_ages(
        entrant_times=(close,),
        completed_bar_times=(close - timedelta(minutes=1), close),
    )

    assert result.p50_age_seconds == 0
    assert result.future_bar_used is False
