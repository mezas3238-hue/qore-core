"""Trader Lab: exact causal distinctions for bounded MFE/MAE and post-SL TP.

Synthetic OHLC fixtures test measurement logic, never signal quality.
"""
from datetime import datetime, timedelta, timezone
import pytest

from scripts.cibo_p0_closed_trade_path_forensics import (
    AUTHORITY, SOURCE, analyze_closed_trade, report_forensics,
)

T = datetime(2020,1,1,tzinfo=timezone.utc)
SHA = "sha256:"+"a"*64


def bar(i, high="101", low="99", close="100", opening="100"):
    a=T+timedelta(minutes=5*i)
    b=a+timedelta(minutes=5)
    bid={"open":opening,"high":high,"low":low,"close":close}
    from decimal import Decimal as D
    ask={k:str(D(v)+D(".1")) for k,v in bid.items()}
    return {"opened_at":a.isoformat(),"closed_at":b.isoformat(),
            **{"bid_"+k:v for k,v in bid.items()},
            **{"ask_"+k:v for k,v in ask.items()},
            "evidence_sha256":SHA}


def trade(sid="a", *, reason="STOP_FIRST_OR_SL_ONLY", net="-1",
          exit_idx=0, bars=None, side="BUY"):
    if bars is None:
        bars=[bar(0,high="101",low="99",close="99.5")]
    t=T+timedelta(minutes=5*(exit_idx+1))
    entry="100" if side=="BUY" else "100"
    return {"signal_fingerprint":sid,"symbol":"EURUSD","trader_id":"A1",
            "mode":"ATTACK","side":side,
            "entry_price":entry,
            "initial_stop_price":"99" if side=="BUY" else "101",
            "take_profit_price":"102" if side=="BUY" else "98",
            "entry_at":T.isoformat(),"exit_at":t.isoformat(),
            "exit_reason":reason,"net_pnl_usd":net,"bars":bars}


def envelope(rows):
    return {"ledger_authority":AUTHORITY,"price_source":SOURCE,
            "ledger_sha256":SHA,"input_sha256":SHA,
            "code_sha256":SHA,"market_data_sha256":SHA,
            "closed_trade_paths":rows}


def test_stop_then_later_tp_is_observable_but_not_saved_profit():
    rows=[bar(0,high="101",low="99",close="99.5"),
          bar(1,high="102.5",low="99.4",close="101")]
    result=analyze_closed_trade(trade(bars=rows))
    assert result["mfe_r_lower_bound"]=="0"
    assert result["mfe_r_upper_bound"]=="1"
    assert result["mae_r_lower_bound"]=="1"
    assert result["post_stop_target_windows"]=={
        "60m":"YES_POST_STOP","240m":"YES_POST_STOP",
        "1440m":"YES_POST_STOP"}
    assert result["result"]=="LOSS"


def test_same_bar_stop_and_target_cannot_establish_order():
    result=analyze_closed_trade(trade(
        bars=[bar(0,high="102.5",low="99",close="100")]))
    assert result["stop_and_tp_same_bar_order_unknown"]
    assert result["post_stop_target_windows"]["60m"]=="UNKNOWN_COVERAGE"
    assert result["mfe_r_lower_bound"]=="0"
    assert result["mfe_r_upper_bound"]=="2.5"


def test_completed_1hour_window_proves_no_later_target():
    rows=[bar(i,high="101",low="99.5") for i in range(13)]
    rows[0]=bar(0,high="101",low="99",close="99.5")
    r=analyze_closed_trade(trade(bars=rows))
    assert r["post_stop_target_windows"]["60m"]=="NO"
    assert r["post_stop_target_windows"]["240m"]=="UNKNOWN_COVERAGE"


def test_gap_after_stop_prevents_false_no_later_tp():
    second=bar(3,high="101.3",low="99.5")
    r=analyze_closed_trade(trade(bars=[bar(0,low="99"),second]))
    assert r["post_stop_target_windows"]["60m"]=="UNKNOWN_COVERAGE"


def test_pre_exit_mfe_bound_uses_prior_bar_known():
    bars=[bar(0,high="101.5",low="99.5"),
          bar(1,high="102.5",low="98.5")]
    r=analyze_closed_trade(trade(exit_idx=1,bars=bars))
    assert r["mfe_r_lower_bound"]=="1.5"
    assert r["mfe_r_upper_bound"]=="2.5"
    assert r["mae_r_upper_bound"]=="1.5"


def test_report_pf_uses_net_wins_and_losses_only():
    loss=trade("loss",net="-1")
    gain=trade("gain",reason="TAKE_PROFIT",net="2",bars=[
        bar(0,high="102",low="99.5",close="101")])
    r=report_forensics(envelope([loss,gain]),expected_closed=2)
    assert r["closed_count"]==2
    assert r["wins"]==1
    assert r["losses"]==1
    assert r["win_rate_pct"]=="50"
    assert r["profit_factor_net"]=="2"
    assert r["stop_exits"]==1
    assert r["by_result"]["WIN"]["count"]==1
    assert r["by_result"]["LOSS"]["count"]==1


def test_refuse_legacy_replay_or_incompatible_ledgers():
    old=envelope([trade()])
    old["ledger_authority"]="PAPERQDLE_FROM_OTHER_BRANCH"
    with pytest.raises(ValueError,match="single canonical"):
        report_forensics(old)
    old["ledger_authority"]=AUTHORITY
    old["price_source"]="VERIFIED_MT5_TICKS"
    with pytest.raises(ValueError,match="historical broker"):
        report_forensics(old)


def test_refuse_duplicate_trade_and_wrong_count():
    dup=envelope([trade("x"),trade("x")])
    with pytest.raises(ValueError,match="duplicate"):
        report_forensics(dup)
    with pytest.raises(ValueError,match="count mismatch"):
        report_forensics(envelope([trade()]),expected_closed=537)


def test_refuse_future_or_missing_bars_for_a_fake_closed_trade():
    row=trade()
    row["exit_at"]=(T+timedelta(minutes=15)).isoformat()
    with pytest.raises(ValueError,match="terminal"):
        analyze_closed_trade(row)
    another=trade()
    another["bars"][0]["evidence_sha256"]="UNTRUSTED"
    with pytest.raises(ValueError,match="evidence"):
        analyze_closed_trade(another)
