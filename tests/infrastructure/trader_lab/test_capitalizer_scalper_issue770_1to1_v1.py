"""Issue770 barrier geometry, gap censor and STOP_FIRST negative regressions."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_issue770_1to1_aggregate_v1 import (
    COSTS,
    cohort_metrics,
    quantile,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_issue770_1to1_market_v1 import (
    barrier_prices,
    scan,
)

AT=datetime(2026,1,2,14,0,tzinfo=UTC)


def bar(i:int,low:str,high:str,close:str)->CapitalizerM1Bar:
    opened=AT+timedelta(minutes=i)
    return CapitalizerM1Bar(
        symbol="AUDUSD",opened_at=opened,
        closed_at=opened+timedelta(minutes=1),
        open=Decimal("100"),high=Decimal(high),low=Decimal(low),
        close=Decimal(close),volume=10,digits=4,
    )


def run(bars:tuple[CapitalizerM1Bar,...],*,capped:bool=False,
        direction:str="LONG",stop:str="99")->dict:
    return scan(
        bars=bars,entry_at=AT,entry=Decimal("100"),
        stop=Decimal(stop),direction=direction,capped=capped,
    )


def test_one_to_one_side_geometry_and_reversed_direction() -> None:
    assert barrier_prices(Decimal("100"),Decimal("99"),"LONG")==(
        Decimal("99"),Decimal("101")
    )
    assert barrier_prices(Decimal("100"),Decimal("101"),"SHORT")==(
        Decimal("101"),Decimal("99")
    )
    with pytest.raises(ValueError,match="zero risk"):
        barrier_prices(Decimal("100"),Decimal("100"),"LONG")
    with pytest.raises(ValueError,match="invalid long"):
        barrier_prices(Decimal("100"),Decimal("101"),"LONG")


def test_dual_touch_is_stop_first_target_first_sensitivity_only() -> None:
    item=run((bar(0,"98.5","101.5","100"),))
    assert item["status"]=="STOP"
    assert item["R"]=="-1"
    assert item["both_touched"]
    assert item["target_first_sensitivity_R"]=="1"
    item_short=run((bar(0,"98.5","101.5","100"),),
                   direction="SHORT",stop="101")
    assert item_short["status"]=="STOP"


def test_pure_continues_beyond_session_not_session_exit() -> None:
    item=run((bar(0,"99.1","100.1","100"),
              bar(1,"99.1","101.1","100.5")))
    assert item["status"]=="TARGET"
    item_short=run((bar(0,"99.1","100.1","100"),),capped=True)
    assert item_short["status"]=="SESSION_EXIT"


def test_missing_m1_is_censored_and_not_assumed_filled() -> None:
    item=run((bar(0,"99.5","100.5","100"),
              bar(2,"98.0","102.0","100")))
    assert item["status"]=="RIGHT_CENSORED_PRICE_GAP"
    assert item["R"] is None
    assert item["m1_bars_held"]==1
    assert item["gap_next_observed_at"]==(AT+timedelta(minutes=2)).isoformat()
    capped=run((bar(0,"99.5","100.5","100"),
                bar(2,"98.0","102.0","100")),capped=True)
    assert capped["status"]=="GAP_CENSORED_SESSION"


def test_end_of_feed_censor_does_not_become_loss() -> None:
    item=run((bar(0,"99.5","100.5","100"),))
    assert item["status"]=="RIGHT_CENSORED_END_OF_FEED"
    assert item["R"] is None
    with pytest.raises(ValueError,match="exact first"):
        run((bar(1,"99.5","100.5","100"),))


def test_all_2020_denominator_censor_bounds_and_cost_grid() -> None:
    assert COSTS==(
        Decimal("0"),Decimal("0.025"),Decimal("0.05"),Decimal("0.10")
    )
    a={
        "source_opportunity_id":"a","entry_at":AT.isoformat(),"symbol":"AUDUSD",
        "pure_1to1":{"status":"TARGET","exit_at":AT.isoformat(),
                      "R":"1","both_touched":False,
                      "m1_bars_held":1,"target_first_sensitivity_R":"1"},
    }
    b={
        "source_opportunity_id":"b","entry_at":AT.isoformat(),"symbol":"AUDUSD",
        "pure_1to1":{"status":"RIGHT_CENSORED_PRICE_GAP",
                      "exit_at":None,"R":None,"both_touched":False,
                      "m1_bars_held":2,"target_first_sensitivity_R":None},
    }
    result=cohort_metrics((a,b),"pure_1to1",Decimal("0.025"))
    assert result["source_intents"]==2
    assert result["resolved"]==1
    assert result["censored"]==1
    assert result["target_rate_all_lower_bound"]=="0.5"
    assert result["target_rate_all_upper_bound_if_censored_target"]=="1"
    assert result["expectancy_per_resolved_R"]=="0.975"
    with pytest.raises(ValueError,match="empty"):
        quantile([],0.5)
