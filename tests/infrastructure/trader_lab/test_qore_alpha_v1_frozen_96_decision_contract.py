"""QORE-alpha frozen 96-space/source window/outcome screening tests."""

import json
from datetime import UTC, datetime
from pathlib import Path
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.qore_alpha_v1_frozen_96_decision_contract import (
    BONFERRONI_PER_TEST_ALPHA,
    ENTRIES,
    MAX_DD_PCT,
    PF_TEST,
    SESSIONS,
    STOPS,
    TARGETS,
    VARIANT_IDS,
    VARIANTS,
    ScreeningStatus,
    SegmentMetrics,
    frozen_manifest,
    internal_test_decision,
    screen_train_validate,
    segment_of,
    session_of,
    validate_source_coverage,
)


def metrics(variant, segment, *, pf="1.50", trades=65, dd="5", wr="0.45"):
    return SegmentMetrics(
        variant, segment, Decimal(pf), trades, Decimal(dd), Decimal(wr)
    )


def cohorts():
    return (
        tuple(metrics(v.variant_id, "TRAIN", pf="1.01") for v in VARIANTS),
        tuple(metrics(v.variant_id, "VALIDATE", pf="1.00") for v in VARIANTS),
    )


def promote_once(tr, val, index, *, t_pf="1.41", v_pf="1.31"):
    a,b=list(tr),list(val)
    a[index]=metrics(VARIANTS[index].variant_id,"TRAIN",pf=t_pf)
    b[index]=metrics(VARIANTS[index].variant_id,"VALIDATE",pf=v_pf)
    return tuple(a),tuple(b)


def screen(tr,va,*,data=True,cost=True):
    return screen_train_validate(
        tr,va,coverage_verified=data,broker_cost_proven=cost
    )


def test_product_is_exactly_96_no_97th_and_deterministic_order():
    assert len(VARIANTS) == 96
    assert len(VARIANT_IDS) == 96
    assert len(ENTRIES)*len(SESSIONS)*len(STOPS)*len(TARGETS)==96
    assert VARIANTS[0].variant_id=="QALPHA-V001"
    assert VARIANTS[-1].variant_id=="QALPHA-V096"
    assert VARIANTS[0].entry=="POSITIONAL_C3"
    assert VARIANTS[-1].target=="EXTERNAL_LIQUIDITY"
    assert len({
        (v.entry,v.session,v.stop,v.target) for v in VARIANTS
    })==96
    m=frozen_manifest()
    assert m==frozen_manifest()
    assert len(m["sha256"])==64
    assert m["statistical_disclosure"]["pf_1_40_is_bonferroni_adjusted"] is False
    assert BONFERRONI_PER_TEST_ALPHA == Decimal("0.05") / 96


def test_session_no_overlap_and_dst_aware():
    def ny(h):
        return datetime(2025,5,1,h,tzinfo=UTC)
    # NY EDT = UTC-4
    assert session_of(ny(0))=="ASIA"
    assert session_of(ny(6))=="LONDON"
    assert session_of(ny(12))=="NEW_YORK"
    assert session_of(ny(16)) is None
    with pytest.raises(ValueError, match="naive"):
        session_of(datetime(2025,3,1))


def test_split_inclusive_exclusive_ny_fixed():
    def when(y,m,d):
        return datetime(y,m,d,16,tzinfo=UTC)
    assert segment_of(when(2022,1,3))=="TRAIN"
    assert segment_of(when(2024,6,30))=="TRAIN"
    assert segment_of(when(2024,7,1))=="VALIDATE"
    assert segment_of(when(2025,6,30))=="VALIDATE"
    assert segment_of(when(2025,7,1))=="INTERNAL_TEST"
    assert segment_of(when(2026,6,30))=="INTERNAL_TEST"
    assert segment_of(when(2026,7,1)) is None


def test_source_2023_to_2026_cannot_pass_train_2022():
    obj=validate_source_coverage(
        market="USDCHF",
        first_m3_open=datetime(2023,10,1,tzinfo=UTC),
        last_m3_close=datetime(2026,10,1,tzinfo=UTC),
        months_with_m3=frozenset({"2023-10"}),
    )
    assert obj["status"]=="BLOCKED_DATA_COVERAGE"
    assert "M3_TRAIN_2022_MISSING" in obj["blockers"]
    assert "M3_MONTHS_WITHOUT_ANY_BAR" in obj["blockers"]
    assert obj["variants_backtested"]==0


def test_missing_end_or_independent_cross_feed_blocks():
    obj=validate_source_coverage(
        market="USDCAD",
        first_m3_open=datetime(2022,1,3,tzinfo=UTC),
        last_m3_close=datetime(2026,5,1,tzinfo=UTC),
        months_with_m3=frozenset(),
        first_m15_open=datetime(2023,1,1,tzinfo=UTC),
        last_m15_close=datetime(2026,5,1,tzinfo=UTC),
    )
    assert "M3_INTERNAL_TEST_END_MISSING" in obj["blockers"]
    assert "M15_INDEPENDENT_PERIOD_INCOMPLETE" in obj["blockers"]


