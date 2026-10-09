#!/usr/bin/env python3
"""P0 closed-trade path forensics, GH Trader Lab PAPER ONLY.

Requires a canonical single-ledger export, not legacy replay rows. Historical
fixed-spread M5 is an OHLC scenario, not broker-native bid/ask or observed fills.
All extrema on the terminal stop bar are BOUNDS, not exact pre-stop path.
Post-SL target observations are hindsight diagnostics ONLY and must never feed
CIBO's decision for that historical trade.
"""
from __future__ import annotations

import argparse
import json
import hashlib
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal as D, InvalidOperation
from pathlib import Path

AUTHORITY = "SINGLE_QDLE_RESEARCH_PAPER_V1"
SOURCE = "ATLAS_M5_FIXED_SPREAD_RESEARCH_UNVERIFIED"
STOP_REASONS = {"STOP_FIRST_OR_SL_ONLY", "GAP_OPEN_STOP",
                "OPEN_GAP_AFTER_STOP_UPDATE"}
TARGET_REASONS = {"TAKE_PROFIT", "GAP_OPEN_TARGET"}
OPEN_EXIT_REASONS = {"GAP_OPEN_STOP", "OPEN_GAP_AFTER_STOP_UPDATE",
                     "GAP_OPEN_TARGET", "DEFENSIVE_CLOSE_NEXT_OPEN"}
WINDOW_MINUTES = (60, 240, 1440)
REQUIRED = ("opened_at", "closed_at", "bid_open", "bid_high",
            "bid_low", "bid_close", "ask_open", "ask_high",
            "ask_low", "ask_close", "evidence_sha256")


def _decimal(v, field):
    try:
        x = D(str(v))
    except (TypeError, ValueError, InvalidOperation) as exc:
        raise ValueError(field + ": decimal required") from exc
    if not x.is_finite():
        raise ValueError(field + ": nonfinite")
    return x


def _date(v):
    if not isinstance(v, str):
        raise ValueError("aware ISO date required")
    try:
        t = datetime.fromisoformat(v)
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if t.utcoffset() is None:
        raise ValueError("timezone-aware timestamp required")
    return t


def _digest(value):
    return (isinstance(value,str) and value.startswith("sha256:")
            and len(value)==71
            and all(c in "0123456789abcdef" for c in value[7:]))


def _bar(raw):
    if not isinstance(raw, dict) or not all(x in raw for x in REQUIRED):
        raise ValueError("missing full executable-side OHLC bar")
    if not _digest(raw["evidence_sha256"]):
        raise ValueError("missing bar evidence SHA")
    opened,closed=_date(raw["opened_at"]),_date(raw["closed_at"])
    if closed<=opened:
        raise ValueError("invalid bar chronology")
    row={"opened_at":opened, "closed_at":closed}
    for key in REQUIRED[2:-1]:
        row[key]=_decimal(raw[key],key)
        if row[key]<=0: raise ValueError("nonpositive OHLC")
    for prefix in ("bid","ask"):
        o,h,l,c=(row[prefix+"_"+suffix] for suffix in
                 ("open","high","low","close"))
        if not l<=min(o,c)<=max(o,c)<=h:
            raise ValueError("invalid OHLC price range")
    for suffix in ("open","high","low","close"):
        if row["bid_"+suffix]>row["ask_"+suffix]:
            raise ValueError("negative executable spread")
    return row


def _stats(values):
    if not values: return None
    arr=sorted(values)
    def percentile(p):
        index=D(len(arr)-1)*D(p)/D(100)
        lo=int(index)
        weight=index-D(lo)
        return arr[lo]*(D(1)-weight)+arr[min(lo+1,len(arr)-1)]*weight
    return {"n":len(arr),"mean":str(sum(arr,D(0))/D(len(arr))),
            "p25":str(percentile(25)),"p50":str(percentile(50)),
            "p75":str(percentile(75)),"p90":str(percentile(90))}


def _favorable(side, entry, price, unit):
    return D(unit)*(price-entry) if side=="BUY" else D(unit)*(entry-price)


