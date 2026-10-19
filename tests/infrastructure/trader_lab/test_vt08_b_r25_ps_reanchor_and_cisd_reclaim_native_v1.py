"""B R25 original CISD-level recovery: synthetic adversarial checks, never trade."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

import qore.infrastructure.trader_lab.vt08_b_r25_ps_reanchor_and_cisd_reclaim_native_v1 as r25

M = "EURJPY"
T = datetime(2026, 5, 4, 12, tzinfo=UTC)
SHA = "a"*64
ID = hashlib.sha256(
    f"{M}|{T.isoformat()}|{(T+timedelta(minutes=30)).isoformat()}".encode()
).hexdigest()


def _bars(mode: str = "same", *, cisd_wick: str = "97.9"):
    rows = [
        ("100", "100.1", "98.5", "99.5"),
        ("99.5", "99.6", "98", "99.2"),
        ("99.2", "101", cisd_wick, "100.5"),
    ]
    if mode == "same":
        rows.append(("99", "101", "97.8", "100.2"))
    elif mode == "later":
        rows.extend([("99", "100", "97.8", "99.5"), (
            "99.5", "101", "99", "100.4",
        )])
    elif mode == "absent":
        rows.append(("99", "100", "97.8", "99.5"))
    elif mode == "none":
        rows.append(("99", "100", "98", "99.5"))
    while len(rows) < 10:
        rows.append(("99.5", "100", "98.1", "99.5"))
    return [tuple(Decimal(v) for v in bar) for bar in rows]


@pytest.mark.parametrize(("mode","klass","first_new","first_reclaim"),[
    ("same",r25.RECLAIM_SAME,3,3),
    ("later",r25.RECLAIM_LATER,3,4),
    ("absent",r25.RECLAIM_ABSENT,3,None),
    ("none",r25.RECLAIM_NA,None,None),
])
def test_low_reanchor_before_c3_not_a_second_author_cisd(
    mode: str,klass: str,first_new: int | None,first_reclaim: int | None,
) -> None:
    result=r25.classify_reanchored_low_and_reclaim(
        _bars(mode),cisd_i=3,original_low=Decimal("98"),
        prior_cisd_level=Decimal("100"),
    )
    assert result["reanchored_as_of_cisd_closed_low"] == "97.9"
    assert result["confirming_bar_reanchors_original_run_low"] is True
    assert result["post_break_old_cisd_level_reclaim"] == klass
    assert result["first_post_cisd_break_reanchored_index"] == first_new
    assert result["first_post_break_reclaim_m3_index"] == first_reclaim
    assert result["authentic_reformed_protected_swing"] == "D_NOT_ASSESSED"
    assert result["reclaim_of_old_level_is_new_cisd"] is False


def test_confirmation_low_equal_to_prior_run_does_not_reanchor() -> None:
    result=r25.classify_reanchored_low_and_reclaim(
        _bars("none",cisd_wick="98"),cisd_i=3,
        original_low=Decimal("98"),prior_cisd_level=Decimal("100"),
    )
    assert result["reanchored_as_of_cisd_closed_low"] == "98"
    assert result["confirming_bar_reanchors_original_run_low"] is False


@pytest.mark.parametrize("attack",[
    "no_bars","future_index","invalid_low","old_level_not_above_low",
    "invalid_bar","inf_price",
])
def test_refuses_original_m3_level_corruption(attack: str) -> None:
    bars=_bars()
    cisd=3
    low=Decimal("98")
    level=Decimal("100")
    if attack == "no_bars":
        bars=[]
    elif attack == "future_index":
        cisd=11
    elif attack == "invalid_low":
        low=Decimal("-1")
    elif attack == "old_level_not_above_low":
        level=Decimal("98")
    elif attack == "invalid_bar":
        bars[3]=(Decimal("99"),Decimal("98"),Decimal("97"),Decimal("100"))
    elif attack == "inf_price":
        bars[3]=(Decimal("Infinity"),*bars[3][1:])
    with pytest.raises(ValueError):
        r25.classify_reanchored_low_and_reclaim(
            bars,cisd_i=cisd,original_low=low,prior_cisd_level=level,
        )


def _run(monkeypatch: pytest.MonkeyPatch,attack: str = ""):
    monkeypatch.setitem(r25.MARKET_EXPECTED,M,(1,"b"*64))
    monkeypatch.setitem(r25.PINNED_R19_REPORT_DIGESTS,M,"c"*64)
    monkeypatch.setattr(r25,"digest_r19",lambda _: "c"*64)
    old={
        "case_id_sha256":ID,
        "cisd_proxy_confirmed_at_utc":(T+timedelta(minutes=9)).isoformat(),
        "opposing_series_opened_at_utc":T.isoformat(),
        "cisd_level_proxy":"100",
        "ps_low_proxy":"98",
    }
    def r14(_frozen: object, *,market: str,native_m3: Path):
        assert market==M
        return{
            "native_m3_sha256":SHA,"frozen_source_cases":1,
            "all_source_only_witnesses":[old],
        }
    def raw(_path: Path,profile: str,market: str):
        assert profile=="M3" and market==M
        return SHA,{}
    def verify(_receipt: object,*,expected_open,minutes,profile,source_sha,raw):
        assert profile=="M3" and source_sha==SHA and minutes==3
        i=int((expected_open-T)/r25.M3)
        return _bars()[i]
    monkeypatch.setattr(r25,"audit_m3_opposing_series",r14)
    monkeypatch.setattr(r25,"_raw_bars",raw)
    monkeypatch.setattr(r25,"_verify_bar",verify)
    frozen={
        "examples_by_stage":{
            "UNIQUE_M3_CISD_PS_SHAPE_REQUIRES_AUTHOR_ADJUDICATION":[{
                "market":M,"c2_opened_at_utc":T.isoformat(),
                "decision_at_utc":(T+timedelta(minutes=30)).isoformat(),
                "c2_m3_raw_bar_receipts":[{
                    "source_bar_id":hashlib.sha256(str(i).encode()).hexdigest(),
                } for i in range(10)],
            }],
        },
    }
    blind={
        "market":M,"original_r18_sha256":"b"*64,
        "original_r18_cases":1,"rater_A_signed":0,"rater_B_signed":0,
        "source_complete_entries":0,"cognitive_admissions":0,
        "broker_fills":0,"holdout_7y_accessed":False,"sizing_used":False,
        "selected_source_only_cases":1,
        "review_packets":[{
            "case_id_sha256":ID,"market":M,
            "category":"CONTROL_NO_THREE_H1_FVG",
            "selection_rank_sha256":"d"*64,
            "human_rater_A_source_signoff":None,
            "human_rater_B_independent_signoff":None,
            "source_complete":False,"cognitive_ready":False,
            "orders_authorized":False,
        }],
    }
    case=frozen["examples_by_stage"][
        "UNIQUE_M3_CISD_PS_SHAPE_REQUIRES_AUTHOR_ADJUDICATION"
    ][0]
    if attack=="false_proxy":
        old["ps_low_proxy"]="98.8"
    elif attack=="false_level":
        old["cisd_level_proxy"]="101"
    elif attack=="fake_sign":
        blind["review_packets"][0]["human_rater_A_source_signoff"]="forged"
    elif attack=="future_cisd":
        old["cisd_proxy_confirmed_at_utc"]=(T+timedelta(minutes=33)).isoformat()
    elif attack=="wrong_c3":
        case["decision_at_utc"]=(T+timedelta(minutes=27)).isoformat()
    elif attack=="dropped":
        case["c2_m3_raw_bar_receipts"].pop()
    elif attack=="holdout":
        blind["holdout_7y_accessed"]=True
    elif attack=="duplicate":
        frozen["examples_by_stage"][
            "UNIQUE_M3_CISD_PS_SHAPE_REQUIRES_AUTHOR_ADJUDICATION"
        ].append(dict(case))
    return r25.audit_r25(frozen,blind,market=M,native_m3=Path("/synthetic.json"))


def test_source_only_full_join_preserves_original_blind_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result=_run(monkeypatch)
    assert result["original_candidate_census"]==1
    assert result["original_r19_source_review_cases"]==1
    assert result["post_break_old_level_reclaim_histogram"]=={r25.RECLAIM_SAME:1}
    assert result["source_old_vs_reanchored_low_counts"][
        "OLD_RUN_LOW_NEEDS_ANY_REANCHOR"
    ]==1
    assert result["same_107_r19_blind_source_review"][0]["A_signed_review"] is None
    assert result["source_complete_entries"]==0
    assert result["broker_fills"]==0


@pytest.mark.parametrize("attack",[
    "false_proxy","false_level","fake_sign","future_cisd",
    "wrong_c3","dropped","holdout","duplicate",
])
def test_broken_source_inputs_and_forged_review_fail_closed(
    monkeypatch: pytest.MonkeyPatch,attack: str,
) -> None:
    with pytest.raises(ValueError):
        _run(monkeypatch,attack)