def test_zero_pass_stops_feature_set():
    d=screen(*cohorts())
    assert d.status is ScreeningStatus.NO_PASS_STOP
    assert d.winner_id is None and not d.test_internal_authorized


def test_pf_gates_strict_not_equal():
    a,b=cohorts()
    a,b=promote_once(a,b,0,t_pf="1.40",v_pf="1.99")
    assert screen(a,b).winner_id is None
    a,b=promote_once(a,b,0,t_pf="1.41",v_pf="1.30")
    assert screen(a,b).winner_id is None


def test_min_trade_requirements_50_25_and_stable_winrate_15pp():
    a,b=cohorts()
    a,b=promote_once(a,b,0)
    aa,bb=list(a),list(b)
    aa[0]=metrics(VARIANTS[0].variant_id,"TRAIN",trades=49)
    assert screen(tuple(aa),b).winner_id is None
    bb[0]=metrics(VARIANTS[0].variant_id,"VALIDATE",trades=24)
    assert screen(a,tuple(bb)).winner_id is None
    bb[0]=metrics(VARIANTS[0].variant_id,"VALIDATE",wr="0.61")
    assert screen(a,tuple(bb)).winner_id is None
    bb[0]=metrics(VARIANTS[0].variant_id,"VALIDATE",wr="0.60")
    assert screen(a,tuple(bb)).winner_id==VARIANTS[0].variant_id


def test_max_dd_both_segments_strictly_below_twenty():
    a,b=promote_once(*cohorts(),0)
    x=list(a)
    x[0]=metrics(VARIANTS[0].variant_id,"TRAIN",dd="20")
    assert screen(tuple(x),b).winner_id is None
    y=list(b)
    y[0]=metrics(VARIANTS[0].variant_id,"VALIDATE",dd="20")
    assert screen(a,tuple(y)).winner_id is None
    assert MAX_DD_PCT==Decimal("20")


def test_only_one_winner_by_validate_pf_no_peeking_and_tie_id():
    a,b=promote_once(*cohorts(),0,v_pf="1.40")
    a,b=promote_once(a,b,2,v_pf="1.80")
    decision=screen(a,b)
    assert decision.status is ScreeningStatus.ONE_WINNER_LOCKED
    assert decision.winner_id==VARIANTS[2].variant_id
    assert len(decision.passing_variant_ids)==2
    assert internal_test_decision(
        metrics(decision.winner_id,"INTERNAL_TEST",pf="1.20"),decision
    )=="PAPER_3_MONTHS_PROSPECTIVE_REQUIRED"
    assert PF_TEST==Decimal("1.20")
    assert internal_test_decision(
        metrics(decision.winner_id,"INTERNAL_TEST",pf="1.19"),decision
    )=="INTERNAL_TEST_NO_GO_CLOSE_FEATURE_SET"


def test_three_pass_requires_split_review_before_internal_test():
    a,b=cohorts()
    for i in (0,5,9):
        a,b=promote_once(a,b,i)
    d=screen(a,b)
    assert d.status is ScreeningStatus.REVIEW_REQUIRED
    assert len(d.passing_variant_ids)==3
    assert not d.test_internal_authorized
    with pytest.raises(ValueError,match="violation"):
        internal_test_decision(
            metrics(d.winner_id,"INTERNAL_TEST"),d,
        )


def test_no_96_run_on_missing_2022_or_cost_data():
    with pytest.raises(ValueError,match="GATE_BLOCKED"):
        screen(*cohorts(),data=False)
    with pytest.raises(ValueError,match="GATE_BLOCKED"):
        screen(*cohorts(),cost=False)


def test_97th_variant_and_duplicate_cannot_be_smuggled_in():
    a,b=cohorts()
    with pytest.raises(ValueError,match="exactly 96"):
        screen(a[:-1],b)
    aa=list(a)
    aa[1]=aa[0]
    with pytest.raises(ValueError,match="exactly 96|duplicated"):
        screen(tuple(aa),b)
    aa=list(a)
    aa[1]=metrics("QALPHA-V097","TRAIN")
    with pytest.raises(ValueError,match="97th"):
        screen(tuple(aa),b)


def test_wrong_segment_or_winner_cannot_advance():
    a,b=promote_once(*cohorts(),0)
    d=screen(a,b)
    with pytest.raises(ValueError,match="violation"):
        internal_test_decision(
            metrics(VARIANTS[1].variant_id,"INTERNAL_TEST"),d,
        )
    with pytest.raises(ValueError,match="violation"):
        internal_test_decision(
            metrics(d.winner_id,"VALIDATE"),d,
        )


def test_registry_committed_in_github_matches_exact_manifest_no_hidden_97th():
    root=Path(__file__).resolve().parents[3]
    file=root / (
        "docs/research/"
        "QORE_ALPHA_V1_FROZEN96_VARIANT_REGISTRY_2026-10-11.json"
    )
    registry=json.loads(file.read_text(encoding="utf-8"))
    manifest=frozen_manifest()
    assert registry["variants"]==manifest["variants"]
    assert registry["frozen_manifest_sha256"]==manifest["sha256"]
    assert registry["holdout"]=="SEALED_NOT_ACCESSIBLE"
