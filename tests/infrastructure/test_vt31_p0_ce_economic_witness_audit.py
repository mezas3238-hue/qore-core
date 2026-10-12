"""Synthetic-only adversarial fixtures for the VT31 CE economic evidence audit."""
from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from scripts.vt31_p0_ce_economic_witness_audit import (
    SESSIONS, audit, synthetic_ohlc_path_witness,
)

NY = ZoneInfo("America/New_York")
DUMMY_SHA = "0" * 64


def ledger() -> dict:
    events = []
    for sess, n in SESSIONS.items():
        hour = {"VT31_LONDON": 3, "VT31_NY_AM": 10, "VT31_NY_PM": 14}[sess]
        formed = datetime(2025, 1, 6, hour, 7, tzinfo=NY).astimezone(UTC)
        for i in range(n):
            side = "LONG" if i % 2 else "SHORT"
            events.append({
                "client_order_id": f"{sess}-{i}",
                "trader_id": "VT31",
                "session_window": sess,
                "side": side,
                "formed_at": formed.isoformat(),
                "source_first_m1_open": (formed - timedelta(minutes=3)).isoformat(),
                "m1_ce_research_limit": "20000",
                "draw_target": "20030" if side == "LONG" else "19970",
                "actual_broker_order_submitted": False,
                "paper_fill_count": 0,
                "live_fill_count": 0,
                "broker_execution_ack": None,
                "final_source_phase": "SOURCE_INVALIDATED",
                "m1_touch_observed_at_not_fill": None,
                "m1_ce_overlap_same_m1_as_source_revocation": None,
                "cognition_lost_or_source_invalidated_at": formed.isoformat(),
            })
    return {
        "market_m1_count": 1059784,
        "trader_id": "VT31",
        "source_fvg_hypothesis_count": 2140,
        "candidate_count_by_window": SESSIONS.copy(),
        "broker_execution_ack_count": 0,
        "paper_fills_proven": 0,
        "live_fills_proven": 0,
        "events": events,
    }


def test_identical_ohlc_quote_side_paths_have_opposite_reachable_exits() -> None:
    w = synthetic_ohlc_path_witness()
    p = w["intraminute_mid_sequences"]
    assert set(map(tuple, ((min(v), max(v)) for v in []))) == set()
    assert [min(map(int, v)) for v in p.values()] == [96, 96]
    assert [max(map(int, v)) for v in p.values()] == [106, 106]
    assert [v[0] for v in p.values()] == ["102", "102"]
    assert [v[-1] for v in p.values()] == ["101", "101"]
    assert len(set(w["alternative_theoretical_path_outcomes"].values())) == 2
    assert w["broker_fills_proven"] == 0 and w["real_VT31_trades"] == 0


def test_frozen_population_valid_but_no_invented_economic_pnl() -> None:
    r = audit(ledger(), sha256=DUMMY_SHA)
    assert r["source_candidates"] == 2140
    assert r["explicit_stop_price_missing"] == 2140
    assert r["exit_policy_or_exit_ack_missing"] == 2140
    assert r["entry_execution_ack_present"] == 0
    assert r["broker_fees_present"] == 0
    assert r["valid_directional_ce_target_geometry"] == 2140
    assert r["can_calculate_true_net_profit_factor"] is False
    assert r["can_calculate_true_net_expectancy"] is False
    assert r["can_calculate_true_position_drawdown"] is False


def test_non_proven_fields_do_not_silently_become_broker_truth() -> None:
    x = ledger()
    x["events"][0]["stop_loss_price"] = "19950"
    x["events"][0]["exit_policy_id"] = "EXPERIMENTAL_ONLY"
    x["events"][0]["commission"] = "2.5"
    r = audit(x, sha256=DUMMY_SHA)
    assert r["explicit_stop_price_present"] == 1
    assert r["exit_policy_or_exit_ack_present"] == 1
    assert r["broker_fees_present"] == 1
    assert r["field_presence_is_not_provenance"]
    assert not r["can_calculate_true_net_profit_factor"]


@pytest.mark.parametrize("bad", ["duplicate", "timezone", "gap", "wrong_side_target",
                                  "broker_claim", "wrong_window", "wrong_population", "bad_sha"])
def test_fail_closed_against_source_corruption_or_false_broker_claim(bad: str) -> None:
    x = ledger()
    if bad == "duplicate":
        x["events"][1]["client_order_id"] = x["events"][0]["client_order_id"]
    elif bad == "timezone":
        x["events"][0]["formed_at"] = "2025-01-06T08:07:00"
    elif bad == "gap":
        x["events"][0]["source_first_m1_open"] = (
            datetime(2025, 1, 6, 8, 0, tzinfo=UTC).isoformat()
        )
    elif bad == "wrong_side_target":
        x["events"][0]["draw_target"] = "20030"  # SHORT cannot target above CE
    elif bad == "broker_claim":
        x["events"][0]["broker_execution_ack"] = {"id": "not-source"}
    elif bad == "wrong_window":
        x["events"][0]["formed_at"] = "2025-01-06T11:07:00+00:00"
    elif bad == "wrong_population":
        x["events"].pop()
    if bad == "bad_sha":
        with pytest.raises(ValueError):
            audit(x, sha256="invalid")
    else:
        with pytest.raises(ValueError):
            audit(x, sha256=DUMMY_SHA)
