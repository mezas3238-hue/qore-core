"""VT08 B R19 preregistered blind review selection adversarial regression."""
from __future__ import annotations

import hashlib
from copy import deepcopy

import pytest

from qore.infrastructure.trader_lab.vt08_b_r18_pre_cisd_h1_poi_native_timing_v1 import (
    SCHEMA as R18_SCHEMA,
    digest as r18_digest,
)
from qore.infrastructure.trader_lab import vt08_b_r19_blind_dual_rater_poi_queue_v1 as r19


def make_source() -> dict[str, object]:
    rows = []
    for i in range(26):
        cid = hashlib.sha256(f"frozen-{i}".encode()).hexdigest()
        if i < 12:
            fvg = {"type":r19.BULL,"first_touch_phase":r19.PRE,
                   "first_touch_bar_opened_at_utc":"2026-01-01T00:09:00+00:00",
                   "first_touch_m3_source_bar_id":"a"*64}
        elif i < 24:
            fvg = None
        elif i == 24:
            fvg = {"type":r19.BULL,"first_touch_phase":r19.SAME,
                   "first_touch_bar_opened_at_utc":"2026-01-01T00:12:00+00:00",
                   "first_touch_m3_source_bar_id":"b"*64}
        else:
            fvg = {"type":r19.BEAR,"first_touch_phase":r19.PRE,
                   "first_touch_bar_opened_at_utc":"2026-01-01T00:06:00+00:00",
                   "first_touch_m3_source_bar_id":"c"*64}
        rows.append({
            "case_id_sha256":cid,"market":"EURJPY",
            "c2_opened_at_utc":"2026-01-01T00:00:00+00:00",
            "cisd_closed_at_utc":"2026-01-01T00:15:00+00:00",
            "c3_opened_at_utc":"2026-01-01T00:30:00+00:00",
            "upstream_h1_status":"THREE_PRIOR_H1_CLOSED",
            "pre_existing_h1_fvg_candidate":fvg,
            "pre_existing_h1_low_candidates":[],
            "author_source_complete":False,
            "author_relevant_swing_selected":False,
            "author_poi_significant_and_selected":False,
            "author_protected_swing_adjudicated":False,
            "cognitive_admission":False,
            "broker_fill":False,
        })
    return {
        "schema":R18_SCHEMA,"market":"EURJPY",
        "owner_scope":"VT08_CURRENT_ONLY_NO_QORE_ALPHA",
        "original_source_cases":26,
        "source_complete_entries":0,"cognitive_admissions":0,
        "broker_fills":0,"profit_factor":None,
        "all_pre_cisd_h1_poi_source_witnesses":rows,
    }


def authorized_unit_fixture(monkeypatch):
    report = make_source()
    monkeypatch.setitem(
        r19.MARKET_EXPECTED,"EURJPY",(26,r18_digest(report)),
    )
    return report


def test_blind_queue_is_preregistered_and_unsigned(monkeypatch) -> None:
    report=authorized_unit_fixture(monkeypatch)
    out=r19.build_blind_review_queue(report,market="EURJPY")
    assert out["selected_source_only_cases"]==22
    assert out["selected_category_counts"]=={
        "BULLISH_FVG_TOUCHED_PRE_CISD":10,
        "CONTROL_NO_THREE_H1_FVG":10,
        "SAME_CISD_M3_BAR_INTRABAR_UNKNOWN":1,
        "BEARISH_FVG_TOUCHED_PRE_CISD_NEGATIVE_CONTROL":1,
    }
    assert len({x["case_id_sha256"] for x in out["review_packets"]})==22
    for packet in out["review_packets"]:
        assert packet["human_rater_A_source_signoff"] is None
        assert packet["human_rater_B_independent_signoff"] is None
        assert packet["source_complete"] is False
        assert packet["orders_authorized"] is False
    assert out["broker_fills"]==0 and out["alpha_programs_authorized"]==0


def test_same_input_yields_same_manifest_digest(monkeypatch) -> None:
    report=authorized_unit_fixture(monkeypatch)
    first=r19.build_blind_review_queue(report,market="EURJPY")
    second=r19.build_blind_review_queue(deepcopy(report),market="EURJPY")
    assert r19.digest(first)==r19.digest(second)


def test_any_raw_poi_mutation_rejected_by_signed_digest(monkeypatch) -> None:
    report=authorized_unit_fixture(monkeypatch)
    report["all_pre_cisd_h1_poi_source_witnesses"][0][
        "pre_existing_h1_fvg_candidate"]["type"]="ALPHA_SUBSTITUTE"
    with pytest.raises(ValueError,match="digest mismatch"):
        r19.build_blind_review_queue(report,market="EURJPY")


def test_author_source_complete_forgery_rejected(monkeypatch) -> None:
    report=authorized_unit_fixture(monkeypatch)
    report["all_pre_cisd_h1_poi_source_witnesses"][0][
        "author_source_complete"]=True
    monkeypatch.setitem(
        r19.MARKET_EXPECTED,"EURJPY",(26,r18_digest(report)),
    )
    with pytest.raises(ValueError,match="false source/cognitive"):
        r19.build_blind_review_queue(report,market="EURJPY")


def test_first_touch_missing_original_m3_id_rejected(monkeypatch) -> None:
    report=authorized_unit_fixture(monkeypatch)
    report["all_pre_cisd_h1_poi_source_witnesses"][0][
        "pre_existing_h1_fvg_candidate"].pop("first_touch_m3_source_bar_id")
    monkeypatch.setitem(
        r19.MARKET_EXPECTED,"EURJPY",(26,r18_digest(report)),
    )
    with pytest.raises(ValueError,match="no source M3 bar ID"):
        r19.build_blind_review_queue(report,market="EURJPY")


def test_alternate_alpha_owner_scope_rejected(monkeypatch) -> None:
    report=authorized_unit_fixture(monkeypatch)
    report["owner_scope"]="VT08_QORE_ALPHA"
    monkeypatch.setitem(
        r19.MARKET_EXPECTED,"EURJPY",(26,r18_digest(report)),
    )
    with pytest.raises(ValueError,match="digest mismatch"):
        r19.build_blind_review_queue(report,market="EURJPY")


def test_duplicate_candidates_fail_even_if_sha_is_recomputed(monkeypatch) -> None:
    report=authorized_unit_fixture(monkeypatch)
    rows=report["all_pre_cisd_h1_poi_source_witnesses"]
    rows[1]=deepcopy(rows[0])
    monkeypatch.setitem(
        r19.MARKET_EXPECTED,"EURJPY",(26,r18_digest(report)),
    )
    with pytest.raises(ValueError,match="duplicate/corrupt"):
        r19.build_blind_review_queue(report,market="EURJPY")


def test_unapproved_market_rejected() -> None:
    with pytest.raises(ValueError,match="unapproved"):
        r19.build_blind_review_queue({},market="QORE_ALPHA")
