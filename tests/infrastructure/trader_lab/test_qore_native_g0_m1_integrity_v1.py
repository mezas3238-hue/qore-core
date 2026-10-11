"""QORE Native G0: source-only integrity & paired M1 clock, no financial outcomes."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.qore_native_g0_m1_integrity_v1 import (
    WINDOW_START, audit_stream, interval_bin,
)


def b(t:datetime,sym:str="EURUSD")->CapitalizerM1Bar:
    return CapitalizerM1Bar(
        symbol=sym,opened_at=t,closed_at=t+timedelta(minutes=1),
        open=Decimal("1.1"),high=Decimal("1.1002"),
        low=Decimal("1.0998"),close=Decimal("1.1001"),
        volume=22,digits=5,
    )


def test_prereg_start_and_no_price_outcomes() -> None:
    t=WINDOW_START
    sample=[b(t),b(t+timedelta(minutes=1)),b(t+timedelta(minutes=3))]
    result,clock=audit_stream(sample,"EURUSD")
    assert result["integrity_gate"]=="SOURCE_INTEGRITY_PASS"
    assert result["source_native_m1_rows_in_year"]==3
    assert result["coverage"]=="COVERAGE_PARTIAL"
    assert result["m15_complete_15of15"]==0
    assert result["m15_incomplete_1to14"]==1
    assert result["h1_incomplete_1to59"]==1
    assert result["intra_UTC_day_gap_count_by_duration"]["2-4m"]==1
    assert not result["trading_strategy_edge_evaluated"]
    assert not result["unseen_holdout"]
    assert not result["physical_trade_replay_authorized"]
    d=t.date().isoformat()
    assert int(clock["days"][d],16).bit_count()==3


def test_complete_15_m1_and_h1_are_not_artificially_truncated() -> None:
    x=[b(WINDOW_START+timedelta(minutes=i)) for i in range(60)]
    r,_=audit_stream(x,"EURUSD")
    assert r["m15_complete_15of15"]==4
    assert r["m15_incomplete_1to14"]==0
    assert r["h1_complete_60of60"]==1
    assert r["h1_incomplete_1to59"]==0
    assert r["coverage"]=="ACTIVE_BUCKETS_COMPLETE"


def test_duplicate_timestamp_and_unsorted_refused() -> None:
    with pytest.raises(ValueError,match="duplicate"):
        audit_stream([b(WINDOW_START),b(WINDOW_START)],"EURUSD")
    with pytest.raises(ValueError,match="nonmonotone"):
        audit_stream([b(WINDOW_START+timedelta(minutes=1)),b(WINDOW_START)],"EURUSD")


def test_source_wrong_symbol_and_unsupported_market_fail_closed() -> None:
    with pytest.raises(ValueError,match="wrong symbol"):
        audit_stream([b(WINDOW_START,"GBPUSD")],"EURUSD")
    with pytest.raises(ValueError,match="scope"):
        audit_stream([b(WINDOW_START)],"BTCUSD")


def test_gaps_intra_day_not_conflated_with_weekends() -> None:
    t=WINDOW_START
    r,_=audit_stream([b(t),b(t+timedelta(minutes=30)),b(t+timedelta(days=3))],"EURUSD")
    assert r["intra_UTC_day_gap_count_by_duration"]["15-59m"]==1
    assert r["maximum_intra_day_missing_minutes"]==29


def test_reader_rejects_impossible_OHLC():
    with pytest.raises(ValueError,match="high"):
        CapitalizerM1Bar(
            symbol="EURUSD",opened_at=WINDOW_START,closed_at=WINDOW_START+timedelta(minutes=1),
            open=Decimal("1.10"),high=Decimal("1.09"),
            low=Decimal("1.08"),close=Decimal("1.10"),volume=1,digits=5
        )


def test_gap_categories_fixed():
    assert interval_bin(2)=="2-4m"
    assert interval_bin(5)=="5-14m"
    assert interval_bin(15)=="15-59m"
    assert interval_bin(60)==">=60m"
    with pytest.raises(ValueError):
        interval_bin(1)
