"""Causal contract tests for frozen London reentry G1. No live/OAuth."""
from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_london_reentry_g1_dev_v1 as g


def dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso).astimezone(UTC)


def bar(opened: datetime, o: float = 100.0, h: float = 100.2,
        l: float = 99.8, c: float = 100.0) -> g.Bar:
    return g.Bar(opened=opened, o=o, h=h, l=l, c=c)


def test_frozen_study_contract_and_no_tuning() -> None:
    assert g.SYMBOLS == ("EURJPY", "USDCHF")
    assert (g.START, g.END_EXCLUSIVE) == (date(2020, 9, 24), date(2023, 9, 23))
    assert g.MIN_TRADES_PER_CELL == 50
    assert g.BOOTSTRAPS == 2000
    assert g.RESERVED_CUTOFF == dt("2023-09-24T23:45:00+00:00")
    assert 0.1 * 2 == pytest.approx(0.2)


def test_london_0800_local_tracks_bst_transition() -> None:
    assert g.london_utc(date(2023, 3, 24), 480) == dt("2023-03-24T08:00:00Z")
    assert g.london_utc(date(2023, 3, 27), 480) == dt("2023-03-27T07:00:00Z")


def test_reentry_short_long_and_both_sides_exclusion() -> None:
    now = dt("2021-06-01T07:00:00Z")
    ref = [bar(now + i * timedelta(minutes=5), h=101, l=99, c=100)
           for i in range(96)]
    event = [bar(now, h=101.4, l=99.5, c=100) for _ in range(12)]
    assert g.setup_direction(ref, event, 1.0) == "SHORT"
    reverse = [bar(now, h=100.5, l=98.6, c=100) for _ in range(12)]
    assert g.setup_direction(ref, reverse, 1.0) == "LONG"
    both = [bar(now, h=101.4, l=98.6, c=100) for _ in range(12)]
    assert g.setup_direction(ref, both, 1.0) is None
    no_return = [bar(now, h=101.4, l=99.5, c=102.0) for _ in range(12)]
    assert g.setup_direction(ref, no_return, 1.0) is None


def test_atr_is_14_completed_m15_not_current() -> None:
    now = dt("2022-11-01T00:00:00Z")
    series = [bar(now + i * timedelta(minutes=15), o=100, h=101, l=99, c=100)
              for i in range(15)]
    assert g.true_range_atr(series) == pytest.approx(2.0)
    with pytest.raises(ValueError, match="15 completed"):
        g.true_range_atr(series[1:])


def test_same_m5_sl_and_tp_must_stop_first() -> None:
    now = dt("2021-06-01T08:00:00Z")
    period = [bar(now + timedelta(minutes=5 * i),
                  o=100, h=102, l=98, c=100) for i in range(24)]
    exit_bar = bar(now + timedelta(minutes=120))
    t = g.execute_proxy("EURJPY", date(2021, 6, 1), "LONDON",
                        "LONG", 1.0, period, exit_bar)
    assert t.exit_kind == "STOP_FIRST"
    assert t.gross_r == -1.0


def test_target_and_time_exit() -> None:
    now = dt("2021-06-01T08:00:00Z")
    period = [bar(now + timedelta(minutes=5 * i),
                  o=100, h=101.6, l=99.7, c=100) for i in range(24)]
    t = g.execute_proxy("USDCHF", date(2021, 6, 1), "PLACEBO",
                        "LONG", 1.0, period, bar(now + timedelta(minutes=120)))
    assert t.exit_kind == "TARGET" and t.gross_r == 1.0
    flat_period = [bar(now + timedelta(minutes=5 * i),
                       o=100, h=100.2, l=99.8, c=100) for i in range(24)]
    t = g.execute_proxy("USDCHF", date(2021, 6, 1), "PLACEBO",
                        "LONG", 1.0, flat_period,
                        bar(now + timedelta(minutes=120), o=100.75))
    assert t.exit_kind == "TIME"
    assert t.gross_r == pytest.approx(0.5)


def test_missing_reference_abstains_even_when_prices_look_good() -> None:
    t, why = g.arm_decision("EURJPY", date(2021, 6, 1), "LONDON", {}, {})
    assert t is None and why == "MISSING_REFERENCE"


def test_source_native_reader_stops_at_sealed_cutoff(tmp_path: Path) -> None:
    first = dt("2023-09-24T23:40:00Z")
    second = g.RESERVED_CUTOFF
    def item(opened: datetime) -> dict[str, str]:
        return {
            "close": "100.00", "closed_at": (opened + timedelta(minutes=5)).isoformat(),
            "high": "101.00", "low": "99.00", "open": "100.00",
            "opened_at": opened.isoformat(), "period": "M5"}
    payload = '{"periods":{"M5":['
    payload += json.dumps(item(first), separators=(",", ":"), sort_keys=True)
    payload += ',' + json.dumps(item(second), separators=(",", ":"), sort_keys=True)
    payload += ',THIS_IS_FUTURE_DATA_MUST_NOT_BE_PARSED]}}'
    path = tmp_path / "source.json"
    path.write_text(payload)
    bars = list(g.iter_pre_cutoff(path, "M5"))
    assert len(bars) == 1 and bars[0].opened == first


def test_reject_duplicate_native_m5(tmp_path: Path) -> None:
    first = dt("2020-01-01T00:00:00Z")
    data = []
    for _ in range(2):
        data.append({
            "close": "100", "closed_at": (first + timedelta(minutes=5)).isoformat(),
            "high": "101", "low": "99", "open": "100",
            "opened_at": first.isoformat(), "period": "M5"})
    path = tmp_path / "dupe.json"
    path.write_text(json.dumps({"periods": {"M5": data}}, sort_keys=True, separators=(",", ":")))
    with pytest.raises(ValueError, match="duplicated"):
        list(g.iter_pre_cutoff(path, "M5"))


def test_no_sample_cannot_get_potential_verdict() -> None:
    report = g.aggregate([], [])
    assert report["verdict"] == "DEV_UNDERPOWERED"
    assert report["primary_delta_r"] is None
    assert not report["min_sample_met"]