def _extremes(b,side):
    return (b["bid_high"],b["bid_low"]) if side=="BUY" else (
        b["ask_low"],b["ask_high"])


def _target_hit(bar,side,target):
    return bar["bid_high"]>=target if side=="BUY" else bar["ask_low"]<=target


def _window_after_stop(bars,terminal,exit_at,side,target,minutes):
    """A YES is independently observed after the terminal stop bar.

    NO requires continuous bars spanning the WHOLE requested window.
    A same-bar stop+TP does not establish which happened first.
    """
    deadline=exit_at+timedelta(minutes=minutes)
    last=bars[terminal]["closed_at"]
    full_coverage=(last==exit_at)
    for bar in bars[terminal+1:]:
        if bar["opened_at"]!=last:
            return "UNKNOWN_COVERAGE"
        last=bar["closed_at"]
        if bar["closed_at"]>deadline:
            return "NO" if full_coverage and bar["opened_at"]>=deadline else "UNKNOWN_COVERAGE"
        if _target_hit(bar,side,target):
            return "YES_POST_STOP"
        if last>=deadline:
            return "NO" if full_coverage else "UNKNOWN_COVERAGE"
    return "UNKNOWN_COVERAGE"


def analyze_closed_trade(row):
    if not isinstance(row,dict):
        raise ValueError("closed trade row required")
    sid=row.get("signal_fingerprint")
    if not isinstance(sid,str) or not sid:
        raise ValueError("signal fingerprint required")
    side=row["side"]
    if side not in ("BUY","SELL"):
        raise ValueError("BUY/SELL required")
    entry,stop,target=(_decimal(row[k],k) for k in (
        "entry_price","initial_stop_price","take_profit_price"))
    direction=D(1) if side=="BUY" else D(-1)
    risk_dist=direction*(entry-stop)
    if risk_dist<=0 or direction*(target-entry)<=0:
        raise ValueError("incorrect SL/TP geometry")
    fill_at,exit_at=_date(row["entry_at"]),_date(row["exit_at"])
    if exit_at<fill_at:
        raise ValueError("exit before entry")
    reason=row["exit_reason"]
    net=_decimal(row["net_pnl_usd"],"net PnL")
    raw_bars=row.get("bars")
    if not isinstance(raw_bars,list) or not raw_bars:
        raise ValueError("terminal price path required; UNKNOWN is not a closed trade")
    bars=[_bar(x) for x in raw_bars]
    if bars[0]["opened_at"]!=fill_at:
        raise ValueError("first bar must coincide with PAPER fill")
    # Bars through settlement must be chronologically contiguous. Historical
    # gaps AFTER exit are permissible but make post-SL windows UNKNOWN.
    is_open_exit=reason in OPEN_EXIT_REASONS
    candidates=[i for i,b in enumerate(bars)
                if (b["opened_at"]==exit_at if is_open_exit
                    else b["closed_at"]==exit_at)]
    if len(candidates)!=1:
        raise ValueError("missing unambiguous terminal fill bar")
    terminal=candidates[0]
    for prev,nxt in zip(bars[:terminal],bars[1:terminal+1]):
        if prev["closed_at"]!=nxt["opened_at"]:
            raise ValueError("pre-exit price path gap")
    favorable_pre=[D(0)]
    adverse_pre=[D(0)]
    for b in bars[:terminal]:
        good,bad=_extremes(b,side)
        favorable_pre.append(max(D(0),_favorable(side,entry,good,1)/risk_dist))
        adverse_pre.append(max(D(0),-_favorable(side,entry,bad,1)/risk_dist))
    last=bars[terminal]
    executable_open=last["bid_open"] if side=="BUY" else last["ask_open"]
    favorable_pre.append(max(D(0),_favorable(side,entry,executable_open,1)/risk_dist))
    adverse_pre.append(max(D(0),-_favorable(side,entry,executable_open,1)/risk_dist))
    mfe_lower=max(favorable_pre)
    mae_lower=max(adverse_pre)
    good,bad=_extremes(last,side)
    mfe_upper=max(mfe_lower,max(D(0),_favorable(side,entry,good,1)/risk_dist))
    mae_upper=max(mae_lower,max(D(0),-_favorable(side,entry,bad,1)/risk_dist))
    if reason in STOP_REASONS:
        mae_lower=max(mae_lower,D(1) if reason=="STOP_FIRST_OR_SL_ONLY" else mae_lower)
        mae_upper=max(mae_upper,mae_lower)
    if reason in TARGET_REASONS:
        mfe_lower=max(mfe_lower,_favorable(side,entry,target,1)/risk_dist)
        mfe_upper=max(mfe_upper,mfe_lower)
    samebar=bool(reason in STOP_REASONS and _target_hit(last,side,target))
    windows={str(n)+"m":_window_after_stop(
        bars,terminal,exit_at,side,target,n) if reason in STOP_REASONS else
        "NOT_STOP_EXIT" for n in WINDOW_MINUTES}
    return {
        "signal_fingerprint":sid,
        "symbol":row["symbol"],"trader_id":row["trader_id"],
        "mode":row["mode"],"side":side,
        "entry_hour_utc":str(fill_at.astimezone(
            __import__("datetime").timezone.utc).hour).zfill(2),
        "result":("WIN" if net>0 else "LOSS" if net<0 else "BREAKEVEN"),
        "net_pnl_usd":str(net),"exit_reason":reason,
        "duration_minutes":str(D((exit_at-fill_at).total_seconds())/D(60)),
        "mfe_r_lower_bound":str(mfe_lower),"mfe_r_upper_bound":str(mfe_upper),
        "mae_r_lower_bound":str(mae_lower),"mae_r_upper_bound":str(mae_upper),
        "terminal_bar_includes_unknown_intrabar_order":not is_open_exit,
        "stop_and_tp_same_bar_order_unknown":samebar,
        "post_stop_target_windows":windows,
        "bars_before_and_including_exit":terminal+1,
        "bid_ask_source":SOURCE,
    }


