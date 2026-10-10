"""Non-invasive source discrepancy types and native M1 post-hoc excursions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_cisd_381_discrepancy_forensic_v1 import (
    DIFFERENCE_TYPES,
    HorizonExcursion,
    _one_horizon,
    classify,
    excursions,
)

START=datetime(2026,5,4,10,tzinfo=UTC)


def _bar(i: int) -> CapitalizerM1Bar:
    t=START+timedelta(minutes=i)
    return CapitalizerM1Bar(
        symbol="EURUSD",opened_at=t,closed_at=t+timedelta(minutes=1),
        open=Decimal("100"),close=Decimal("100")+Decimal(i)/100,
        high=Decimal("100.6")+Decimal(i)/100,
        low=Decimal("99.4")+Decimal(i)/100,volume=1,digits=5,
    )


def test_mismatch_types_are_mutually_exclusive_and_causal() -> None:
    original=START+timedelta(minutes=22)
    assert classify(original,"FVG_RETRACE_CISD",original-timedelta(minutes=5),
                    "LIQUIDITY_SWEEP_CISD")=="SENSOR_EARLIER_THAN_V49"
    assert classify(original,"FVG_RETRACE_CISD",original+timedelta(minutes=2),
                    "LIQUIDITY_SWEEP_CISD")=="SENSOR_LATER_THAN_V49"
    assert classify(original,"FVG_RETRACE_CISD",original,
                    "LIQUIDITY_SWEEP_CISD")=="SAME_TIME_DIFFERENT_FAMILY"
    assert classify(original,"FVG_RETRACE_CISD",None,None)=="SENSOR_NOT_DETECTED"
    assert classify(original,"FVG_RETRACE_CISD",original,
                    "FVG_RETRACE_CISD")=="MATCHED"
    assert len(set(DIFFERENCE_TYPES))==5


def test_horizon_excur_requires_exact_native_m1_and_never_authorizes() -> None:
    bars=tuple(_bar(i) for i in range(70))
    times=tuple(b.opened_at for b in bars)
    got=excursions(
        bars,times,at=START+timedelta(minutes=1),
        session="LONDON",side=1,stop=Decimal("98"),
    )
    assert all(r.native_contiguous_m1 for r in got)
    assert got[0].mfe_r_original_m15_stop is not None
    assert Decimal(got[0].mae_price or "0")>=0
    assert got[0].authorizes_entry is False
    gaps=bars[:6]+bars[7:]
    missing=excursions(
        gaps,tuple(b.opened_at for b in gaps),
        at=START+timedelta(minutes=1),
        session="LONDON",side=1,stop=Decimal("98"),
    )
    assert all(not x.native_contiguous_m1 for x in missing)


def test_invalid_risk_geometry_not_used_as_valid_r_metric() -> None:
    bars=tuple(_bar(i) for i in range(70))
    got=excursions(bars,tuple(b.opened_at for b in bars),
                   at=START+timedelta(minutes=2),
                   session="LONDON",side=1,stop=Decimal("120"))
    assert got[0].native_contiguous_m1
    assert not got[0].risk_geometry_valid_at_observation
    assert got[0].mfe_r_original_m15_stop is None


def test_research_rows_cannot_be_misrepresented_as_actions() -> None:
    with pytest.raises(ValueError, match="research"):
        HorizonExcursion(
            30,True,"1","0.3","0.2","0.3","0.2",True,
            authorizes_entry=True,
        )


def test_pair_metrics_require_coverage_for_both_timestamps() -> None:
    assert _one_horizon((),30)["paired_n"]==0
