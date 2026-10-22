"""VT08 B R23: source-first dual review ledger rejects false certification."""
from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.trader_lab import vt08_b_r23_semantic_review_firstfail_ledger_v1 as r23
from qore.infrastructure.trader_lab.vt08_b_r20_poi_opposing_run_causal_join_v1 import (
    SCHEMA as R20_SCHEMA,
)
from qore.infrastructure.trader_lab.vt08_b_r20_poi_opposing_run_causal_join_v1 import (
    digest as digest20,
)
from qore.infrastructure.trader_lab.vt08_b_r22_multi_poi_contradiction_join_v1 import (
    SCHEMA as R22_SCHEMA,
)

CASE_IDS = ("a"*64, "b"*64)


def fixtures(monkeypatch):
    source = []
    context = []
    review20 = []
    review22 = []
    for i, cid in enumerate(CASE_IDS):
        phys = {
            "case_id_sha256": cid,
            "source_complete": False,
            "author_protected_swing": False,
            "physical_first_touch_relative_to_run":
                "WITHIN_BEARISH_OPPOSING_SERIES",
            "bearish_series_fvg_touch_bar_ids": ["1"*64],
            "same_m3_bar_event_order_proven_by_ticks": False,
        }
        other = {
            "case_id_sha256": cid,
            "relevance_and_poi_selection_adjudicated": False,
            "two_independent_raters_signed": False,
            "source_context_cross_category": "BULL_FVG_PRE__NY_LOW_NOT_SWEPT",
        }
        base = {
            "case_id_sha256": cid,
            "market": "EURJPY",
            "category": "BULLISH_FVG_TOUCHED_PRE_CISD",
            "selection_rank_sha256": str(i)*64,
            "c2_opened_at_utc": "2026-01-05T11:30:00+00:00",
            "cisd_closed_at_utc": "2026-01-05T11:45:00+00:00",
            "c3_opened_at_utc": "2026-01-05T12:00:00+00:00",
            "human_rater_A_source_signoff": None,
            "human_rater_B_independent_signoff": None,
            "source_complete": False,
            "cognitive_ready": False,
            "orders_authorized": False,
        }
        source.append(phys)
        context.append(other)
        review20.append({
            **base, "independent_bearish_run_causal_witness": phys,
        })
        review22.append({
            **base, "R22_independent_physical_context": other,
            "primary_source_important_poi_ref": None,
            "primary_source_relevant_swing_ref": None,
            "rater_A_verified": False,
            "rater_B_verified": False,
            "eligible_for_pnl": False,
        })
    r20 = {
        "schema": R20_SCHEMA, "market": "EURJPY",
        "owner_scope": r23.OWNER, "original_cases": 2,
        "blind_review_cases": 2, "source_authorized_entries": 0,
        "genuine_human_A_signoffs": 0, "genuine_human_B_signoffs": 0,
        "cognitive_admissions": 0, "broker_fills": 0,
        "profit_factor": None, "holdout_7y_accessed": False,
        "sizing_used": False, "r18_pinned_sha256": "1"*64,
        "r19_pinned_sha256": "2"*64,
        "original_native_m3_sha256": "3"*64,
        "all_physical_causal_opposing_run_witnesses": source,
        "enriched_blind_review_packets": review20,
    }
    r22 = {
        "schema": R22_SCHEMA, "market": "EURJPY",
        "all_original_case_count": 2,
        "r19_blind_packets_enriched": 2,
        "source_author_complete": 0,
        "dual_source_human_reviews_completed": 0,
        "cognitive_admissions": 0, "broker_fills": 0,
        "economic_gates_evaluated": False,
        "holdout_7y_accessed": False, "sizing_used": False,
        "frozen_original_r18_digest": "1"*64,
        "frozen_original_r19_digest": "2"*64,
        "original_r21_m3_source_sha": "3"*64,
        "entire_original_census": context,
        "blind_rater_dossiers": review22,
    }
    monkeypatch.setitem(
        r23.EXPECTED, "EURJPY", (2, 2, digest20(r20)),
    )
    return r20, r22