def report_forensics(payload, *, expected_closed=None):
    if not isinstance(payload,dict) or payload.get("ledger_authority")!=AUTHORITY:
        raise ValueError("single canonical PAPER ledger authority required")
    if payload.get("price_source")!=SOURCE:
        raise ValueError("historical broker/native prices cannot be inferred from M5 proxy")
    if not all(_digest(payload.get(k)) for k in (
        "input_sha256","ledger_sha256","code_sha256","market_data_sha256")):
        raise ValueError("immutable experiment source, ledger and code digests required")
    trades=payload.get("closed_trade_paths")
    if not isinstance(trades,list):
        raise ValueError("closed_trade_paths list required")
    if expected_closed is not None and len(trades)!=expected_closed:
        raise ValueError("expected closed trade count mismatch")
    rows=[analyze_closed_trade(trade) for trade in trades]
    ids=[r["signal_fingerprint"] for r in rows]
    if len(set(ids))!=len(ids):
        raise ValueError("duplicate trade fingerprint")
    nets=[D(r["net_pnl_usd"]) for r in rows]
    positives=[n for n in nets if n>0]
    negatives=[-n for n in nets if n<0]
    wins=len(positives)
    losses=len(negatives)
    sample=len(rows)
    avg_win=sum(positives,D(0))/wins if wins else None
    avg_loss=sum(negatives,D(0))/losses if losses else None
    pf=sum(positives,D(0))/sum(negatives,D(0)) if negatives else None
    required_rate=avg_loss/(avg_loss+avg_win) if avg_win is not None and avg_loss is not None else None
    by_result={}
    for category in ("WIN","LOSS","BREAKEVEN"):
        subset=[r for r in rows if r["result"]==category]
        by_result[category]={
            "count":len(subset),
            **{key:_stats([D(r[key]) for r in subset]) for key in (
                "duration_minutes","mfe_r_lower_bound","mfe_r_upper_bound",
                "mae_r_lower_bound","mae_r_upper_bound")},
        }
    stops=[r for r in rows if r["exit_reason"] in STOP_REASONS]
    posterior={label:dict(sorted({
        state:sum(r["post_stop_target_windows"][label]==state for r in stops)
        for state in ("YES_POST_STOP","NO","UNKNOWN_COVERAGE")}.items()))
        for label in (str(n)+"m" for n in WINDOW_MINUTES)}
    cohorts={}
    for field in ("symbol","trader_id","mode","exit_reason","entry_hour_utc"):
        groups=defaultdict(list)
        for receipt in rows:
            groups[receipt[field]].append(receipt)
        cohorts[field]={
            group: {
                "n":len(members),
                "win_rate_pct":str(D(100)*D(sum(m["result"]=="WIN" for m in members))/D(len(members))),
                "net_total_usd":str(sum((D(m["net_pnl_usd"]) for m in members),D(0))),
                "duration_minutes":_stats([D(m["duration_minutes"]) for m in members]),
                "mfe_r_lower_bound":_stats([D(m["mfe_r_lower_bound"]) for m in members]),
                "mfe_r_upper_bound":_stats([D(m["mfe_r_upper_bound"]) for m in members]),
                "mae_r_lower_bound":_stats([D(m["mae_r_lower_bound"]) for m in members]),
                "mae_r_upper_bound":_stats([D(m["mae_r_upper_bound"]) for m in members]),
            }
            for group,members in sorted(groups.items())
        }
    return {
        "schema":"qore.cibo.p0.closed-trade-forensics.v1",
        "status":"RESEARCH_M5_OHLC_BOUNDED_NOT_BROKER_CERTIFIED",
        "authority":AUTHORITY,"ledger_sha256":payload["ledger_sha256"],
        "input_sha256":payload["input_sha256"],"code_sha256":payload["code_sha256"],
        "price_source":SOURCE,"closed_count":sample,
        "wins":wins,"losses":losses,"breakeven":sample-wins-losses,
        "win_rate_pct":str(D(100)*D(wins)/D(sample)) if sample else None,
        "profit_factor_net":str(pf) if pf is not None else None,
        "mean_win_usd":str(avg_win) if avg_win is not None else None,
        "mean_loss_usd":str(avg_loss) if avg_loss is not None else None,
        "required_win_rate_pct_for_zero_expectancy":str(D(100)*required_rate)
            if required_rate is not None else None,
        "net_expectancy_usd":str(sum(nets,D(0))/sample) if sample else None,
        "stop_exits":len(stops),
        "ambiguous_stop_and_tp_same_bar":sum(r["stop_and_tp_same_bar_order_unknown"] for r in stops),
        "post_stop_target_counts":posterior,
        "by_result":by_result,
        "by_symbol":cohorts["symbol"],
        "by_trader":cohorts["trader_id"],
        "by_mode":cohorts["mode"],
        "by_exit_reason":cohorts["exit_reason"],
        "by_entry_utc_hour":cohorts["entry_hour_utc"],
        "closed_trades":rows,
        "certifies_historical_broker_pnl":False,
        "certifies_cibo_native_max":False,
        "limitations":[
            "Terminal OHLC contains unobservable intrabar ordering; MFE/MAE are ranges",
            "Subsequent TP after SL is post-outcome hindsight for diagnosis, never a pretrade feature",
            "Fixed 2026 spread on historic M5 is a scenario, not actual FundedNext quotes",
        ],
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--expected-closed",type=int)
    args=p.parse_args()
    result=report_forensics(json.loads(args.input.read_text()),
                             expected_closed=args.expected_closed)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("CIBO_P0_CLOSED_TRADE_FORENSICS",json.dumps(
        {"status":result["status"],"closed_count":result["closed_count"],
         "win_rate_pct":result["win_rate_pct"],
         "profit_factor_net":result["profit_factor_net"],
         "stop_exits":result["stop_exits"]},sort_keys=True))


if __name__=="__main__":
    main()
