"""Adversarial as-of tests of current H1: never treat partial as closed."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import vt08_b_r10_three_h1_current_asof_v1 as b

T = datetime(2025, 5, 15, 8, tzinfo=UTC)
MARKET = "EURJPY"
SHA = b.PINNED_M15[MARKET]


def inputs(*, start_minute: int = 30):
    raw = {}
    for i in range(16):
        opened = T + i * timedelta(minutes=15)
        low = "110"
        if 4 <= i < 8:
            low = "100"
        elif 8 <= i < 12:
            low = "90"
        elif 12 <= i < 16:
            low = "105"
        raw[opened] = {
            "opened_at": opened.isoformat(),
            "closed_at": (opened + timedelta(minutes=15)).isoformat(),
            "open": "115", "high": "120", "low": low, "close": "115",
        }
    c2 = T + timedelta(hours=3, minutes=start_minute)
    c3 = c2 + timedelta(minutes=30)
    digest = hashlib.sha256(
        (MARKET + "|" + c2.isoformat() + "|" + c3.isoformat()).encode()
    ).hexdigest()
    joined = {
        "schema": b.JOIN_SCHEMA, "market": MARKET, "frozen_event_count": 1,
        "source_complete_entries": 0, "broker_fills": 0,
        "profit_factor": None, "signed_A_B_manifest": None,
        "certified": False,
        "all_source_only_cases": [{
            "market": MARKET,
            "c2_opened_at_utc": c2.isoformat(),
            "decision_at_utc": c3.isoformat(), "case_id_sha256": digest,
            "basic_bullish_h1_pivot": False,
            "pre_c2_three_h1_physically_complete": True,
        }],
    }
    return raw, joined


def run(monkeypatch, raw, report):
    monkeypatch.setattr(b, "_raw_bars", lambda *_: (SHA, raw))
    return b.reconstruct_current_h1_context(
        report, market=MARKET, m15_file=Path("fixture-m15.json")
    )


def test_three_including_current_are_observed_separately(monkeypatch):
    raw, report = inputs()
    result = run(monkeypatch, raw, report)
    assert result["frozen_source_events"] == 1
    row = result["all_source_only_witnesses"][0]
    assert row["current_h1_asof_c2"]["bars_closed"] == 2
    assert row["current_h1_asof_c3"]["bars_closed"] == 4
    assert row["pivot_three_including_current_asof_c2"] is True
    assert row["pivot_three_including_current_asof_c3"] is True
    assert result["counts"]["basic_low_pivot_at_c3_current_h1_complete"] == 1
    assert result["author_relevant_swing_certified"] is False
    assert result["broker_fills"] == 0


def test_current_h1_empty_at_hour_boundary_and_partial_at_c3(monkeypatch):
    raw, report = inputs(start_minute=0)
    result = run(monkeypatch, raw, report)
    row = result["all_source_only_witnesses"][0]
    assert row["current_h1_asof_c2"]["bars_closed"] == 0
    assert row["current_h1_asof_c2"]["ohlc"] is None
    assert row["pivot_three_including_current_asof_c2"] is None
    assert row["current_h1_asof_c3"]["bars_closed"] == 2
    assert result["counts"]["current_h1_partial_at_c3"] == 1


def test_future_m15_cannot_change_either_snapshot(monkeypatch):
    raw, report = inputs()
    original = run(monkeypatch, raw, report)
    opened = T + timedelta(hours=4)
    raw[opened] = {
        "opened_at": opened.isoformat(),
        "closed_at": (opened + timedelta(minutes=15)).isoformat(),
        "open": "115", "high": "999", "low": "1", "close": "115",
    }
    assert run(monkeypatch, raw, report) == original


def test_gap_in_oldest_h1_not_reclassified_as_no_pivot(monkeypatch):
    raw, report = inputs()
    del raw[T + timedelta(minutes=45)]
    report["all_source_only_cases"][0]["pre_c2_three_h1_physically_complete"] = False
    result = run(monkeypatch, raw, report)
    assert result["counts"]["r7_closed_three_available"] == 0
    assert result["counts"]["prior_two_h1_available"] == 1
    assert result["counts"]["basic_low_pivot_observable_at_c3"] == 1


def test_missing_current_bar_never_inferred(monkeypatch):
    raw, report = inputs()
    del raw[T + timedelta(hours=3, minutes=15)]
    result = run(monkeypatch, raw, report)
    row = result["all_source_only_witnesses"][0]
    assert row["current_h1_asof_c2"] is None
    assert row["current_h1_asof_c3"] is None
    assert row["pivot_three_including_current_asof_c3"] is None


def test_false_r7_completeness_and_fake_pnl_fail(monkeypatch):
    raw, report = inputs()
    report["all_source_only_cases"][0]["pre_c2_three_h1_physically_complete"] = False
    with pytest.raises(ValueError, match="native vs R7 mismatch"):
        run(monkeypatch, raw, report)
    _, report = inputs()
    report["profit_factor"] = 1.8
    with pytest.raises(ValueError, match="false certified"):
        run(monkeypatch, raw, report)


def test_duplicate_event_and_tampered_identity_fail(monkeypatch):
    raw, report = inputs()
    report["all_source_only_cases"].append(dict(report["all_source_only_cases"][0]))
    report["frozen_event_count"] = 2
    with pytest.raises(ValueError, match="repeated"):
        run(monkeypatch, raw, report)
    _, report = inputs()
    report["all_source_only_cases"][0]["case_id_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="checksum"):
        run(monkeypatch, raw, report)


def test_native_market_sha_must_be_pinned(monkeypatch):
    raw, report = inputs()
    monkeypatch.setattr(b, "_raw_bars", lambda *_: ("a" * 64, raw))
    with pytest.raises(ValueError, match="not pinned"):
        b.reconstruct_current_h1_context(
            report, market=MARKET, m15_file=Path("fixture.json")
        )
