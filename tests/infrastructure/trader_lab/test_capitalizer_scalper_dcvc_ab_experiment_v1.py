"""DCVC negative leakage and preregistered classifier controls.

These are fixtures, never nine-market profitability evidence.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_dcvc_ab_experiment_v1 import (
    COSTS,
    DCVCState,
    aggregate,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_dcvc_causal_features_v1 import (
    observe,
    safe_record,
)

AT = datetime(2026, 1, 5, 10, tzinfo=UTC)


def _source() -> V49Opportunity:
    return V49Opportunity(
        symbol="AUDJPY",session="ASIA",operating_date="2026-01-05",
        h1_state_direction="BULLISH",
        h1_state_from=(AT-timedelta(hours=2)).isoformat(),
        h1_state_until=(AT+timedelta(hours=1)).isoformat(),
        h1_state_basis="CANDLE2_REVERSAL",
        m15_setup_confirmed_at=(AT-timedelta(minutes=15)).isoformat(),
        m15_protected_swing_price="99",
        m1_trigger_confirmed_at=AT.isoformat(),
        m1_trigger_family="FVG_RETRACE_CISD",
        decision_reference_price="102.40",
        structural_target_witness_price="104.0",
    )


def _bars() -> tuple[CapitalizerM1Bar, ...]:
    out=[]
    for i in range(241):
        close=Decimal("100")+Decimal(i)/Decimal(100)
        opened=AT-timedelta(minutes=241-i)
        out.append(CapitalizerM1Bar(
            symbol="AUDJPY",opened_at=opened,
            closed_at=opened+timedelta(minutes=1),
            open=close,high=close+Decimal("0.1"),
            low=close-Decimal("0.1"),close=close,
            volume=100,digits=3,
        ))
    return tuple(out)


def test_exact_closed_prefix_and_future_ohlc_isolation() -> None:
    original=_source()
    bars=_bars()
    observed=observe(original,bars,tuple(x.closed_at for x in bars))
    assert observed.regime=="HIGH_VOL_TREND"
    assert observed.native_last_m1_closed_at==AT.isoformat()
    assert not observed.native_bid_ask_present
    assert not observed.m30_m3_author_cisd_confirmed
    output=safe_record(observed)
    assert "realized_r" not in output
    assert "h1_state_until" not in output
    assert "future_winner" not in output
    future=replace(bars[-1],opened_at=AT,closed_at=AT+timedelta(minutes=1),
                   close=Decimal("999999"),high=Decimal("1000000"))
    assert observe(original,(*bars,future),
                   (*tuple(x.closed_at for x in bars),future.closed_at))==observed


def test_missing_native_bar_gives_unknown_not_interpolation() -> None:
    bars=_bars()
    bad=(*bars[:100],*bars[101:])
    observed=observe(_source(),bad,tuple(x.closed_at for x in bad))
    assert observed.regime=="UNKNOWN"
    assert observed.relative_volatility is None


def test_no_m1_future_decision_or_mutated_frozen_fill() -> None:
    bars=_bars()
    with pytest.raises(ValueError,match="not exact"):
        observe(replace(_source(),
                        m1_trigger_confirmed_at=(AT+timedelta(minutes=1)).isoformat()),
                bars,tuple(x.closed_at for x in bars))
    with pytest.raises(ValueError,match="reference entry"):
        observe(replace(_source(),decision_reference_price="555"),
                bars,tuple(x.closed_at for x in bars))


def test_classifier_depends_only_on_predecision_features_and_settled_b() -> None:
    bars=_bars()
    item=observe(_source(),bars,tuple(x.closed_at for x in bars))
    state=DCVCState()
    for _ in range(60):
        state.settle(item.regime,Decimal("-1"))
    first=state.admit(item)
    assert first[0] is False
    assert first[1]=="FROZEN_POSTERIOR_EXPECTANCY"
    assert state.total==60
    # Changing a trade's future R is impossible from admit signature.
    assert state.admit(item)==first


def test_cost_grid_fixed_and_no_fake_nine_market(tmp_path) -> None:
    assert COSTS==(Decimal("0"),Decimal("0.025"),
                   Decimal("0.05"),Decimal("0.10"))
    with pytest.raises(ValueError,match="nine V49"):
        aggregate(tmp_path,tmp_path)
