from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.certified_trader_telemetry import (
    HistoricalTrade,
    LiveWeekObservation,
    TelemetryStatus,
    compare_live_week,
    compute_weekly_telemetry,
    load_certified_baselines,
    nominal_equity_percent,
)

_BASELINE = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "research"
    / "CERTIFIED-TRADER-WEEKLY-TELEMETRY-v1.json"
)


def _trade(
    entry: datetime,
    *,
    exit_after_hours: int = 1,
    net_r: str,
) -> HistoricalTrade:
    return HistoricalTrade(
        entry_at=entry,
        exit_at=entry + timedelta(hours=exit_after_hours),
        net_r=Decimal(net_r),
    )


def test_compute_weekly_telemetry_is_new_york_calendar_based() -> None:
    start = datetime(2026, 1, 5, 0, 0, tzinfo=UTC)
    end = datetime(2026, 1, 26, 0, 0, tzinfo=UTC)
    trades = (
        _trade(datetime(2026, 1, 5, 14, 0, tzinfo=UTC), net_r="-1"),
        _trade(datetime(2026, 1, 6, 14, 0, tzinfo=UTC), net_r="-0.5"),
        _trade(datetime(2026, 1, 12, 14, 0, tzinfo=UTC), net_r="2"),
        _trade(datetime(2026, 1, 12, 16, 0, tzinfo=UTC), net_r="-3"),
        _trade(datetime(2026, 1, 20, 14, 0, tzinfo=UTC), net_r="1"),
    )
    metrics = compute_weekly_telemetry(
        trades,
        window_start=start,
        window_end=end,
    )
    assert metrics.trades == 5
    assert metrics.calendar_weeks == 4
    assert metrics.active_weeks == 3
    assert metrics.zero_entry_weeks == 1
    assert metrics.average_entries_per_week == Decimal("1.25")
    assert metrics.median_entries_per_week == Decimal("1.5")
    assert metrics.p95_entries_per_week == 2
    assert metrics.max_entries_per_week == 2
    assert metrics.max_entries_per_day == 2
    assert metrics.worst_closed_day_r == Decimal("-1")
    assert metrics.worst_closed_week_r == Decimal("-1.5")


def test_canonical_r34_r38_baselines_are_frozen() -> None:
    baselines = load_certified_baselines(_BASELINE)
    assert set(baselines) == {"R34_XAUUSD", "R38_EURUSD"}

    r34 = baselines["R34_XAUUSD"]
    assert r34.identity == "TURTLE_SOUP_XAUUSD_R34"
    assert r34.symbol == "XAUUSD"
    assert r34.metrics.trades == 367
    assert r34.metrics.calendar_weeks == 105
    assert r34.metrics.average_entries_per_week == Decimal(
        "3.49523809523809523809523809524"
    )
    assert r34.metrics.median_entries_per_week == Decimal("3")
    assert r34.metrics.p95_entries_per_week == 6
    assert r34.metrics.max_entries_per_week == 9
    assert r34.metrics.zero_entry_weeks == 2
    assert r34.metrics.worst_closed_day_r == Decimal("-2.7500")
    assert r34.metrics.worst_closed_week_r == Decimal(
        "-4.500000000000000000000000000"
    )
    assert (
        r34.source_trade_ledger_sha256
        == "784185b4f3f9db079780715d311c38058124f8643562dd7ad7d09f4f8389db2e"
    )

    r38 = baselines["R38_EURUSD"]
    assert r38.identity == "TURTLE_SOUP_EURUSD_R38"
    assert r38.symbol == "EURUSD"
    assert r38.metrics.trades == 366
    assert r38.metrics.calendar_weeks == 105
    assert r38.metrics.average_entries_per_week == Decimal(
        "3.48571428571428571428571428571"
    )
    assert r38.metrics.median_entries_per_week == Decimal("3")
    assert r38.metrics.p95_entries_per_week == 7
    assert r38.metrics.max_entries_per_week == 8
    assert r38.metrics.zero_entry_weeks == 1
    assert r38.metrics.worst_closed_day_r == Decimal("-2.4200")
    assert r38.metrics.worst_closed_week_r == Decimal("-2.4200")
    assert (
        r38.source_trade_ledger_sha256
        == "61746b6866dce66c2b522be56016c5d5b786821704f71f947b4cf2337aeefc9a"
    )


def test_live_comparison_is_advisory_and_detects_envelope_breaks() -> None:
    baseline = load_certified_baselines(_BASELINE)["R38_EURUSD"]
    normal = compare_live_week(
        baseline,
        LiveWeekObservation(
            entries=5,
            closed_r=Decimal("-1"),
            worst_closed_day_r=Decimal("-1"),
        ),
    )
    assert normal.frequency_status is TelemetryStatus.WITHIN_BASELINE
    assert normal.outside_historical_envelope is False
    assert normal.advisory_only is True

    warning = compare_live_week(
        baseline,
        LiveWeekObservation(
            entries=9,
            closed_r=Decimal("-3"),
            worst_closed_day_r=Decimal("-2.5"),
        ),
    )
    assert warning.frequency_status is TelemetryStatus.ABOVE_HISTORICAL_MAX_FREQUENCY
    assert warning.weekly_loss_status is TelemetryStatus.WORSE_THAN_HISTORICAL_WEEK
    assert warning.daily_loss_status is TelemetryStatus.WORSE_THAN_HISTORICAL_DAY
    assert warning.outside_historical_envelope is True
    assert warning.advisory_only is True


def test_nominal_equity_translation_matches_current_0_20pct_per_r_reference() -> None:
    assert nominal_equity_percent(Decimal("-2.75")) == Decimal("-0.55000")
    assert nominal_equity_percent(Decimal("-4.50")) == Decimal("-0.90000")
    assert nominal_equity_percent(Decimal("-2.42")) == Decimal("-0.48400")
