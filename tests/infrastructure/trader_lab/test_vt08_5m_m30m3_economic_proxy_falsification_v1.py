"""Pre-registered economic proxy adversarial unit tests, not real TTrades."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_5m_m30m3_economic_proxy_falsification_v1 import (
    _metrics,
    first_mother_per_ny_day,
    simulate_m30_window,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

T = datetime(2026, 10, 6, 9, tzinfo=UTC)
LONG = DemoTradingSetupSide.LONG


def bar(i: int, op: str, hi: str, lo: str, cl: str) -> Vt08B01Bar:
    t=T+timedelta(minutes=3*i)
    return Vt08B01Bar(
        opened_at=t,closed_at=t+timedelta(minutes=3),
        open=Decimal(op),high=Decimal(hi),
        low=Decimal(lo),close=Decimal(cl),
    )


def window(bars=None):
    result=[
        bar(0,"100","102","99","101"),
        bar(1,"101","101","100","100"),
    ]
    result += [
        bar(i,"100","100","99","100") for i in range(2,10)
    ]
    if bars:
        for i,x in bars.items():
            result[i]=x
    return tuple(result)


def run(bars=None,limit="98",stop="95",target="105"):
    return simulate_m30_window(
        side=LONG,entry_open=Decimal("100"),limit=Decimal(limit),
        stop=Decimal(stop),target=Decimal(target),
        m3_window=window(bars),
    )


def test_positional_expires_at_last_closed_m3():
    out=run()
    assert out["positional"]["status"]=="EXPIRE_C3_CLOSE"
    assert out["positional"]["gross_r"]=="0"
    assert out["cisd_limit"]["status"]=="NO_FILL"


def test_positional_both_stop_target_same_bar_stop_first():
    out=run({0:bar(0,"100","105","94","102")})
    assert out["positional"]["status"]=="STOP_FIRST_BOTH_HIT"
    assert out["positional"]["gross_r"]=="-1"
    assert out["cisd_limit"]["status"]=="AMBIGUOUS_TOUCH_STOP_FIRST"


def test_positional_target_only():
    out=run({0:bar(0,"100","106","99","105")})
    assert out["positional"]["status"]=="TARGET"
    assert out["positional"]["gross_r"]=="1"
    assert out["cisd_limit"]["status"]=="NO_FILL_EXIT_BEFORE_LIMIT"


def test_limit_fills_before_later_target():
    out=run({
        1:bar(1,"101","102","97","99"),
        2:bar(2,"99","105","98","105"),
    })
    assert out["cisd_limit"]["status"]=="TARGET"
    assert out["cisd_limit"]["gross_r"]==str(Decimal(7)/Decimal(3))


def test_limit_retest_and_target_same_candle_is_ambiguous_loss():
    out=run({1:bar(1,"101","105","97","103")})
    assert out["cisd_limit"]["status"]=="AMBIGUOUS_TOUCH_STOP_FIRST"
    assert out["cisd_limit"]["gross_r"]=="-1"


def test_no_limit_when_not_favorable_ex_ante():
    out=run(limit="101")
    assert out["cisd_limit"]["status"]=="NO_FAVORABLE_PREDECLARED_LIMIT"


def test_missing_m3_or_future_timestamps_rejected():
    with pytest.raises(ValueError,match="exactly 10"):
        simulate_m30_window(
            side=LONG,entry_open=Decimal("100"),limit=Decimal("98"),
            stop=Decimal("95"),target=Decimal("105"),
            m3_window=window()[:9],
        )
    series=list(window())
    series[1]=Vt08B01Bar(
        opened_at=series[1].opened_at+timedelta(minutes=3),
        closed_at=series[1].closed_at+timedelta(minutes=3),
        open=series[1].open,high=series[1].high,
        low=series[1].low,close=series[1].close,
    )
    with pytest.raises(ValueError,match="future/missing"):
        simulate_m30_window(
            side=LONG,entry_open=Decimal("100"),limit=Decimal("98"),
            stop=Decimal("95"),target=Decimal("105"),
            m3_window=tuple(series),
        )


def test_preentry_selection_does_not_look_at_retest_winning():
    a={
        "status":"M30_M3_SOURCE_GEOMETRY_ONLY",
        "market_ny_date":"2026-10-06",
        "origin_id":"first",
        "entry_positional_proposed_at":T.isoformat(),
        "retest":{"status":"NO_FILL"},
    }
    b={
        **a,
        "origin_id":"second",
        "entry_positional_proposed_at":(T+timedelta(minutes=30)).isoformat(),
        "retest":{"status":"CLEAN_OHLC_TOUCH_NOT_PHYSICAL_FILL"},
    }
    chosen=first_mother_per_ny_day([b,a])
    assert chosen[0]["origin_id"]=="first"
    assert len(chosen)==1


def test_costs_apply_only_hypothetical_fills_and_pf():
    records=[
        {"status":"TARGET","gross_r":"2","filled":True},
        {"status":"STOP","gross_r":"-1","filled":True},
        {"status":"NO_FILL","gross_r":"0","filled":False},
    ]
    gross=_metrics(records,cost=Decimal("0"))
    net=_metrics(records,cost=Decimal("0.10"))
    assert gross["profit_factor_net"]=="2"
    assert net["profit_factor_net"]==str(Decimal("1.9")/Decimal("1.1"))
    assert net["expectancy_net_r_per_signal_including_no_fills"]=="0.2666666666666666666666666667"
    assert net["no_fill"]==1


def test_bearish_negative_risk_and_positive_target():
    out=simulate_m30_window(
        side=DemoTradingSetupSide.SHORT,
        entry_open=Decimal("100"),limit=Decimal("102"),
        stop=Decimal("105"),target=Decimal("95"),
        m3_window=window({0:bar(0,"100","101","94","95")}),
    )
    assert out["positional"]["status"]=="TARGET"
    assert out["positional"]["gross_r"]=="1"
