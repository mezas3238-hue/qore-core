"""E3 causal ATR14, normalized versus original state, paired-date statistics."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.qore_london_after_asia_raid_paths_v1 import at
from qore.infrastructure.trader_lab.qore_london_eurgbp_acceptance_atr_e3 import (
    E3_STATES, ORIG_STATES, atr14_m15_asia, block_bootstrap,
    classify_acceptance, four_cells,
)

DAY=date(2026, 7, 15)


def m1(t, open="1.10000", high="1.10020",
       low="1.09980", close="1.10000"):
    return CapitalizerM1Bar(
        symbol="EURUSD",opened_at=t,closed_at=t+timedelta(minutes=1),
        open=Decimal(open),high=Decimal(high),low=Decimal(low),
        close=Decimal(close),volume=1,digits=5,
    )


def asian_m1():
    start=at(DAY-timedelta(days=1),20)
    return {start+timedelta(minutes=i):m1(start+timedelta(minutes=i))
            for i in range(240)}


def test_exact_native_asia_atr14_M15_is_nonzero():
    bars=asian_m1()
    atr,n=atr14_m15_asia(bars,DAY)
    assert n==240
    assert atr==Decimal("0.00040")
    # Future hourly movement must never change pre-raid ATR.
    post=at(DAY,2)+timedelta(minutes=90)
    bars[post]=m1(post,open="1.30000",high="1.40000",
                  low="1.20000",close="1.30000")
    assert atr14_m15_asia(bars,DAY)==(atr,240)


def test_fails_closed_on_missing_asia_minute():
    bars=asian_m1()
    bars.pop(at(DAY-timedelta(days=1),20)+timedelta(minutes=60))
    assert atr14_m15_asia(bars,DAY) is None


def test_acceptance_normalized_without_three_closes():
    atr=Decimal("0.00040")
    low=Decimal("1.09900")
    high=Decimal("1.10000")
    state,z=classify_acceptance(
        Decimal("1.10025"),low,high,"HIGH",atr
    )
    assert state=="ACCEPTED_ATR_0P5"
    assert z==Decimal("0.625")
    assert classify_acceptance(Decimal("1.10010"),low,high,"HIGH",atr)[0]=="OUTSIDE_WEAK"
    assert classify_acceptance(Decimal("1.09950"),low,high,"HIGH",atr)[0]=="RECLAIM_INSIDE"
    assert classify_acceptance(Decimal("1.09850"),low,high,"HIGH",atr)[0]=="OPPOSITE_OUTSIDE"


def test_symmetric_LOW_raid_positive_extension():
    st,z=classify_acceptance(Decimal("1.09870"),Decimal("1.09900"),
                              Decimal("1.10100"),"LOW",Decimal(".0004"))
    assert st=="ACCEPTED_ATR_0P5"
    assert z==Decimal(".75")


def test_reject_impossible_atr_or_side():
    with pytest.raises(ValueError):
        classify_acceptance(Decimal("1.10"),Decimal("1.09"),Decimal("1.11"),"HIGH",Decimal(0))
    with pytest.raises(ValueError):
        classify_acceptance(Decimal("1.10"),Decimal("1.09"),Decimal("1.11"),"BUY",Decimal(".001"))


def test_four_cell_interaction_and_paired_bootstrap():
    rows=[]
    for day in range(1,16):
        for sym in ("EURUSD","GBPUSD"):
            for st in ORIG_STATES:
                rows.append({
                    "ny_day":f"2026-07-{day:02d}", "symbol":sym,
                    "original_state":st, "E3_state": (
                        "ACCEPTED_ATR_0P5" if st=="ACCEPTED_OUTSIDE" else st
                    ),
                    "status":"CHECKPOINT_VALID",
                    "terminal_60":("REVERSAL" if (day%2==0 or sym=="EURUSD")
                                   and st=="RECLAIM_INSIDE" else "NEUTRAL"),
                })
    e=four_cells(rows,"original_state",ORIG_STATES)
    assert e is not None
    assert e["interaction_EUR_minus_GBP"]>0
    boot=block_bootstrap(rows,"E3_state",E3_STATES,
                         sorted({r["ny_day"] for r in rows}),reps=24)
    assert boot["valid"]==24
    assert boot["CI95"][0] is not None
    assert boot["paired_NY_block_dates"]==5
