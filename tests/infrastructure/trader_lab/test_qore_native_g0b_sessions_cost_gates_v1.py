"""QORE Native G0B must be descriptive and fail closed."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_g0b_sessions_cost_gates_v1 as g


def at(iso: str) -> datetime:
    return datetime.fromisoformat(iso).astimezone(UTC)


def test_continuous_day_is_not_a_certified_broker_session() -> None:
    start = at("2026-03-10T00:00:00+00:00")
    out = g.utc_m5_census(start + timedelta(minutes=5 * i) for i in range(288))
    assert out["bars"] == 288
    assert out["utc_days_with_288_m5"] == 1
    assert out["h4_d1_broker_candles_verified"] is False
    assert out["exchange_holiday_and_expected_closures_verified"] is False
    assert out["unclassified_discontinuity_runs"] == 0


def test_dst_fallback_uses_distinct_offsets_not_ambiguous_local_hour() -> None:
    out = g.utc_m5_census([
        at("2026-11-01T05:55:00+00:00"),
        at("2026-11-01T06:00:00+00:00"),
    ])
    assert out["new_york_utc_offset_bar_counts"] == {"-0400": 1, "-0500": 1}
    assert len(out["new_york_weekday_clock_offset_bar_counts"]) == 2
    assert out["unclassified_discontinuity_runs"] == 0
    assert out["broker_rollover_and_dst_verified"] is False


def test_weekend_absence_is_unclassified_not_corrupted_or_tradable() -> None:
    out = g.utc_m5_census([
        at("2026-10-09T21:55:00+00:00"),
        at("2026-10-11T22:00:00+00:00"),
    ])
    assert out["unclassified_discontinuity_runs"] == 1
    assert out["max_unclassified_gap_minutes"] > 1000
    assert out["gap_examples_first_20"][0]["classification"] == (
        "UNKNOWN_CLOSURE_OR_FEED_GAP"
    )


@pytest.mark.parametrize("instants", [
    [at("2026-03-10T00:01:00+00:00")],
    [at("2026-03-10T00:00:00+00:00")] * 2,
    [at("2026-03-10T00:05:00+00:00"), at("2026-03-10T00:00:00+00:00")],
    [datetime(2026, 3, 10, 0, 0)],
    [],
])
def test_invalid_timestamp_sequences_fail_closed(instants: list[datetime]) -> None:
    with pytest.raises(ValueError):
        g.utc_m5_census(instants)


def test_no_cost_or_calendar_claims_mean_no_economic_gate() -> None:
    out = g.evidence_gate(None)
    assert out["missing_source_claims"]
    assert out["status"] == "BLOCKED_MISSING_SOURCE_EVIDENCE"
    assert out["g1_net_authorized"] is False
    assert out["cost_pit_verified"] is False


def test_even_complete_self_asserted_source_claims_are_not_verification() -> None:
    fields = g.evidence_gate(None)["missing_source_claims"]
    out = g.evidence_gate(dict.fromkeys(fields, "f" * 64))
    assert not out["missing_source_claims"]
    assert out["status"] == "SOURCE_CLAIMS_NEED_INDEPENDENT_VERIFICATION"
    assert out["g1_net_authorized"] is False


def test_g0b_file_never_reads_market_outcomes() -> None:
    source = Path(g.__file__).read_text(encoding="utf-8")
    forbidden = (
        'row["open_relative"]', 'row["high_relative"]', 'row["low_relative"]',
        'row["close_relative"]', 'row["volume"]', "profit_factor(",
        "sharpe_ratio(", "backtest(", "place_order(", "ctrader_open_api_client",
    )
    assert all(item not in source for item in forbidden)


def test_frozen_twelve_remain_identical_to_sha_g0() -> None:
    assert len(g.g0.SYMBOLS) == 12
    assert g.g0.SOURCE_RUN == 35166210458
    assert g.G1_STATUS == "BLOCKED_BROKER_SESSIONS_COSTS_AND_NEWS_ASOF"
