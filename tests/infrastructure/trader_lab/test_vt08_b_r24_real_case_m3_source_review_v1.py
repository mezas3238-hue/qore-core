"""R24 source snapshot is a reviewer tool, not a fake methodology signature."""
from __future__ import annotations

import hashlib
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import vt08_b_r24_real_case_m3_source_review_v1 as r24

START = datetime(2026, 1, 1, 12, tzinfo=UTC)
SHA3 = "f"*64
CASE_ID = hashlib.sha256(
    ("EURJPY|"+START.isoformat()+"|"+(START+timedelta(minutes=30)).isoformat()).encode()
).hexdigest()


def source(monkeypatch):
    phys = {
        "case_id_sha256": CASE_ID,
        "original_r18_source_sha256": "1"*64,
        "physical_first_touch_relative_to_run": "NO_H1_THREE_BAR_FVG",
        "opposing_series_opened_at_utc": (START+timedelta(minutes=3)).isoformat(),
        "cisd_close_at_utc": (START+timedelta(minutes=15)).isoformat(),
        "original_fvg_physical_exists": False,
        "bearish_series_fvg_touch_bar_ids": [],
        "bearish_series_sweep_bar_ids": ["a"*64],
        "same_bar_fvg_touch_and_liquidity_sweep": None,
    }
    context = {"case_id_sha256": CASE_ID, "h1_lows_touched_before_cisd_bar":1}
    sample = {
        "case_id_sha256": CASE_ID,
        "C3_decision_at_utc": (START+timedelta(minutes=30)).isoformat(),
        "physical_candidate_evidence": {
            "r20_bearish_series_causal_witness":phys,
            "r22_competing_poi_context":context,
        },
        "human_A_real_review":None,
        "human_B_real_review":None,
        "source_authenticity_accepted":False,
    }
    r23 = {
        "schema": r24.R23_SCHEMA,
        "market":"EURJPY", "original_source_cases_unchanged":1,
        "sample_cases_for_genuine_review":1,
        "source_author_complete":0, "human_A_genuinely_reviewed":0,
        "human_B_genuinely_reviewed":0,
        "broker_fills":0, "QORE_alpha_excluded":True,
        "sizing_used":False, "holdout_7y_accessed":False,
        "original_r18_sha256":"1"*64, "review_dossiers":[sample],
    }
    m3 = {
        "source_m3_sha256":SHA3,
        "examples_by_stage":{
            r24.STAGE:[{
                "c2_opened_at_utc":START.isoformat(),
                "decision_at_utc":(START+timedelta(minutes=30)).isoformat(),
                "c2_m3_raw_bar_receipts":[
                    {"source_bar_id":f"{i:064x}"} for i in range(10)
                ],
            }]
        },
    }
    original_digest = r24.digest23(r23)
    monkeypatch.setitem(r24.PINNED, "EURJPY", (1,1,original_digest))
    monkeypatch.setattr(r24,"_raw_bars",lambda path, tf, market:(SHA3,{}))
    def bar_validator(receipt,**kwargs):
        i=int(receipt["source_bar_id"],16)
        if i in (1,2,3):
            return (100, 101, 99, 99)
        if i == 4:
            return (99, 104, 99, 103)
        return (100, 101, 99, 100)
    monkeypatch.setattr(r24,"_verify_bar",bar_validator)
    return r23,m3


def test_one_real_source_snapshot_waits_without_auto_signoff(monkeypatch):
    r23,m3=source(monkeypatch)
    result=r24.review_real_frozen_cases(r23,m3,Path("/unused"),market="EURJPY")
    assert result["case_review_snapshots"]==1
    item=result["review_evidence"][0]
    assert len(item["native_c2_m3_source_only_bars"])==10
    assert item["methodological_findings"]["trade_admission"] is False
    assert item["human_A_signed"] is False and item["human_B_signed"] is False
    assert result["author_complete_entries"]==0
    assert item["case_review_ruling"].startswith("D_")


def test_canonical_evidence_snapshot_reproducible(monkeypatch):
    r23,m3=source(monkeypatch)
    first=r24.review_real_frozen_cases(r23,m3,Path("/unused"),market="EURJPY")
    second=r24.review_real_frozen_cases(
        deepcopy(r23),deepcopy(m3),Path("/unused"),market="EURJPY",
    )
    assert r24.digest(first)==r24.digest(second)


def test_tampered_r23_case_id_digest_rejected(monkeypatch):
    r23,m3=source(monkeypatch)
    r23["review_dossiers"][0]["case_id_sha256"]="a"*64
    with pytest.raises(ValueError,match="evidence or owner scope changed"):
        r24.review_real_frozen_cases(r23,m3,Path("/unused"),market="EURJPY")


def test_future_cisd_rejected_even_if_hash_pinned(monkeypatch):
    r23,m3=source(monkeypatch)
    r23["review_dossiers"][0]["physical_candidate_evidence"][
        "r20_bearish_series_causal_witness"]["cisd_close_at_utc"]=(
            START+timedelta(minutes=33)).isoformat()
    monkeypatch.setitem(r24.PINNED,"EURJPY",(1,1,r24.digest23(r23)))
    with pytest.raises(ValueError,match="chronology"):
        r24.review_real_frozen_cases(r23,m3,Path("/unused"),market="EURJPY")


def test_wrong_original_m3_sha_rejected(monkeypatch):
    r23,m3=source(monkeypatch)
    m3["source_m3_sha256"]="c"*64
    with pytest.raises(ValueError,match="source SHA"):
        r24.review_real_frozen_cases(r23,m3,Path("/unused"),market="EURJPY")


def test_fake_signer_rejected_even_if_r23_digest_pinned(monkeypatch):
    r23,m3=source(monkeypatch)
    r23["review_dossiers"][0]["human_A_real_review"]={"signed":True}
    monkeypatch.setitem(r24.PINNED,"EURJPY",(1,1,r24.digest23(r23)))
    with pytest.raises(ValueError,match="fake methodological signoff"):
        r24.review_real_frozen_cases(r23,m3,Path("/unused"),market="EURJPY")


def test_missing_raw_c2_m3_bar_rejected(monkeypatch):
    r23,m3=source(monkeypatch)
    m3["examples_by_stage"][r24.STAGE][0]["c2_m3_raw_bar_receipts"].pop()
    with pytest.raises(ValueError,match="original 10 M3"):
        r24.review_real_frozen_cases(r23,m3,Path("/unused"),market="EURJPY")


def test_foreign_market_rejected():
    with pytest.raises(ValueError,match="outside authorized"):
        r24.review_real_frozen_cases({}, {}, Path("/unused"),market="QORE_ALPHA")
