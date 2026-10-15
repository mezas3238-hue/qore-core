"""First-fail frozen M30/M3 candidate census: no lookahead, no fake author PASS."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_a_m30m3_frozen_family_source_funnel_v1 import (
    STAGES,
    _sample_records,
    _within_frozen_owner_windows,
    bullish_c2_geometry,
    classify,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

T=datetime(2026,10,15,12,tzinfo=UTC)


def bar(t, minutes, op="101", hi="102", lo="100", cl="101"):
    return Vt08B01Bar(
        opened_at=t,closed_at=t+timedelta(minutes=minutes),
        open=Decimal(op),high=Decimal(hi),low=Decimal(lo),close=Decimal(cl),
    )


def case(c2_low="99", c2_high="101.5", c2_open="100", c2_close="101.2"):
    c1_open=T
    c2_open_at=T+timedelta(minutes=30)
    m3_c1=tuple(bar(c1_open+timedelta(minutes=3*i),3) for i in range(10))
    m15_c1=tuple(bar(c1_open+timedelta(minutes=15*i),15) for i in range(2))
    m3_c2=tuple(bar(
        c2_open_at+timedelta(minutes=3*i),3,
        op=c2_open,hi=c2_high,lo=c2_low,cl=c2_close,
    ) for i in range(10))
    m15_c2=tuple(bar(
        c2_open_at+timedelta(minutes=15*i),15,
        op=c2_open,hi=c2_high,lo=c2_low,cl=c2_close,
    ) for i in range(2))
    return m3_c1,m3_c2,m15_c1,m15_c2


def test_missing_m30_constituent_first_failure():
    a,b,c,d=case()
    assert classify(c1=None,c2=b,c1_m15=c,c2_m15=d)[0] == STAGES[0]


def test_cross_source_ohlc_mismatch_is_not_silently_repaired():
    a,b,c,d=case()
    m15_c2=tuple(bar(x.opened_at,15,hi="103",op="100",lo="99",cl="101.2") for x in d)
    stage,_=classify(c1=a,c2=b,c1_m15=c,c2_m15=m15_c2)
    assert stage == STAGES[1]


@pytest.mark.parametrize("low,high,op,close",[
    ("100","101.5","100","101.2"),
    ("99","103","100","101.2"),
    ("99","101.5","101.4","101.2"),
    ("99","101.5","100","99.5"),
])
def test_non_bullish_or_dual_sweep_c2_is_negative(low,high,op,close):
    a,b,c,d=case(low,high,op,close)
    result,_=classify(c1=a,c2=b,c1_m15=c,c2_m15=d)
    assert result == STAGES[2]


def test_geometric_low_sweep_is_not_author_complete():
    a,b,c,d=case()
    assert bullish_c2_geometry(
        bar(T,30),bar(T+timedelta(minutes=30),30,"100","101.5","99","101.2"),
    )
    stage,details=classify(c1=a,c2=b,c1_m15=c,c2_m15=d)
    assert stage in STAGES[3:]
    assert details.get("methodology_complete") is not True


def test_c1_c2_source_clock_must_be_contiguous():
    c1=bar(T,30)
    c2=bar(T+timedelta(minutes=33),30,"100","101.5","99","101.2")
    with pytest.raises(ValueError,match="noncontiguous"):
        bullish_c2_geometry(c1,c2)


def test_reviewer_case_selection_is_chronology_only():
    rows=[{"n":i} for i in range(101)]
    assert [x["n"] for x in _sample_records(rows)] == [0,14,28,42,57,71,85,100]
    assert _sample_records(rows[:4]) == rows[:4]


def test_owner_windows_follow_new_york_dst_hour_not_utc_fixed_hour():
    from zoneinfo import ZoneInfo
    ny=ZoneInfo("America/New_York")
    for month in (1,7):
        assert _within_frozen_owner_windows(datetime(2025,month,15,1,tzinfo=ny))
        assert _within_frozen_owner_windows(datetime(2025,month,15,12,30,tzinfo=ny))
        assert not _within_frozen_owner_windows(datetime(2025,month,15,13,tzinfo=ny))
        assert not _within_frozen_owner_windows(datetime(2025,month,15,0,30,tzinfo=ny))
