"""R22 native-source join anti-forgery adversarial tests (synthetic only)."""
from __future__ import annotations

import hashlib
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

import qore.infrastructure.trader_lab.vt08_b_r22_multi_poi_contradiction_join_v1 as r22

M = "EURJPY"
BASE = datetime(2026, 3, 16, 12, tzinfo=UTC)
M3 = timedelta(minutes=3)


def _source(i: int) -> tuple[dict[str, object], dict[str, object], str]:
    c2 = BASE + timedelta(minutes=i * 30)
    c3 = c2 + timedelta(minutes=30)
    cisd = c2 + timedelta(minutes=21)
    cid = hashlib.sha256(f"{M}|{c2.isoformat()}|{c3.isoformat()}".encode()).hexdigest()
    lo = {
        "level": "100",
        "available_at_utc": (c2 - timedelta(hours=1)).isoformat(),
        "raw_m15_bar_ids": ["a" * 64] * 4,
        "first_touch_phase": r22.PRE if i == 0 else "NOT_TOUCHED_DURING_C2",
        "first_touch_bar_opened_at_utc": (
            (c2 + M3).isoformat() if i == 0 else None
        ),
        "first_touch_m3_source_bar_id": ("c" * 64 if i == 0 else None),
        "author_relevant_low_adjudicated": False,
    }
    lows = [lo, {
        **lo, "level": "100.1",
        "first_touch_phase": "NOT_TOUCHED_DURING_C2",
        "first_touch_bar_opened_at_utc": None,
        "first_touch_m3_source_bar_id": None,
    }, {
        **lo, "level": "100.2",
        "first_touch_phase": "NOT_TOUCHED_DURING_C2",
        "first_touch_bar_opened_at_utc": None,
        "first_touch_m3_source_bar_id": None,
    }]
    fvg = None if i == 1 else {
        "type": "BULLISH_H1_3BAR_FVG_GEOMETRY",
        "lower": "99.2", "upper": "99.8",
        "available_at_utc": (c2 - timedelta(hours=1)).isoformat(),
        "source_bar_ids": ["d"*64] * 8,
        "first_touch_phase": r22.PRE,
        "first_touch_bar_opened_at_utc": (c2+M3).isoformat(),
        "first_touch_m3_source_bar_id": "e" * 64,
        "author_significant_poi": False,
    }
    source = {
        "market": M, "case_id_sha256": cid,
        "c2_opened_at_utc": c2.isoformat(),
        "c3_opened_at_utc": c3.isoformat(),
        "cisd_closed_at_utc": cisd.isoformat(),
        "upstream_h1_status": "THREE_PRIOR_H1_CLOSED",
        "pre_existing_h1_low_candidates": lows,
        "pre_existing_h1_fvg_candidate": fvg,
        "author_source_complete": False,
        "author_poi_significant_and_selected": False,
        "cognitive_admission": False,
    }
    day = {
        "market": M, "case_id_sha256": cid,
        "c2_opened_at_utc": c2.isoformat(),
        "C3_decision_at_utc": c3.isoformat(),
        "c1_low": "100", "c2_low": "99",
        "ny_midnight_to_c2_prior_low": "99.5" if i == 0 else "98",
        "day_context_complete": True,
        "day_low_source_diagnostic": r22.LABEL_YES if i == 0 else r22.LABEL_NO,
        "important_level_ttrades_author_confirmed": False,
        "cognitive_admission": False,
    }
    return source, day, cid


