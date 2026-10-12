"""No genuine FX carry outcomes: all forward data in tests is explicitly synthetic."""
from __future__ import annotations

import math
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest

from qore.research.alpha2_fx28_carry_one_test import (
    CCYS, FX28, ForwardWitness, _block3, one_month, summarize, validate_roster
)


def synthetic_quotes(ym=(2020,5), *, duplicate=False, missing=False):
    decision=datetime(ym[0],ym[1],5,0,30,tzinfo=UTC)
    observed=decision-timedelta(hours=1)
    # Eight independent CURRENCY money-market yields generate 28 pair spreads.
    y={c:0.005+i*.014 for i,c in enumerate(sorted(CCYS))}
    rows=[]
    for sym in FX28:
        carry=y[sym[:3]]-y[sym[3:]]
        spot=100.0
        forward=spot*math.exp(-carry/12)
        rows.append(ForwardWitness(
            symbol=sym,observed_at=observed,
            available_at=observed+timedelta(minutes=1),
            decision_at=decision,contractual_maturity=decision.date()+timedelta(days=30),
            spot_mid_asof=spot,forward_1m_mid_asof=forward,
            settlement_spot_mid=spot,evidence_source_uri="https://synthetic.invalid/fake-no-network",
            evidence_sha256="a"*64
        ))
    if missing:
        rows=rows[:-1]
    if duplicate:
        rows[-1]=rows[0]
    return rows


def test_eight_currency_full_graph_28_pairs_not_independent_signals():
    validate_roster()
    assert len(FX28)==28
    assert len(CCYS)==8
    assert {frozenset((s[:3],s[3:])) for s in FX28}=={
        frozenset((a,b)) for a in CCYS for b in CCYS if a!=b
    }


def test_exact_six_high_carry_long_six_low_carry_short_and_currency_concentration():
    o=one_month(date(2020,5,1),synthetic_quotes())
    assert len(o["long6"])==len(o["short6"])==6
    assert not set(o["long6"])&set(o["short6"])
    assert all(x["signed_gross_notional_weight"]==1/12 for x in o["ranked_selected_12"][:6])
    assert all(x["signed_gross_notional_weight"]==-1/12 for x in o["ranked_selected_12"][6:])
    assert o["assumed_2bps_each_side_for_gross_notional1_bps"]==4.0
    assert o["gross_minus_assumed_cost_proxy_bps"]==pytest.approx(o["gross_reference_bps"]-4)
    assert sum(o["currency_net_exposure_signed"].values())==pytest.approx(0)
    assert o["maximum_absolute_currency_exposure"]>0.1
    assert o["broker_NET_not_proven"] is True


@pytest.mark.parametrize("change", [
    {"available_at":datetime(2020,5,5,1,0,tzinfo=UTC)},
    {"observed_at":datetime(2020,5,5,2,0,tzinfo=UTC)},
    {"forward_1m_mid_asof":0.0},
    {"evidence_source_uri":"invented"},
    {"evidence_sha256":"0"*63},
])
def test_future_quotes_or_missing_forward_provenance_are_rejected(change):
    x=synthetic_quotes()[0]
    with pytest.raises(ValueError):
        replace(x,**change)


def test_one_missing_or_duplicate_symbol_fails_closed_no_27_carry_surrogate():
    for k in ({"missing":True},{"duplicate":True}):
        with pytest.raises(ValueError,match="INCOMPLETE_28"):
            one_month(date(2020,5,1),synthetic_quotes(**k))


def test_rank_snapshot_era_crossing_or_future_embargo_censored():
    for ym in ((2021,12),(2024,9)):
        # 2021-12 into diagnosis, or 2024-09 beyond embargo, never allowed
        with pytest.raises(ValueError,match="OUTSIDE_SOURCE_EMBARGO_OR_SPLIT"):
            synthetic_quotes(ym)


def test_one_snap_must_share_same_available_decision_and_prevent_month_cherry_pick():
    q=synthetic_quotes()
    q[0]=replace(q[0],decision_at=q[0].decision_at+timedelta(seconds=5))
    with pytest.raises(ValueError,match="SYNC_DECISION"):
        one_month(date(2020,5,1),q)


def test_no_hist_forward_is_identifiability_not_carry_failure():
    output=summarize([])
    assert output["status"]=="CARRY_NOT_IDENTIFIABLE_SPOT_ONLY"
    assert output["no_forward_factor_no_edge_test"] is True
    assert output["account_broker_NET_not_computed"] is True
    assert output["orders"]==0
    assert not output["UTC001_certified"]
    assert output["eras"]["DEVELOPMENT"]["executed_full28_months"]==0


def test_gross_and_cost_not_broker_net_with_one_synthetic_snapshot():
    one=one_month(date(2020,5,1),synthetic_quotes())
    report=summarize([one])
    assert report["status"]=="CARRY28_UNDERPOWERED"
    assert report["eras"]["DEVELOPMENT"]["executed_full28_months"]==1
    assert report["eras"]["DIAGNOSTIC"]["executed_full28_months"]==0


def test_bootstrap_reproducible_3_months_and_fixed_width():
    sample=[0.,2.,-3.,4.,-1.,3.]
    assert _block3(sample,seed=20261012)==_block3(sample,seed=20261012)
    ci=_block3(sample,seed=20261012)
    assert ci[0]<=ci[1]
