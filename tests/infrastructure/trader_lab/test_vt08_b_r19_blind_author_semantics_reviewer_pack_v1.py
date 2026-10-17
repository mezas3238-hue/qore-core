"""R19 blind human-review dossiers; all test data synthetic, no outcomes."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.vt08_b_r19_blind_author_semantics_reviewer_pack_v1 import (
    R3_STAGE,
    build_blind_semantic_review_packets,
)

T = datetime(2026, 2, 2, 12, tzinfo=UTC)
M = "EURJPY"
SHA3 = "a" * 64
SHA15 = "b" * 64
CLASS = "NO_CLOSED_THREE_H1_BULLISH_BASIC_PIVOT_SHAPE"
CATS = (
    "MISSING_PRE_C2_H1_SOURCE",
    CLASS,
    "NO_UNTOUCHED_H1_HIGH_IN_OBSERVED_SEGMENT",
    "MULTIPLE_UNTOUCHED_H1_HIGHS_D",
    "UNIQUE_OBSERVED_H1_HIGH_AND_BASIC_PIVOT_FOR_BLIND_REVIEW_ONLY",
)


def _bars(n: int, minutes: int, sha: str) -> list[dict[str, object]]:
    result = []
    for i in range(n):
        bar = {
            "profile": "M3" if minutes == 3 else "M15",
            "source_raw_sha256": sha,
            "opened_at_utc": (T + timedelta(minutes=minutes*i)).isoformat(),
            "closed_at_utc": (T + timedelta(minutes=minutes*(i+1))).isoformat(),
            "ohlc": ["100", "101", "99", "100"],
        }
        digest = hashlib.sha256(json.dumps(
            bar, sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest()
        result.append({
            **bar, "market": M,
            "semantics": "OBSERVED_OHLC_ONLY_NOT_TTRADES_RULE",
            "source_bar_id": digest,
            "available_at_utc": bar["closed_at_utc"],
        })
    return result


def _bundle() -> tuple[dict[str, object], dict[str, object]]:
    sources = []
    observations = []
    for i in range(538):
        c2 = (T + timedelta(minutes=30*i)).isoformat()
        c3 = (T + timedelta(minutes=30*(i+1))).isoformat()
        identity = hashlib.sha256(f"{M}|{c2}|{c3}".encode()).hexdigest()
        sources.append({
            "market": M,
            "family": "BULLISH_M30_C2_REVERSAL_M3_CISD_C3_POSITIONAL",
            "stage": R3_STAGE,
            "c2_opened_at_utc": c2, "decision_at_utc": c3,
            "source_m3_file_sha256": SHA3, "source_m15_file_sha256": SHA15,
            "pre_c2_h1_context_available": True,
            "c1_m3_raw_bar_receipts": _bars(10, 3, SHA3),
            "c2_m3_raw_bar_receipts": _bars(10, 3, SHA3),
            "c2_m15_raw_bar_receipts": _bars(2, 15, SHA15),
            "pre_c2_h1_m15_raw_bar_receipts": _bars(12, 15, SHA15),
            "details": {
                "cisd_confirmed_at_utc": (T+timedelta(minutes=3)).isoformat(),
                "opposing_series_opened_at_utc": T.isoformat(),
            },
            "A_rule_complete": False, "B_signoff": False,
            "cognitive_ready": False, "broker_fill": False, "pnl_read": False,
        })
        observations.append({
            "market": M,
            "c2_opened_at_utc": c2, "decision_at_utc": c3,
            "case_id_sha256": identity,
            "pre_c2_three_h1_physically_complete": True,
            "basic_bullish_h1_pivot": False,
            "target_cardinality": 2,
            "source_unconsumed_h1_highs": [{"high": "101"}, {"high": "102"}],
            "diagnostic_review_class": CLASS,
            "h1_swing_source_ids": [],
            "c2_eq_full_conditional": "100.5",
            "c2_eq_close_to_low_conditional": "99.5",
            "rater_A": None, "rater_B_independent": None,
            "author_adjudication": "NOT_STARTED_D",
            **{s: False for s in (
                "source_author_relevant_swing_verified",
                "source_author_target_selected",
                "source_author_breaker_verified",
                "source_author_ps_cisd_verified",
                "source_author_poi_verified",
                "methodology_source_complete", "cognitive_verified",
                "broker_fill_verified",
            )},
        })
    r3 = {
        "schema": "qore.vt08.a.frozen_bullish_m30m3.source_funnel.v1",
        "market": M, "source_m3_sha256": SHA3, "source_m15_sha256": SHA15,
        "selection": "ALL_C2_M30_OPEN_WITHIN_OWNER_WINDOWS_FIRST_FAIL_PRE_PNL",
        "c2_windows_total": 18646,
        "stage_counts": {R3_STAGE: 538},
        "all_unique_proxy_cases_with_raw_receipts": 538,
        "examples_by_stage": {R3_STAGE: sources},
        "AUTHOR_RELEVANT_SWING_POI_BREAKER_TARGET_PENDING": True,
        "source_complete_entries": 0, "real_cognitive_admissions": 0,
        "fills": 0, "sizing_applied": False, "sealed_holdout_accessed": False,
        "pnl_evaluated": False, "A_B_signed_manifest": False,
    }
    r7 = {
        "schema": "qore.vt08.a.blind_three_source_review_join.v1",
        "market": M, "frozen_event_count": 538,
        "category_counts": {k: 538 if k == CLASS else 0 for k in CATS},
        "all_source_only_cases": observations,
        "selection_basis": "CHRONOLOGY_AND_PHYSICAL_SOURCE_ONLY_NO_PNL",
        "B_independent_semantic_review_complete": False,
        "signed_A_B_manifest": None,
        "source_complete_entries": 0, "broker_fills": 0,
        "profit_factor": None, "sortino": None, "max_drawdown": None,
        "holdout_7y_accessed": False, "sizing_used": False, "certified": False,
    }
    return r3, r7


def _run(r3: dict[str, object], r7: dict[str, object]) -> dict[str, object]:
    return build_blind_semantic_review_packets(r3, r7, expected_market=M)


def test_full_universe_plus_three_blind_semantic_review_dossiers() -> None:
    r3, r7 = _bundle()
    p = _run(r3, r7)
    assert p["all_cases_census"] == 538
    assert p["review_packets_selected"] == 3
    assert len(p["case_index"]) == 538
    assert [d["case_id_sha256"] for d in p["review_packets"]] == [
        r7["all_source_only_cases"][i]["case_id_sha256"] for i in (0, 268, 537)
    ]
    for packet in p["review_packets"]:
        assert packet["independent_reviewer_a_answers"] is None
        assert packet["independent_reviewer_b_answers"] is None
        assert packet["eligible_for_pnl"] is False
        assert packet["cognitive_27_fields_proven"] is False
        assert len(packet["methodological_questions"]) == 8
        assert len(packet["c2_m3_receipts"]) == 10
        assert len(packet["prior_h1_m15_receipts"]) == 12
        assert len(packet["packet_evidence_sha256"]) == 64
    assert p["source_author_complete"] == p["cognitive_admissions"] == 0
    assert p["economic_gates_evaluated"] is False


@pytest.mark.parametrize("mutation", [
    "pnl", "missing", "duplicate", "feed", "market", "signoff",
    "future", "category", "sizing", "alpha", "sha", "h1",
])
def test_adversarial_no_sample_or_source_forgery(mutation: str) -> None:
    r3, r7 = _bundle()
    cases = r3["examples_by_stage"][R3_STAGE]
    if mutation == "pnl":
        r3["pnl_evaluated"] = True
    elif mutation == "missing":
        cases.pop()
    elif mutation == "duplicate":
        cases[1] = deepcopy(cases[0])
    elif mutation == "feed":
        cases[0]["c2_m3_raw_bar_receipts"][0]["source_raw_sha256"] = "f"*64
    elif mutation == "market":
        cases[0]["market"] = "USDCAD"
    elif mutation == "signoff":
        cases[0]["B_signoff"] = True
    elif mutation == "future":
        r7["all_source_only_cases"][0]["decision_at_utc"] = (
            T + timedelta(minutes=45)
        ).isoformat()
    elif mutation == "category":
        r7["category_counts"][CLASS] = 0
    elif mutation == "sizing":
        r3["sizing_applied"] = True
    elif mutation == "alpha":
        cases[0]["foreign_signal_origin"] = "QORE-alpha"
    elif mutation == "sha":
        r7["all_source_only_cases"][0]["case_id_sha256"] = "f"*64
    elif mutation == "h1":
        cases[0]["pre_c2_h1_context_available"] = False
    with pytest.raises(ValueError):
        _run(r3, r7)


def test_invalid_sample_count_cannot_change_experiment_universe() -> None:
    r3, r7 = _bundle()
    with pytest.raises(ValueError, match="sample"):
        build_blind_semantic_review_packets(
            r3, r7, expected_market=M, per_category=0,
        )