def _fixture(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setitem(r22.MARKET_EXPECTED, M, (2, "b"*64))
    monkeypatch.setitem(r22.R19_REPORT_DIGEST, M, "c"*64)
    monkeypatch.setattr(r22, "digest_r18", lambda _: "b"*64)
    monkeypatch.setattr(r22, "digest_r19", lambda _: "c"*64)
    a0, d0, i0 = _source(0)
    a1, d1, _ = _source(1)
    r18 = {
        "schema": r22.R18_SCHEMA, "market": M,
        "original_source_cases": 2,
        "owner_scope": "VT08_CURRENT_ONLY_NO_QORE_ALPHA",
        "original_m3_sha256": "a"*64,
        "source_complete_entries": 0, "cognitive_admissions": 0,
        "broker_fills": 0, "profit_factor": None,
        "counts": {
            "cases_source_only": 2,
            "cases_h1_prior_low_touched_before_cisd_bar": 1,
            "fvg_BULLISH_H1_3BAR_FVG_GEOMETRY_TOUCHED_BEFORE_CISD_BAR": 1,
        },
        "all_pre_cisd_h1_poi_source_witnesses": [a0, a1],
    }
    r19 = {
        "schema": r22.R19_SCHEMA, "market": M,
        "seed": r22.SEED,
        "original_r18_sha256": "b"*64,
        "original_r18_cases": 2,
        "selection_without_pnl": True,
        "review_sample_not_a_trading_cohort": True,
        "selected_source_only_cases": 1,
        "rater_A_signed": 0, "rater_B_signed": 0,
        "source_complete_entries": 0, "cognitive_admissions": 0,
        "broker_fills": 0,
        "review_packets": [{
            "market": M, "case_id_sha256": i0,
            "category": "BULLISH_FVG_TOUCHED_PRE_CISD",
            "selection_seed": r22.SEED,
            "human_rater_A_source_signoff": None,
            "human_rater_B_independent_signoff": None,
            "source_complete": False, "cognitive_ready": False,
            "orders_authorized": False,
            "c2_opened_at_utc": a0["c2_opened_at_utc"],
            "c3_opened_at_utc": a0["c3_opened_at_utc"],
            "cisd_closed_at_utc": a0["cisd_closed_at_utc"],
        }],
    }
    r21 = {
        "schema": r22.R21_SCHEMA, "market": M,
        "all_case_count": 2, "r20_universe_count": 2,
        "original_raw_m3_sha256": "a"*64,
        "all_source_author_poi_signatures_present": False,
        "source_complete_entries": 0, "cognitive_admissions": 0,
        "broker_fills": 0, "economic_gates_evaluated": False,
        "holdout_7y_accessed": False, "sizing_used": False,
        "day_low_category_counts": {
            r22.LABEL_YES: 1, r22.LABEL_NO: 1, r22.LABEL_GAP: 0,
        },
        "full_day_context_index": [d0, d1],
    }
    return r18, r19, r21


def test_two_source_contexts_and_blind_poi_conflicts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    r18, r19, r21 = _fixture(monkeypatch)
    result = r22.join_competing_poi_contexts(r18, r19, r21, market=M)
    assert result["all_original_case_count"] == 2
    assert result["r19_blind_packets_enriched"] == 1
    assert result["crossed_fvg_vs_ny_day_low_counts"] == {
        "BULL_FVG_PRE__NY_LOW_SWEPT": 1,
        "NO_FVG_PRE__NY_LOW_NOT_SWEPT": 1,
    }
    assert result["count_h1_lows_touched_before_cisd_histogram"] == {
        "0": 1, "1": 1,
    }
    packet = result["blind_rater_dossiers"][0]
    assert packet["human_rater_A_source_signoff"] is None
    assert packet["human_rater_B_independent_signoff"] is None
    assert packet["eligible_for_pnl"] is False
    assert packet["R22_independent_physical_context"]["h1_lows_touched_before_cisd_bar"] == 1
    assert not result["source_author_complete"]
    assert not result["cognitive_admissions"]


@pytest.mark.parametrize("attack", [
    "fake_rater", "wrong_r19_source", "wrong_r18_source",
    "foreign_r21_source", "future_h1", "altered_touch", "fake_author_poi",
    "gap_without_source", "category_tamper", "case_dropped",
    "bad_day_price", "fabricated_broker_fill", "changed_cisd_clock",
])
def test_no_fabricated_review_or_source_leakage(
    monkeypatch: pytest.MonkeyPatch, attack: str,
) -> None:
    original = _fixture(monkeypatch)
    a, b, c = deepcopy(original)
    if attack == "fake_rater":
        b["review_packets"][0]["human_rater_B_independent_signoff"] = "signed"
    elif attack == "wrong_r19_source":
        b["original_r18_sha256"] = "e"*64
    elif attack == "wrong_r18_source":
        a["owner_scope"] = "QORE-alpha"
    elif attack == "foreign_r21_source":
        c["original_raw_m3_sha256"] = "f"*64
    elif attack == "future_h1":
        a["all_pre_cisd_h1_poi_source_witnesses"][0][
            "pre_existing_h1_low_candidates"
        ][0]["available_at_utc"] = (BASE+timedelta(hours=3)).isoformat()
    elif attack == "altered_touch":
        a["all_pre_cisd_h1_poi_source_witnesses"][0][
            "pre_existing_h1_fvg_candidate"
        ]["first_touch_phase"] = r22.SAME
    elif attack == "fake_author_poi":
        a["all_pre_cisd_h1_poi_source_witnesses"][0][
            "pre_existing_h1_fvg_candidate"
        ]["author_significant_poi"] = True
    elif attack == "gap_without_source":
        c["full_day_context_index"][0]["day_context_complete"] = False
    elif attack == "category_tamper":
        b["review_packets"][0]["category"] = "CONTROL_NO_THREE_H1_FVG"
    elif attack == "case_dropped":
        c["full_day_context_index"].pop()
    elif attack == "bad_day_price":
        c["full_day_context_index"][0]["ny_midnight_to_c2_prior_low"] = "90"
    elif attack == "fabricated_broker_fill":
        c["broker_fills"] = 1
    elif attack == "changed_cisd_clock":
        a["all_pre_cisd_h1_poi_source_witnesses"][0]["cisd_closed_at_utc"] = (
            BASE + timedelta(minutes=24)
        ).isoformat()
    with pytest.raises(ValueError):
        r22.join_competing_poi_contexts(a, b, c, market=M)
