"""Fail-closed frozen identities and common NY day-block bootstrap tests."""
from __future__ import annotations

import pytest

from qore.infrastructure.trader_lab.qore_london_e3_f1_f2_falsification import (
    CELLS, SCENARIOS, any_zero_ci, build_date_vectors, cell_counts,
    combine, decide_f1, interaction, moving_block_bootstrap,
)


def mk(day:str,symbol:str,state:str,rev:bool,known:bool=True)->dict:
    return {
        "symbol":symbol,"ny_day":day,"status":"CHECKPOINT_VALID",
        "E3_state":state,
        "terminal_60":"REVERSAL" if rev else "NEUTRAL",
        "H4_E2_status":"H4_ALIGNED_WITH_RAID" if known else "H4_PROXY_UNKNOWN_LOW_COVERAGE",
    }


def test_four_cell_difference_and_same_dates():
    dates=[f"2026-07-{i:02d}" for i in range(1,11)]
    rows=[]
    for i,d in enumerate(dates):
        for s in ("EURUSD","GBPUSD"):
            for state in ("RECLAIM_INSIDE","ACCEPTED_ATR_0P5"):
                rows.append(mk(d,s,state,s=="EURUSD" and state=="RECLAIM_INSIDE" or (
                    s=="GBPUSD" and state=="ACCEPTED_ATR_0P5"),i>2))
    full=build_date_vectors(rows,dates,"FULL")
    known=build_date_vectors(rows,dates,"H4_KNOWN")
    unknown=build_date_vectors(rows,dates,"H4_UNKNOWN")
    assert len(full)==len(known)==len(unknown)==10
    assert sum(combine(full)[::2])==40
    assert sum(combine(known)[::2])==28
    assert sum(combine(unknown)[::2])==12
    assert interaction(combine(full))==pytest.approx(2.0)
    assert cell_counts(combine(full))["EURUSD|RECLAIM_INSIDE"]["reversal"]==10
    assert len(CELLS)==4


def test_date_blocks_are_reproducible_and_do_not_mix_symbols():
    dates=[f"2026-07-{i:02d}" for i in range(1,12)]
    rows=[mk(d,s,state,(i%3)==0,True)
          for i,d in enumerate(dates)
          for s in ("EURUSD","GBPUSD")
          for state in ("RECLAIM_INSIDE","ACCEPTED_ATR_0P5")]
    a=build_date_vectors(rows,dates,"FULL")
    seed=7182
    p=moving_block_bootstrap(a,seed,70)
    q=moving_block_bootstrap(a,seed,70)
    assert p==q
    assert p["valid"]==70
    assert p["paired_date_blocks"]==5
    assert p["confidence_interval_95"] == [0,0]


def test_f1_no_promotion_on_unstable_confidence_interval():
    uncertain={"low_support":False,"confidence_interval_95":[-.11,+.15]}
    assert decide_f1(.22,.14,uncertain)["status"]=="F1_FAIL_PROMOTION_CI_CROSSES_ZERO"
    assert decide_f1(.22,.04,uncertain)["status"]=="F1_COLLAPSE"
    assert any_zero_ci(uncertain)
    secure={"low_support":False,"confidence_interval_95":[.01,.23]}
    assert decide_f1(.22,.15,secure)["status"]=="F1_SURVIVES_HISTORICAL"


def test_invalid_scenario_rejected():
    with pytest.raises(ValueError):
        build_date_vectors([],[ "2026-07-01" ],"TRADER")
    assert SCENARIOS==("FULL","H4_KNOWN","H4_UNKNOWN")
