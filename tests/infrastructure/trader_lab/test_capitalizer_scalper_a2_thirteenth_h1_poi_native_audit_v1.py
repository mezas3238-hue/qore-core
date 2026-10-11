"""Audit13 H1 POI source-reconstruction is evidence, not a TTrades gate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_scalper_a2_thirteenth_h1_poi_native_audit_v1 as audit,
)
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import (
    V48AggregatedBar,
    V48H1BiasEvent,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
)


def _source(*, inherited: bool=False) -> V49Opportunity:
    basis="CANDLE2_REVERSAL:SWING_LOW"
    if inherited:
        basis="SESSION_INHERITED:"+basis
    return V49Opportunity(
        symbol="EURUSD",session="LONDON",operating_date="2026-01-10",
        h1_state_direction="BULLISH",
        h1_state_from="2026-01-10T12:00:00+00:00",
        h1_state_until="2026-01-10T17:00:00+00:00",
        h1_state_basis=basis,
        m15_setup_confirmed_at="2026-01-10T12:15:00+00:00",
        m15_protected_swing_price="1.1",
        m1_trigger_confirmed_at="2026-01-10T12:30:00+00:00",
        m1_trigger_family="LIQUIDITY_SWEEP_CISD",
        decision_reference_price="1.2",
        structural_target_witness_price="1.3",
    )


def _event() -> V48H1BiasEvent:
    return V48H1BiasEvent(
        confirmed_at=datetime(2026,1,10,12,tzinfo=UTC),
        direction=CapitalizerSourceDirection.BULLISH,
        closure_kind="CANDLE2_REVERSAL",poi_kind="SWING_LOW",
    )


def test_uninherited_matches_exact_event_not_any_nearby_label() -> None:
    assert audit.choose_origin((_event(),),_source())==_event()
    assert audit.choose_origin((),_source()) is None


def test_inherited_origin_uses_last_pre_session_closure() -> None:
    older=V48H1BiasEvent(
        confirmed_at=_event().confirmed_at-timedelta(hours=1),
        direction=_event().direction,
        closure_kind=_event().closure_kind,poi_kind=_event().poi_kind,
    )
    assert audit.choose_origin((older,),_source(inherited=True))==older
    assert audit.choose_origin((_event(),),_source(inherited=True)) is None


def test_poi_requires_completed_three_candle_formation() -> None:
    base=datetime(2026,1,10,0,tzinfo=UTC)
    bars=tuple(
        V48AggregatedBar(
            opened_at=base+timedelta(hours=i),
            closed_at=base+timedelta(hours=i+1),
            source=CapitalizerSourceBar(
                open=Decimal("1.10"), high=Decimal(str(1.2+i/100)),
                low=Decimal("1.0"),close=Decimal("1.11"),
            ),
            minute_count=60,
        )
        for i in range(2)
    )
    assert audit.make_pois(bars)==()
    assert audit.poi_witness(bars,(),_event())=={
        "source_event_reconstructed":False
    }


def test_no_nine_markets_refuses_certification(tmp_path:Path) -> None:
    with pytest.raises(ValueError,match="9 markets"):
        audit.aggregate(tmp_path)
