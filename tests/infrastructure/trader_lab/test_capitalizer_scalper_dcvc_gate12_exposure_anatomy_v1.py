"""Contracts for DCVC Gate 1 null and Gate2 as-of reconstruction."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.capitalizer_scalper_dcvc_causal_features_v1 import (
    DCVCPredecision,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_dcvc_gate12_exposure_anatomy_v1 import (
    ASSUMED_COST_R,
    N_GLOBAL,
    N_POWER,
    N_STRATIFIED,
    SOURCE_N,
    TARGET_N,
    Data,
    _valid_sample,
    global_sample,
    holm_one_sided,
    percentile,
    source_data,
)


def test_predeclared_exposure_null_and_power_counts() -> None:
    assert (SOURCE_N,TARGET_N,N_GLOBAL,N_STRATIFIED,N_POWER)==(
        2876,266,2000,1000,1000,
    )
    assert ASSUMED_COST_R==0.025


def test_holm_familywise_adjustment_and_fixed_percentile() -> None:
    p=holm_one_sided({
        "PF":0.02,"expectancy":0.001,"DD":0.5,
    })
    assert p["expectancy"]==pytest.approx(0.003)
    assert p["PF"]==pytest.approx(0.04)
    assert p["DD"]==pytest.approx(0.5)
    assert percentile([3.0,1.0,2.0],0.5)==2.0
    with pytest.raises(ValueError,match="empty"):
        percentile([],0.25)


def _feature(sid:int)->DCVCPredecision:
    at=datetime(2026,5,10,12,tzinfo=UTC)
    return DCVCPredecision(
        source_opportunity_id=str(sid),
        symbol="USDJPY" if sid%2 else "EURUSD",
        session="NY",
        operating_date=(
            at+timedelta(days=sid//3)
        ).date().isoformat(),
        decision_at=at.isoformat(),
        source_h1_confirmed_at=(at-timedelta(hours=1)).isoformat(),
        source_m15_confirmed_at=(at-timedelta(minutes=15)).isoformat(),
        native_last_m1_closed_at=at.isoformat(),
        regime="UNKNOWN",
        relative_volatility=None,directional_efficiency=None,
        displacement_intensity=None,directional_persistence=None,
        planned_reward_r=None,m30_closed_m1_count=0,
        m3_closed_m1_count=0,features_known_at=at.isoformat(),
    )


def test_global_equal_266_sample_never_reads_future_outcomes() -> None:
    features={str(i):_feature(i) for i in range(290)}
    # Empty economics are intentional: selecting IDs MUST NOT read trade returns.
    data=Data(features,{}, {},frozenset(),frozenset())
    selected=global_sample(data,1234)
    assert len(selected)==266
    assert len(set(selected))==266
    assert global_sample(data,1234)==selected
    assert global_sample(data,1235)!=selected
    assert len(_valid_sample(data,sorted(features),2))==2


def test_insufficient_group_capacity_rejected(tmp_path) -> None:
    features={str(i):_feature(i) for i in range(2)}
    data=Data(features,{}, {},frozenset(),frozenset())
    with pytest.raises(ValueError,match="cannot satisfy"):
        _valid_sample(data,list(features),3)
    with pytest.raises(ValueError,match="9 native"):
        source_data(tmp_path,tmp_path)
