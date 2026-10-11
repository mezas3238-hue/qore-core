"""Posthoc mirror audit: paired identity, censor matching and cluster sign test."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from qore.infrastructure.trader_lab.capitalizer_scalper_issue770_posthoc_paired_sign_v1 import (
    BLOCK,
    REPS,
    comparative,
    quantile,
    run,
)


def event(i:int,both:bool=True)->dict:
    day=(date(2026,1,5)+timedelta(days=i)).isoformat()
    return {
        "source_opportunity_id":f"id-{i}",
        "symbol":"EURUSD","operating_date":day,
        "entry_at":day+"T12:00:00+00:00",
        "pure_1to1":{
            "status":"STOP" if both else "RIGHT_CENSORED_PRICE_GAP",
            "R":"-1" if both else None,"exit_at":day+"T12:10:00+00:00" if both else None,
        },
        "reverse_direction_same_time_pure":{
            "status":"TARGET" if both else "RIGHT_CENSORED_PRICE_GAP",
            "R":"1" if both else None,"exit_at":day+"T12:10:00+00:00" if both else None,
        },
    }


def test_paired_same_source_day_blocks_and_censors() -> None:
    assert REPS==2000 and BLOCK==5
    data=tuple(event(i) for i in range(7))+(event(8,False),)
    result=comparative(data,"pure_1to1","reverse_direction_same_time_pure")
    assert result["n_original_intents"]==8
    assert result["paired_resolved_count"]==7
    assert result["both_censored"]==1
    assert result["identical_censor_identity"]
    assert result["mean_opposite_minus_original_gross_R"]==2.0
    assert result["day_block_95pct_bootstrap_delta_R"]==[2.0,2.0]
    assert result["sign_reversal_trade_authority"] is False


def test_missing_paired_source_and_empty_percentiles_fail_closed(tmp_path) -> None:
    with pytest.raises(ValueError,match="artifact"):
        run(tmp_path,tmp_path)
    with pytest.raises(ValueError,match="empty"):
        quantile([],0.5)
