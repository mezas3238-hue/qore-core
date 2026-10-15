"""Blind cross-source contract keeps all physical negatives and semantic D."""
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.vt08_a_blind_three_source_review_join_v1 import (
    CATEGORIES,
    join_blind_source_reviews,
)

T = datetime(2025, 5, 15, 12, tzinfo=UTC)


def input_reports():
    eqs = []
    targets = []
    swings = []
    for i in range(5):
        c2 = T + timedelta(hours=i)
        d = c2 + timedelta(minutes=30)
        base = {
            "market": "EURJPY",
            "c2_opened_at_utc": c2.isoformat(),
            "decision_at_utc": d.isoformat(),
        }
        available = i != 0
        low = i != 1
        n = [1, 1, 0, 2, 1][i]
        eqs.append({
            **base,
            "prior_h1_context_available": available,
            "eq_selection_authorized": False,
            "eq_swing_identity_author_adjudicated": False,
            "eq_if_prior_bullish_swing_source_valid_with_close": "100.5",
            "eq_if_prior_bullish_swing_valid_but_close_against": "100",
            "c2_high": "102", "c2_low": "99", "c2_close": "101",
        })
        targets.append({
            **base,
            "witness_count": n,
            "c2_close_price_source_proxy": "101",
            "untouched_h1_high_candidates": [
                {
                    "high": "110",
                    "origin_h1_available_at_utc": (T - timedelta(hours=2)).isoformat(),
                    "origin_source_m15_bar_ids": ["m15-0", "m15-1", "m15-2", "m15-3"],
                    "continuity_since_origin": "OBSERVED_GAP_FREE_M15_ONLY",
                    "higher_than_c2_close_proxy": True,
                    "author_target_relevance_verified": False,
                } for _ in range(n)
            ],
            "author_target_selected": False,
        })
        swings.append({
            **base,
            "pre_c2_h1_complete": available,
            "basic_swing_bullish_low": low,
            "basic_swing_bearish_high": False,
            "source_author_relevant_swing_verified": False,
            "h1_candle_available_at_utc": c2.isoformat(),
            "h1_source_bar_id_groups": [
                ["a", "b", "c", "d"], ["e", "f", "g", "h"],
                ["i", "j", "k", "l"],
            ] if available else [],
        })
    return (
        {
            "schema": "qore.vt08.a.author_eq_conditional_review.v1",
            "market": "EURJPY",
            "source_raw_market_map": {"a" * 64: "EURJPY", "b" * 64: "EURJPY"},
            "source_case_count": 5,
            "source_complete_entries": 0,
            "verified_fills": 0,
            "profit_factor": None,
            "all_conditional_eq_witnesses": eqs,
        },
        {
            "schema": "qore.vt08.a.observed_h1_untouched_high_witness.v1",
            "market": "EURJPY",
            "input_m15_source_sha256": "b" * 64,
            "frozen_source_events": 5,
            "source_complete_entries": 0,
            "broker_fills": 0,
            "profit_factor": None,
            "witnesses": targets,
        },
        {
            "schema": "qore.vt08.a.pre_c2_h1_basic_swing_physical_witness.v1",
            "market": "EURJPY",
            "input_contexts": 5,
            "source_complete": False,
            "broker_fills": 0,
            "profit_factor": None,
            "review_witnesses": swings,
        },
    )


def test_all_five_source_categories_retained_without_pnl_selection():
    result = join_blind_source_reviews(*input_reports())
    assert result["frozen_event_count"] == 5
    assert list(result["category_counts"]) == list(CATEGORIES)
    assert list(result["category_counts"].values()) == [1, 1, 1, 1, 1]
    assert result["source_complete_entries"] == result["broker_fills"] == 0
    assert result["profit_factor"] is None
    assert result["signed_A_B_manifest"] is None
    assert all(
        r["author_adjudication"] == "NOT_STARTED_D"
        and not r["methodology_source_complete"]
        for r in result["all_source_only_cases"]
    )


def test_market_mixing_is_rejected():
    e, t, s = input_reports()
    t["market"] = "NZDUSD"
    with pytest.raises(ValueError, match="cross-market"):
        join_blind_source_reviews(e, t, s)


def test_missing_target_case_is_not_ignored():
    e, t, s = input_reports()
    t["witnesses"].pop()
    with pytest.raises(ValueError, match="nonidentical"):
        join_blind_source_reviews(e, t, s)


def test_duplicate_case_does_not_inflate_density():
    e, t, s = input_reports()
    t["witnesses"].append(dict(t["witnesses"][0]))
    t["frozen_source_events"] += 1
    with pytest.raises(ValueError, match="duplicate physical"):
        join_blind_source_reviews(e, t, s)


def test_fake_eq_or_source_approved_is_rejected():
    e, t, s = input_reports()
    e["all_conditional_eq_witnesses"][1][
        "eq_if_prior_bullish_swing_source_valid_with_close"
    ] = "999"
    with pytest.raises(ValueError, match="source math"):
        join_blind_source_reviews(e, t, s)
    e, t, s = input_reports()
    e["verified_fills"] = 1
    with pytest.raises(ValueError, match="false trading authority"):
        join_blind_source_reviews(e, t, s)


def test_future_h1_high_or_false_author_target_is_rejected():
    e, t, s = input_reports()
    row = t["witnesses"][4]["untouched_h1_high_candidates"][0]
    row["origin_h1_available_at_utc"] = (
        T + timedelta(hours=25)
    ).isoformat()
    with pytest.raises(ValueError, match="future H1"):
        join_blind_source_reviews(e, t, s)
    e, t, s = input_reports()
    t["witnesses"][1]["author_target_selected"] = True
    with pytest.raises(ValueError, match="author-selected"):
        join_blind_source_reviews(e, t, s)


def test_pivot_relevance_cannot_be_claimed_from_basic_geometry():
    e, t, s = input_reports()
    s["review_witnesses"][1]["source_author_relevant_swing_verified"] = True
    with pytest.raises(ValueError, match="mistakenly promoted"):
        join_blind_source_reviews(e, t, s)


def test_wrong_source_group_and_future_h1_candle_fail_closed():
    e, t, s = input_reports()
    s["review_witnesses"][2]["h1_source_bar_id_groups"] = [[]]
    with pytest.raises(ValueError, match="source groups"):
        join_blind_source_reviews(e, t, s)
