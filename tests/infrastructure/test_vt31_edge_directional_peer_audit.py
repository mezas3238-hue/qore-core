"""Independent peer fixtures for PR #874's causal M1 directional screen.

No historical artifact, outcome optimization, order-fill claims, or modifications
to the source implementation. These tests target boundaries of the unchanged
research-only script, on deterministic synthetic M1 examples.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from scripts import vt31_edge_directional_15m_preregistered_3y_v1 as study


NY = ZoneInfo("America/New_York")


def _source_ledger(monkeypatch: pytest.MonkeyPatch) -> dict:
    monkeypatch.setattr(study, "SAMPLE_SIZE", 3)
    monkeypatch.setattr(
        study, "SESSIONS",
        {"VT31_LONDON": 1, "VT31_NY_AM": 1, "VT31_NY_PM": 1},
    )
    # Deliberately includes US winter/summer UTC offsets. M1 source begins
    # three contiguous minutes before the third candle is CLOSED.
    events = []
    for identifier, session, local in (
        ("lon-winter", "VT31_LONDON", datetime(2025, 1, 6, 3, 7, tzinfo=NY)),
        ("am-summer", "VT31_NY_AM", datetime(2025, 7, 7, 10, 7, tzinfo=NY)),
        ("pm-winter", "VT31_NY_PM", datetime(2025, 1, 6, 14, 7, tzinfo=NY)),
    ):
        formed = local.astimezone(UTC)
        events.append({
            "client_order_id": identifier,
            "side": "SHORT" if identifier == "pm-winter" else "LONG",
            "session_window": session,
            "formed_at": formed.isoformat(),
            "source_first_m1_open": (formed-timedelta(minutes=3)).isoformat(),
        })
    return {
        "source_fvg_hypothesis_count": 3,
        "market_m1_count": 1059784,
        "trader_id": "VT31",
        "paper_fills_proven": 0,
        "live_fills_proven": 0,
        "candidate_count_by_window": dict(study.SESSIONS),
        "events": events,
    }


def test_source_event_end_of_third_m1_and_new_york_dst(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = _source_ledger(monkeypatch)
    events, needed = study.prepare(ledger)
    assert len(events) == 3
    assert events[0]["formed"].hour == 8   # 03:07 New York in January
    assert events[1]["formed"].hour == 14  # 10:07 New York in July
    assert [e["side_sign"] for e in events] == [1, 1, -1]
    # First hypothetical entry is next bar OPEN = signal third M1 CLOSE.
    assert events[0]["formed"] in needed
    assert events[0]["formed"] - timedelta(minutes=1) not in needed
    assert events[0]["formed"] + timedelta(minutes=60) in needed


@pytest.mark.parametrize("mutation", ["duplicate", "bad_window", "bad_formation", "naive"])
def test_prepare_fails_closed_on_source_identity_and_causality(
    monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    ledger = _source_ledger(monkeypatch)
    bad = deepcopy(ledger)
    row = bad["events"][1]
    if mutation == "duplicate":
        row["client_order_id"] = bad["events"][0]["client_order_id"]
    elif mutation == "bad_window":
        row["formed_at"] = datetime(2025, 7, 7, 12, 7, tzinfo=UTC).isoformat()
    elif mutation == "bad_formation":
        row["source_first_m1_open"] = row["formed_at"]  # zero M1 duration
    else:
        row["formed_at"] = "2025-07-07T14:07:00"  # lacks timezone
    with pytest.raises(ValueError):
        study.prepare(bad)


def _screen_fixture(monkeypatch: pytest.MonkeyPatch, *, adverse: bool = False):
    monkeypatch.setattr(study, "SAMPLE_SIZE", 32)
    monkeypatch.setattr(study, "SESSIONS", {"VT31_LONDON": 32})
    monkeypatch.setattr(study, "HORIZONS", (5, 15))
    monkeypatch.setattr(study, "PRIMARY", 15)
    monkeypatch.setattr(study, "RESAMPLES", 200)
    events, opens = [], {}
    for i in range(32):
        at = datetime(2025, 1, 6, 8, 5, tzinfo=UTC) + timedelta(weeks=i)
        sign = 1 if i % 2 == 0 else -1
        slope = -1 if adverse else (2 if sign == 1 else -1)
        if adverse:
            sign = 1
        events.append({
            "id": f"fixed-{i}",
            "formed": at,
            "side_sign": sign,
            "session": "VT31_LONDON",
            "ny_iso_week": f"2025-W{i+1:02d}",
        })
        for minute in range(16):
            opens[at + timedelta(minutes=minute)] = 20000 + 100*i + slope*minute
    return events, opens


def test_next_open_long_short_roundtrip_cost_and_stable_sample(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events, opens = _screen_fixture(monkeypatch)
    result = study.screen(events, opens)
    five, fifteen = result["5"], result["15"]
    assert five["valid_exact_contiguous_M1"] == 32
    assert fifteen["valid_exact_contiguous_M1"] == 32
    assert fifteen["mean_gross_directional_pts"] == 22.5
    assert fifteen["mean_net_fixed_1p60_hypothetical_pts"] == 20.9
    assert abs(
        fifteen["mean_gross_directional_pts"] -
        fifteen["mean_net_fixed_1p60_hypothetical_pts"] - study.COST_PTS
    ) < 1e-9
    assert fifteen["is_preregistered_primary"] is True
    assert five["is_preregistered_primary"] is False


def test_middle_m1_gap_is_missing_not_filled_from_future(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events, opens = _screen_fixture(monkeypatch)
    missing = events[0]["formed"] + timedelta(minutes=7)
    del opens[missing]
    result = study.screen(events, opens)
    assert result["5"]["valid_exact_contiguous_M1"] == 32
    assert result["15"]["valid_exact_contiguous_M1"] == 31
    assert result["15"]["missing_exact_contiguous_M1"] == 1
    assert result["15"]["missing_by_window"] == {"VT31_LONDON": 1}


def test_negative_gross_is_not_explained_by_hypothetical_spread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events, opens = _screen_fixture(monkeypatch, adverse=True)
    result = study.screen(events, opens)["15"]
    assert result["mean_gross_directional_pts"] == -15
    assert result["mean_net_fixed_1p60_hypothetical_pts"] == -16.6
    assert result["preregistered_directional_screen_passed"] is False
    assert result["clustered_inference"][
        "weekly_cluster_bootstrap_95pct_net_pts_upper"
    ] < 0


def test_published_cost_translation_is_algebra_not_new_backtest() -> None:
    # Published CI is for net = gross - 1.60, all observations same fixed
    # cost. Its translation to gross does NOT introduce a new experiment.
    lo, hi, cost = -5.130648, -2.019817, 1.60
    assert round(lo+cost, 6) == -3.530648
    assert round(hi+cost, 6) == -0.419817
    assert hi + cost < 0
