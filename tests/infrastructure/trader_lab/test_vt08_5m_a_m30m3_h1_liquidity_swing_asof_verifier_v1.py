"""P0 adversarial tests: pre-C2 H1 liquidity vs future swing/EQ activation."""
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_5m_a_m30m3_h1_liquidity_swing_asof_verifier_v1 import (
    ExternalPivotKind,
    closed_external_pivots,
    prior_h1_liquidity_context,
    verify_record,
)
from qore.infrastructure.trader_lab.vt08_5m_a_native_m30_m3_favorable_entry_v1 import (
    aggregate,
    analyze_setup,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

T = datetime(2026, 1, 14, 9, tzinfo=UTC)


def bar(t: datetime, o: str, hi: str, lo: str, cl: str, mins=60) -> Vt08B01Bar:
    return Vt08B01Bar(
        opened_at=t, closed_at=t + timedelta(minutes=mins),
        open=Decimal(o), high=Decimal(hi),
        low=Decimal(lo), close=Decimal(cl),
    )


def test_three_bar_high_known_only_after_right_closes():
    h1 = (
        bar(T-timedelta(hours=3), "95", "100", "90", "95"),
        bar(T-timedelta(hours=2), "95", "105", "92", "100"),
        bar(T-timedelta(hours=1), "100", "103", "93", "102"),
    )
    with pytest.raises(ValueError, match="future"):
        closed_external_pivots(h1, as_of=T-timedelta(minutes=15))
    records = closed_external_pivots(h1, as_of=T)
    assert len(records) == 1
    assert records[0].kind is ExternalPivotKind.HIGH
    assert records[0].extreme == Decimal("105")
    assert records[0].confirmed_at == T
    assert records[0].payload()["eq_regime_authorized"] == "false"


def test_pivot_low_and_doji_equal_highs_not_arbitrarily_resolved():
    h1 = (
        bar(T-timedelta(hours=3), "95", "105", "90", "95"),
        bar(T-timedelta(hours=2), "95", "105", "85", "100"),
        bar(T-timedelta(hours=1), "100", "102", "93", "102"),
    )
    result = closed_external_pivots(h1, as_of=T)
    assert len(result) == 1 and result[0].kind is ExternalPivotKind.LOW


def test_future_right_cannot_be_hidden_in_middle_timestamp():
    h1 = (
        bar(T-timedelta(hours=3), "95", "100", "90", "95"),
        bar(T-timedelta(hours=2), "95", "110", "90", "100"),
        bar(T, "100", "108", "93", "105"),
    )
    with pytest.raises(ValueError, match="continuous"):
        closed_external_pivots(h1, as_of=T+timedelta(hours=1))


def test_prior_h1_fvg_is_strictly_from_before_c2_open():
    m15 = {}
    start = T - timedelta(hours=3)
    for i in range(12):
        t = start + timedelta(minutes=i*15)
        # First H1 high=90, last H1 low=95: bullish FVG from 3 H1 bars.
        if i < 4:
            r = bar(t, "88", "90", "85", "89", 15)
        elif i < 8:
            r = bar(t, "89", "94", "87", "93", 15)
        else:
            r = bar(t, "96", "102", "95", "100", 15)
        m15[t] = r
    result = prior_h1_liquidity_context(m15, before_c2_open=T)
    assert result["status"] == "H1_PRE_C2_GEOMETRY_ONLY"
    assert result["h1_closed_fvg"]["lower"] == "90"
    assert result["h1_closed_fvg"]["upper"] == "95"
    assert result["h1_last_closed_at"] == T.isoformat()
    assert result["valid_C2_EQ_swing_confirmed"] is False


def test_incomplete_prior_h1_must_not_be_interpolated():
    m15 = {}
    start = T - timedelta(hours=3)
    for i in range(11):
        k = start+timedelta(minutes=i*15)
        m15[k] = bar(k, "95", "100", "94", "96", 15)
    result = prior_h1_liquidity_context(m15, before_c2_open=T)
    assert result["status"] == "H1_PRE_C2_SOURCE_INCOMPLETE"


def synthetic_verified_source():
    # C1 spans 08:30-09:00, C2 09:00-09:30 (M30) and prior H1 06:00-09:00
    c1start = T-timedelta(minutes=30)
    b1 = [
        bar(c1start+timedelta(minutes=3*i), "100", "101", "99", "100", 3)
        for i in range(10)
    ]
    b1[0] = bar(c1start, "100", "110", "95", "100", 3)
    b2 = [
        bar(T+timedelta(minutes=3*i), "104", "105", "103", "104", 3)
        for i in range(10)
    ]
    b2[0] = bar(T, "100", "101", "94", "96", 3)
    b2[1] = bar(T+timedelta(minutes=3), "96", "105", "96", "104", 3)
    c1 = aggregate(tuple(b1), period_minutes=30, member_minutes=3)
    c2 = aggregate(tuple(b2), period_minutes=30, member_minutes=3)
    c3 = bar(c2.closed_at, "104", "105", "101", "102", 3)
    obs = analyze_setup(
        market="EURJPY", c1=c1, c2=c2, c2_m3=tuple(b2),
        c3_first_m3=c3, c3_m3=(c3,),
    )
    assert obs["status"] == "M30_M3_SOURCE_GEOMETRY_ONLY"
    d3 = {z.opened_at:z for z in (*b1,*b2)}
    d15 = {}
    start=T-timedelta(hours=3)
    for i in range(10):
        at=start+timedelta(minutes=15*i)
        d15[at]=bar(at,"96","101","90","98",15)
    # Crucial two M15 windows from each native M3 source span.
    for bs in (b1,b2):
        for j in (0,5):
            seg=tuple(bs[j:j+5])
            c=aggregate(seg,period_minutes=15,member_minutes=3)
            d15[c.opened_at]=c
    return obs,d15,d3


def test_reverifier_recomputes_cisd_and_pre_c2_context():
    record,m15,m3=synthetic_verified_source()
    output=verify_record(record,m15_index=m15,m3_index=m3)
    assert output["status"]=="INDEPENDENT_M3_CISD_VERIFIED_HTF_POI_STILL_D"
    assert output["eq_C2_close_to_wick_regime_authorized"] is False
    assert output["h1_context_poi_source_complete"] is False
    assert output["cognitive_ready"] is False
    assert output["cisd_confirmed_at"] < output["c2_closed_at"]


def test_reverifier_refuses_ps_level_tamper():
    record,m15,m3=synthetic_verified_source()
    altered=dict(record,c2_m3_ps_price="999")
    with pytest.raises(ValueError,match="provenance mismatch"):
        verify_record(altered,m15_index=m15,m3_index=m3)


def test_reverifier_refuses_future_cisd_receipt():
    record,m15,m3=synthetic_verified_source()
    altered=dict(record,c2_m3_cisd_confirmed_at=(T+timedelta(hours=1)).isoformat())
    with pytest.raises(ValueError,match="provenance mismatch"):
        verify_record(altered,m15_index=m15,m3_index=m3)


def test_reverifier_refuses_ohlc_mismatch_even_if_m3_valid():
    record,m15,m3=synthetic_verified_source()
    altered=m15.copy()
    at=T
    altered[at]=replace(altered[at],high=altered[at].high+Decimal("1"))
    with pytest.raises(ValueError,match="independent replay"):
        verify_record(record,m15_index=altered,m3_index=m3)


def test_reverifier_refuses_forged_origin_id():
    record,m15,m3=synthetic_verified_source()
    altered=dict(record,origin_id="vt08-m30m3:forged")
    with pytest.raises(ValueError,match="structural ID mismatch"):
        verify_record(altered,m15_index=m15,m3_index=m3)


def test_reverifier_refuses_wrong_opposing_series_time():
    record,m15,m3=synthetic_verified_source()
    altered=dict(record,c2_m3_opposing_series_start=T.isoformat())
    with pytest.raises(ValueError,match="lineage mismatch"):
        verify_record(altered,m15_index=m15,m3_index=m3)
