"""One preregistered TSMOM252 weekly / 20D ex-ante volatility experiment.

Reuses ONLY ORIGINAL source retrieval / SHA-checked UTC daily M5-derived bars
from the completed TSMOM20 source reader. DOES NOT use its strategy outcomes.
Hypothetical 1bp per notional side: not broker NET, no fills or financing.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import qore_native_d1_tsmom20_single_edge_v1 as src

IDENTITY = "QORE_NATIVE_D1_TSMOM252_VOL20_WEEKLY_SINGLE_FROZEN_PANEL_V1"
LOOKBACK = 252
VOL_DAYS = 20
TARGET_VOL_ANNUAL = 0.10
MAX_ABS_NOTIONAL = 3.0
ANNUAL_DAYS = 252
SIDE_COST = 0.0001
EMBARGO = src.EMBARGO
DIAG_START = src.VALIDATION_START
DEV_START = src.DEV_START
RESEARCH_PERIODS = ("DEV", "DIAG")
FX = frozenset((
    "AUDUSD","EURUSD","GBPUSD","NZDUSD","USDCAD","USDCHF","USDJPY",
    "AUDJPY","AUDCAD","AUDCHF","AUDNZD","CADCHF","CADJPY","CHFJPY",
    "EURAUD","EURCAD","EURCHF","EURGBP","EURJPY","EURNZD",
    "GBPAUD","GBPCAD","GBPCHF","GBPJPY","GBPNZD",
    "NZDCAD","NZDCHF","NZDJPY",
))
INDICES = frozenset(("NAS100","SP500","US30"))
METALS = frozenset(("XAUUSD","XAGUSD"))


def risk_target(completed: list[dict]) -> float:
    """Only finished sessions, no current or future prices allowed."""
    if len(completed) != LOOKBACK + 1:
        raise ValueError("TSMOM252_STRICT_LOOKBACK_253_FINISHED_DAYS_REQUIRED")
    if any(completed[i]["date"] >= completed[i+1]["date"] for i in range(LOOKBACK)):
        raise ValueError("TSMOM252_NON_MONOTONE_LOOKBACK")
    if any((completed[i+1]["date"]-completed[i]["date"]).days > src.MAX_GAP_DAYS
           for i in range(LOOKBACK)):
        return 0.0
    closes = [x["close"] for x in completed]
    if any(type(x) is not int or x <= 0 for x in closes):
        raise ValueError("TSMOM252_PRICE_CLOSE_INVALID")
    movement = closes[-1] - closes[0]
    sign = (movement > 0) - (movement < 0)
    if not sign:
        return 0.0
    # Need exactly 20 daily close-to-close returns ending at last completed
    # session; no contemporaneous rebalance-session price.
    last_returns = [
        closes[-VOL_DAYS-1+k+1] / closes[-VOL_DAYS-1+k] - 1
        for k in range(VOL_DAYS)
    ]
    vol = statistics.stdev(last_returns) * math.sqrt(ANNUAL_DAYS)
    if not math.isfinite(vol):
        raise ValueError("TSMOM252_REALIZED_VOL_NONFINITE")
    if vol <= 0.0:
        return 0.0
    return sign * min(MAX_ABS_NOTIONAL, TARGET_VOL_ANNUAL / vol)


def iso_week(d: date) -> tuple[int,int]:
    y,w,_ = d.isocalendar()
    return y,w


def family(symbol: str) -> str:
    if symbol in FX: return "FX_28"
    if symbol in INDICES: return "INDICES_3"
    if symbol in METALS: return "METALS_2"
    raise ValueError("TSMOM252_UNREGISTERED_INSTRUMENT")


def evaluate_one(symbol: str, bars: list[dict]) -> tuple[list[dict], dict[date,float]]:
    """Daily open-to-open mark; on FIRST session of ISO week change risk notional.

    At mark date t, credit previous holdings' return from open[t-1] to
    open[t] before subtracting transaction costs of new holdings at open[t].
    No outcome from day t informs the signal enacted at its own opening.
    """
    if symbol not in src.universe() or len(bars) < LOOKBACK + 40:
        raise ValueError("TSMOM252_UNIVERSE_OR_HISTORY_INSUFFICIENT")
    if [b["date"] for b in bars] != sorted(set(b["date"] for b in bars)):
        raise ValueError("TSMOM252_DUPLICATE_OR_NON_MONOTONE_DATES")
    if any(not (src.LOWER <= b["date"] < EMBARGO) for b in bars):
        raise ValueError("TSMOM252_HOLDOUT_INPUT_PROHIBITED")

    output = []
    benchmark: dict[date,float] = {}
    for i in range(1,len(bars)):
        a,b=bars[i-1],bars[i]
        if ((b["date"]-a["date"]).days <= src.MAX_GAP_DAYS
                and b["entry_open"] > 0 and a["entry_open"] > 0
                and b["date"] < EMBARGO):
            benchmark[b["date"]] = b["entry_open"]/a["entry_open"] - 1.

    for era in RESEARCH_PERIODS:
        hold = 0.0
        previous_index = None
        last_week = None
        era_rows = []
        for i, current in enumerate(bars):
            if src.period(current["date"]) != era:
                continue
            if (current["entry_ts"].date() != current["date"] or
                    current["entry_ts"].hour*60 + current["entry_ts"].minute
                    < src.FIRST_EXEC_MINUTE_UTC):
                raise ValueError("TSMOM252_EXECUTION_TIME_BEFORE_FROZEN_EARLIEST")
            daily_gain = 0.0
            if previous_index is not None:
                previous = bars[previous_index]
                if (current["date"] - previous["date"]).days > src.MAX_GAP_DAYS:
                    if abs(hold)>1e-14:
                        raise ValueError("TSMOM252_UNPRICED_HELD_GAP")
                else:
                    daily_gain = hold * (current["entry_open"]/previous["entry_open"] - 1.)
            previous_index = i
            if not math.isfinite(daily_gain) or daily_gain <= -1:
                raise ValueError("TSMOM252_INVALID_MARK_TO_MARK_GAIN")
            traded_sides = 0.
            rebalance = False
            week = iso_week(current["date"])
            # Only first eligible observation each ISO week can decide. No
            # retry using later in-week outcomes if feature insufficient.
            if week != last_week:
                last_week = week
                if i >= LOOKBACK+1:
                    previous = bars[i-1]
                    if (src.period(previous["date"]) == era
                        and (current["date"]-previous["date"]).days <= src.MAX_GAP_DAYS
                        and previous["last_ts"]+timedelta(minutes=5,seconds=src.MIN_SIGNAL_TO_ORDER_SECONDS)
                             <= current["entry_ts"]):
                        want = risk_target(bars[i-LOOKBACK-1:i])
                        traded_sides=abs(want-hold)
                        hold=want
                        rebalance=True
            fee = traded_sides*SIDE_COST
            # Keep zero position/fee days as explicit cash rows; no other
            # daily rebalance and no cost from maintaining risk.
            era_rows.append({
                "symbol":symbol, "family":family(symbol), "era":era,
                "date":current["date"], "net_assumed":daily_gain-fee,
                "gross":daily_gain, "cost":fee, "turnover_sides":traded_sides,
                "held_notional_after_open":hold, "rebalance":rebalance,
            })
        # At last open of each period flatten. Charge the final side once,
        # even when positions were held since a long-running weekly signal.
        if era_rows:
            last=era_rows[-1]
            liquidation=abs(hold)*SIDE_COST
            last["net_assumed"]-=liquidation
            last["cost"]+=liquidation
            last["turnover_sides"]+=abs(hold)
        output.extend(era_rows)
    if not output or not any(x["rebalance"] for x in output):
        raise ValueError("TSMOM252_NO_VALID_REBALANCES")
    return output,benchmark


def panel(rows: list[dict], benchmark:dict[date,float], sources:list[dict])->dict:
    registered=set(src.universe())
    if (len(registered)!=33 or FX|INDICES|METALS!=registered or
        len(FX)!=28 or len(INDICES)!=3 or len(METALS)!=2 or
        len(sources)!=33 or {s["symbol"] for s in sources}!=registered):
        raise ValueError("TSMOM252_SOURCE33_OR_FAMILY_COHORT_DRIFT")
    result={}
    for era,begin,end in (
        ("DEV",DEV_START,DIAG_START),("DIAG",DIAG_START,EMBARGO)
    ):
        reported=defaultdict(float)
        family_daily=defaultdict(lambda:defaultdict(float))
        symbol_daily=defaultdict(list)
        traded=0.
        rebalances=0
        position_days=0
        for row in rows:
            if row["era"]!=era:continue
            d=row["date"]
            if not begin<=d<end:
                raise ValueError("TSMOM252_PERIOD_OR_HOLDOUT_LEAK")
            reported[d]+=row["net_assumed"]/33.
            family_daily[row["family"]][d]+=row["net_assumed"]/33.
            symbol_daily[row["symbol"]].append(row["net_assumed"])
            position_days+=int(row["held_notional_after_open"]!=0)
            traded+=row["turnover_sides"]
            rebalances+=int(row["rebalance"])
        calendar=[]
        d=begin
        while d<end:
            if d.weekday()<5:calendar.append(d)
            d+=timedelta(days=1)
        series=[reported[d] for d in calendar]
        pairs=[(reported[d],benchmark[d]) for d in calendar if d in benchmark]
        sector={
            fam:src.performance([famret.get(d,0.) for d in calendar])
            for fam,famret in sorted(family_daily.items())
        }
        result[era]={
            **src.performance(series),
            "date_start_inclusive":begin.isoformat(),
            "date_end_exclusive":end.isoformat(),
            "market_day_held_positions":position_days,
            "rebalances":rebalances,
            "absolute_notional_sides_traded":traded,
            "SP500_CFD_non_SPX_proxy_correlation":src.correlation(
                [a for a,b in pairs],[b for a,b in pairs]),
            "SP500_CFD_matched_days":len(pairs),
            "subgroups_DESCRIPTIVE_NOT_SELECTION":sector,
            "individual_markets_DIAGNOSTIC_ONLY":{
                sym:src.performance(vals) for sym,vals in sorted(symbol_daily.items())
            },
        }
    diag=result["DIAG"]["annualized_sharpe_252_rf0"]
    verdict=("NO_POSITIVE_SUPPORT" if diag is None or diag<=0 else
             "WEAK_EXPLORATORY_ONLY" if diag<=0.5 else
             "PROMISING_EXPLORATORY_ONLY_NOT_CERTIFIED")
    return {
        "identity":IDENTITY,
        "status":"FROZEN_TSMOM252_VOL20_WEEKLY_33_AFTER_ASSUMED_COST_NOT_BROKER_NET",
        "prereg_verdict":verdict,
        "lookback_completed_trading_days":LOOKBACK,
        "vol_realized_completed_daily_close_returns":VOL_DAYS,
        "annualized_target_vol":TARGET_VOL_ANNUAL,
        "max_abs_asset_notional":MAX_ABS_NOTIONAL,
        "rebalance":"FIRST_VALID_SESSION_OF_ISO_WEEK_ONLY",
        "transaction_cost_bp_per_notional_side":SIDE_COST*10000.,
        "original_market_count":33,
        "market_families":{"FX":28,"INDICES":3,"METALS":2},
        "portfolio_ex_ante_weight_per_symbol":"1/33",
        "performance":result,
        "source_reports":sources,
        "historical_futures_excess_returns_equivalent":False,
        "original12_vs_new21_contracts_homologated":False,
        "financing_or_swap_included":False,
        "real_BIDASK_and_broker_fills_verified":False,
        "2024_09_17_onward_holdout_economics_read":False,
        "broker_NET_certified":False,
        "certified_traders":0,
        "production_untouched":True,
    }


def run(workdir:Path,output:Path)->dict[str,Any]:
    repo=os.environ.get("GITHUB_REPOSITORY","mezas3238-hue/qore-core")
    token=os.environ.get("GH_TOKEN")
    if not token:raise ValueError("SOURCE_GITHUB_ACTIONS_READ_TOKEN_MISSING")
    original=src.get_artifact_register(repo,token)
    workdir.mkdir(parents=True,exist_ok=True)
    all_rows=[]
    sources=[]
    proxy={}
    for symbol in sorted(src.universe()):
        info=original[symbol]
        archive=workdir/(symbol+".zip")
        try:
            subprocess.run([
                "curl","--fail","--silent","--show-error","--location",
                "--retry","2","-H",f"Authorization: Bearer {token}",
                "-H","Accept: application/vnd.github+json",
                f"https://api.github.com/repos/{repo}/actions/artifacts/{info['artifact_id']}/zip",
                "--output",str(archive)
            ],check=True)
            bars,witness=src.daily_from_zip(archive,symbol)
            rows,bm=evaluate_one(symbol,bars)
            witness.update({
                "source_artifact_id":info["artifact_id"],
                "source_original_run":info["original_run"],
                "weekly_rebalances":sum(int(r["rebalance"]) for r in rows),
                "asset_period_cash_rows":sum(int(r["held_notional_after_open"]==0) for r in rows),
            })
            sources.append(witness)
            all_rows.extend(rows)
            if symbol=="SP500":proxy=bm
            print("TSMOM252_VOL20_ORIGINAL_SOURCE_PASS",symbol,
                  witness["valid_daily_sessions"],len(rows),flush=True)
        finally:
            archive.unlink(missing_ok=True)
    if not proxy:raise ValueError("SP500_CFD_BENCHMARK_MISSING")
    report=panel(all_rows,proxy,sources)
    output.mkdir(parents=True,exist_ok=True)
    path=output/"TSMOM252_VOL20_WEEKLY_33_COST1BP_SIDE_NOT_BROKER_NET.json"
    path.write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n")
    (output/"SHA256SUMS.txt").write_text(src.sha256_bytes(path.read_bytes())+"  "+path.name+"\n")
    print("TSMOM252_VOL20_WEEKLY_SINGLE_FROZEN_RESULTS",
        json.dumps({"verdict":report["prereg_verdict"],
            "DEV":{k:report["performance"]["DEV"][k] for k in (
                "annualized_sharpe_252_rf0","annualized_return_252","max_drawdown",
                "SP500_CFD_non_SPX_proxy_correlation","rebalances")},
            "DIAG":{k:report["performance"]["DIAG"][k] for k in (
                "annualized_sharpe_252_rf0","annualized_return_252","max_drawdown",
                "SP500_CFD_non_SPX_proxy_correlation","rebalances")},
            "broker_NET":False,"certified":0},sort_keys=True),flush=True)
    return report


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("workdir",type=Path)
    p.add_argument("outputdir",type=Path)
    args=p.parse_args()
    run(args.workdir,args.outputdir)


if __name__=="__main__":main()