def test_two_distinct_native_dossiers_never_auto_approved(monkeypatch):
    r20, r22 = fixtures(monkeypatch)
    out = r23.build_semantic_wait_ledger(r20, r22, market="EURJPY")
    assert out["sample_cases_for_genuine_review"] == 2
    assert out["original_source_cases_unchanged"] == 2
    assert len(r23.REQUIRED) == 8
    assert out["human_A_genuinely_reviewed"] == 0
    assert out["source_author_complete"] == 0
    assert out["broker_fills"] == 0
    for row in out["review_dossiers"]:
        assert row["decision"].startswith("WAIT")
        assert row["economic_evaluation_authorized"] is False
        assert row["human_A_real_review"] is None
        assert row["human_B_real_review"] is None
        assert all(
            v["status"] == "AWAITING_REAL_REVIEW"
            for v in row["source_fidelity_questions"].values()
        )


def test_same_input_reproduces_report_sha(monkeypatch):
    r20, r22 = fixtures(monkeypatch)
    one = r23.build_semantic_wait_ledger(r20, r22, market="EURJPY")
    two = r23.build_semantic_wait_ledger(
        deepcopy(r20), deepcopy(r22), market="EURJPY",
    )
    assert r23.digest(one) == r23.digest(two)


def test_bogus_human_a_signature_rejected(monkeypatch):
    r20, r22 = fixtures(monkeypatch)
    r22["blind_rater_dossiers"][0]["human_rater_A_source_signoff"] = "yes"
    with pytest.raises(ValueError, match="forged human signature"):
        r23.build_semantic_wait_ledger(r20, r22, market="EURJPY")


def test_source_r20_digest_mutation_rejected(monkeypatch):
    r20, r22 = fixtures(monkeypatch)
    r20["all_physical_causal_opposing_run_witnesses"][0][
        "same_m3_bar_event_order_proven_by_ticks"
    ] = True
    with pytest.raises(ValueError, match="source SHA mismatch"):
        r23.build_semantic_wait_ledger(r20, r22, market="EURJPY")


def test_wrong_owner_scope_rejected(monkeypatch):
    r20, r22 = fixtures(monkeypatch)
    r20["owner_scope"] = "VT08_QORE_ALPHA"
    with pytest.raises(ValueError, match="source SHA mismatch"):
        r23.build_semantic_wait_ledger(r20, r22, market="EURJPY")


def test_cross_source_r18_sha_disagrees(monkeypatch):
    r20, r22 = fixtures(monkeypatch)
    r22["frozen_original_r18_digest"] = "0"*64
    with pytest.raises(ValueError, match="cross-feed"):
        r23.build_semantic_wait_ledger(r20, r22, market="EURJPY")


def test_duplicate_r22_candidate_detected(monkeypatch):
    r20, r22 = fixtures(monkeypatch)
    row = r22["blind_rater_dossiers"]
    row[1] = deepcopy(row[0])
    with pytest.raises(ValueError, match="duplicated/invalid"):
        r23.build_semantic_wait_ledger(r20, r22, market="EURJPY")


def test_r20_r22_category_conflict_rejected(monkeypatch):
    r20, r22 = fixtures(monkeypatch)
    r22["blind_rater_dossiers"][0]["category"] = "REWRITTEN_FOR_PROFIT"
    with pytest.raises(ValueError, match="event/category"):
        r23.build_semantic_wait_ledger(r20, r22, market="EURJPY")


def test_wrong_embedded_native_context_rejected(monkeypatch):
    r20, r22 = fixtures(monkeypatch)
    r22["blind_rater_dossiers"][0]["R22_independent_physical_context"] = {
        "case_id_sha256": CASE_IDS[0], "fake_context": True,
    }
    with pytest.raises(ValueError, match="witness drift"):
        r23.build_semantic_wait_ledger(r20, r22, market="EURJPY")


def test_r22_falsely_economic_authorized_rejected(monkeypatch):
    r20, r22 = fixtures(monkeypatch)
    r22["economic_gates_evaluated"] = True
    with pytest.raises(ValueError, match="custody or authority"):
        r23.build_semantic_wait_ledger(r20, r22, market="EURJPY")


def test_r20_fake_broker_fill_rejected(monkeypatch):
    r20, r22 = fixtures(monkeypatch)
    r20["broker_fills"] = 1
    with pytest.raises(ValueError, match="source SHA mismatch"):
        r23.build_semantic_wait_ledger(r20, r22, market="EURJPY")


def test_foreign_market_rejected():
    with pytest.raises(ValueError, match="unknown VT08-only"):
        r23.build_semantic_wait_ledger({}, {}, market="XAUUSD")
