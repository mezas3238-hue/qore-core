"""TTrades intermediate swing hierarchy: triple short-term, no future MSS."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar, Side
from scripts.vt31_m3_intermediate_swing_hierarchy_v5_20261015 import (
    V4_STATES,
    intermediate_swing_source_geometry,
)


def candle(at, *, high="120", low="80", close="100"):
    return M1Bar(
        at,at+timedelta(minutes=1),
        Decimal("100"),Decimal(high),Decimal(low),Decimal(close),
    )


def long_series():
    t=datetime(2025,7,1,14,tzinfo=UTC)
    highs=("101","102","108","101","103","112","102","103","109","101","116")
    closes=("100",)*10+("115",)
    return tuple(candle(t+timedelta(minutes=i),high=h,close=c)
                 for i,(h,c) in enumerate(zip(highs,closes,strict=True)))


def short_series():
    t=datetime(2025,1,15,15,tzinfo=UTC)
    lows=("98","97","92","99","97","88","99","97","94","99","84")
    closes=("100",)*10+("85",)
    return tuple(candle(t+timedelta(minutes=i),low=lo,close=c)
                 for i,(lo,c) in enumerate(zip(lows,closes,strict=True)))


def test_bullish_one_intermediate_triangular_source_component_not_mss():
    x=long_series()
    a=intermediate_swing_source_geometry(
        x,side=Side.LONG,first_return_at=x[0].closed_at,
        as_of=x[-1].closed_at,
    )
    assert a.state=="SINGLE_SOURCE_INTERMEDIATE_GEOMETRY_COMPONENT_ONLY"
    assert a.candidate_short_term_same_kind_count==3
    assert a.confirmed_intermediate_geometries==1
    assert a.freshly_crossed_intermediate_geometries==1
    assert a.single_candidate_confirmed_at==x[9].closed_at
    assert a.single_candidate_confirmed_at<a.as_of
    assert not a.author_protected_swing_identity_certified
    assert not a.displacement_author_certified


def test_bearish_inverse_intermediate_low():
    x=short_series()
    a=intermediate_swing_source_geometry(
        x,side=Side.SHORT,first_return_at=x[0].closed_at,
        as_of=x[-1].closed_at,
    )
    assert a.state=="SINGLE_SOURCE_INTERMEDIATE_GEOMETRY_COMPONENT_ONLY"
    assert a.single_candidate_confirmed_at==x[9].closed_at


def test_right_short_term_not_confirmed_at_same_break_candle():
    x=long_series()
    a=intermediate_swing_source_geometry(
        x[:10],side=Side.LONG,first_return_at=x[0].closed_at,
        as_of=x[9].closed_at,
    )
    assert a.state=="NO_INTERMEDIATE_CONFIRMED_AT_CAUSAL_ASOF"
    assert a.freshly_crossed_intermediate_geometries==0


def test_no_double_count_once_previous_close_above_intermediate():
    x=long_series()
    t=x[-1].closed_at
    after=candle(t,high="117",close="115")
    a=intermediate_swing_source_geometry(
        x+(after,),side=Side.LONG,
        first_return_at=x[0].closed_at,as_of=after.closed_at,
    )
    assert a.state=="NO_INTERMEDIATE_CONFIRMED_AT_CAUSAL_ASOF"
    assert a.freshly_crossed_intermediate_geometries==0


def test_tied_intermediate_extremum_not_source_certified():
    x=list(long_series())
    # Center swing and its left neighbour both =112 => no strict center.
    x[2]=candle(x[2].opened_at,high="112")
    a=intermediate_swing_source_geometry(
        tuple(x),side=Side.LONG,
        first_return_at=x[0].closed_at,as_of=x[-1].closed_at,
    )
    assert a.state=="NO_INTERMEDIATE_CONFIRMED_AT_CAUSAL_ASOF"


def test_two_intermediates_do_not_choose_best_price_or_pnl():
    t=datetime(2025,7,1,14,tzinfo=UTC)
    rows=[candle(t+timedelta(minutes=i),high="101") for i in range(17)]
    for i,high in ((2,"105"),(5,"113"),(8,"109"),(11,"114"),(14,"106")):
        rows[i]=candle(rows[i].opened_at,high=high)
    rows[16]=candle(rows[16].opened_at,high="120",close="119")
    a=intermediate_swing_source_geometry(
        tuple(rows),side=Side.LONG,
        first_return_at=rows[0].closed_at,as_of=rows[-1].closed_at,
    )
    assert a.state=="MULTIPLE_INTERMEDIATE_PIVOTS_UNKNOWN"
    assert a.freshly_crossed_intermediate_geometries>=2
    assert a.single_candidate_confirmed_at is None


def test_gap_missing_M1_naive_source_and_future_asof_all_rejected():
    rows=long_series()
    with pytest.raises(ValueError,match="SOURCE_GAP"):
        intermediate_swing_source_geometry(
            rows[:3]+rows[4:],side=Side.LONG,
            first_return_at=rows[0].closed_at,as_of=rows[-1].closed_at,
        )
    with pytest.raises(ValueError,match="AWARE_TIME"):
        intermediate_swing_source_geometry(
            rows,side=Side.LONG,
            first_return_at=datetime(2025,7,1,14),
            as_of=rows[-1].closed_at,
        )
    with pytest.raises(ValueError,match="ASOF_NOT_CLOSED"):
        intermediate_swing_source_geometry(
            rows,side=Side.LONG,
            first_return_at=rows[0].closed_at,
            as_of=rows[-2].closed_at,
        )


def test_original_v4_318_unknown_is_not_redefined_as_author_trade():
    assert V4_STATES=={
        "SINGLE_CONFIRMED_SWING_CLOSE_COMPONENT_ONLY":96,
        "MULTIPLE_MSS_SWING_REFERENCE_UNKNOWN":318,
        "NO_ATTESTED_STRUCTURAL_CLOSE_COMPONENT":69,
    }
