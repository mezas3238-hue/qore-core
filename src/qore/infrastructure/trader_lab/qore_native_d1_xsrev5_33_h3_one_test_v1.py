"""H3: frozen cross-sectional 5-session reversal on 33 native G0 series.

Research-only: independent one-shot economic hypothesis; 1bp/side assumed
turnover, original raw SHA verified, no 2024-09-17+ return, no broker NET.
Uses H1's source-only daily ingestion, never H1/H2 economics or positions.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from qore.infrastructure.trader_lab import qore_native_d1_tsmom20_single_edge_v1 as source

IDENTITY = "QORE_NATIVE_D1_XSREV5_FIXED33_H3_PREREG_V1"
FORMATION = 5
HOLD = 5
LEG_COUNT = 6
GROSS_EXPOSURE = 1.0
WEIGHT = 1.0 / (2 * LEG_COUNT)
SIDE_COST = 0.0001
EMBARGO = source.EMBARGO
FAMILIES = {
    "FX_28": frozenset((
        "AUDUSD", "EURUSD", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY",
        "AUDJPY", "AUDCAD", "AUDCHF", "AUDNZD", "CADCHF", "CADJPY", "CHFJPY",
        "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD",
        "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD",
        "NZDCAD", "NZDCHF", "NZDJPY",
    )),
    "INDICES_3": frozenset(("NAS100", "SP500", "US30")),
    "METALS_2": frozenset(("XAUUSD", "XAGUSD")),
}
FAMILY_BY_SYMBOL = {s: fam for fam, ss in FAMILIES.items() for s in ss}


def freeze_universe() -> tuple[str, ...]:
    symbols = source.universe()
    if (len(symbols) != 33 or len(set(symbols)) != 33 or
        set(symbols) != set(FAMILY_BY_SYMBOL) or
        sorted(map(len, FAMILIES.values())) != [2, 3, 28]):
        raise ValueError("RESEARCH_H3_FROZEN_33_FAMILY_DRIFT")
    return symbols


def make_common_calendar(dailies: dict[str, list[dict]]) -> tuple[list[date], dict, dict]:
    symbols = freeze_universe()
    if set(dailies) != set(symbols):
        raise ValueError("H3_MISSING_SOURCE_MARKET_OR_EXTRA")
    maps = {}
    unions = set()
    intersections = None
    for symbol in symbols:
        bars = dailies[symbol]
        mapped = {x["date"]: x for x in bars}
        if len(mapped) != len(bars) or not bars:
            raise ValueError("H3_DUPLICATE_OR_EMPTY_DAILY_SOURCE_" + symbol)
        for d, b in mapped.items():
            if not source.LOWER <= d < EMBARGO:
                raise ValueError("H3_HOLDOUT_DAILY_SOURCE_BLOCKED")
            if (b["entry_ts"].date() != d or
                b["entry_ts"].hour * 60 + b["entry_ts"].minute
                < source.FIRST_EXEC_MINUTE_UTC or
                not all(type(b[k]) is int and b[k] > 0
                        for k in ("entry_open", "close"))):
                raise ValueError("H3_INVALID_UTC_EXECUTION_OR_PRICE")
        maps[symbol] = mapped
        keys = set(mapped)
        unions |= keys
        intersections = keys if intersections is None else intersections & keys
    common = sorted(intersections or ())
    if len(common) < 500:
        raise ValueError("H3_COMMON_DAYS_NOT_ENOUGH_33_MARKETS")
    for a, b in zip(common, common[1:]):
        if (b - a).days > source.MAX_GAP_DAYS:
            raise ValueError("H3_GAP_OVER_SEVEN_CALENDAR_DAYS")
    stats = {
        "common_dates_33_assets": len(common),
        "union_source_dates": len(unions),
        "union_dates_excluded_in_complete_case": len(unions) - len(common),
        "first_common_utc": common[0].isoformat(),
        "last_common_utc": common[-1].isoformat(),
        "no_cross_market_day_imputation": True,
    }
    return common, maps, stats


def basket(common: list[date], maps: dict[str,dict], i: int) -> dict[str,float]:
    """Use exclusively close[i-1] and close[i-6] for 5 complete sessions."""
    symbols = freeze_universe()
    if i < FORMATION + 1 or i >= len(common):
        raise ValueError("H3_INSUFFICIENT_FINISHED_FORMATION_DAYS")
    current = common[i]
    previous = common[i-1]
    if (current-previous).days > source.MAX_GAP_DAYS:
        raise ValueError("H3_DAY_GAP_BEFORE_EXECUTION")
    ranks = []
    for symbol in symbols:
        last = maps[symbol][previous]
        old = maps[symbol][common[i-1-FORMATION]]
        now = maps[symbol][current]
        if (last["last_ts"] + timedelta(
                minutes=5, seconds=source.MIN_SIGNAL_TO_ORDER_SECONDS)
                > now["entry_ts"]):
            raise ValueError("H3_FORMATION_LAST_BAR_NOT_CAUSALLY_COMPLETE")
        if not old["close"] or not last["close"]:
            raise ValueError("H3_INVALID_FORMATION_CLOSE")
        ranks.append((last["close"] / old["close"] - 1., symbol))
    ranks.sort(key=lambda r: (r[0],r[1]))
    if len(ranks) != 33 or any(not math.isfinite(x) for x,s in ranks):
        raise ValueError("H3_NONFINITE_OR_INCOMPLETE_CROSS_SECTION")
    long_set = {symbol for _,symbol in ranks[:LEG_COUNT]}
    short_set = {symbol for _,symbol in ranks[-LEG_COUNT:]}
    if long_set & short_set or len(long_set)!=LEG_COUNT or len(short_set)!=LEG_COUNT:
        raise ValueError("H3_BASKET_IS_NOT_6_AND_6")
    positions = {s: 0.0 for s in symbols}
    for s in long_set:positions[s] = WEIGHT
    for s in short_set:positions[s] = -WEIGHT
    if (abs(sum(positions.values())) > 1e-12 or
        abs(sum(abs(p) for p in positions.values()) - GROSS_EXPOSURE) > 1e-12):
        raise ValueError("H3_PORTFOLIO_NOT_50_50_GROSS1")
    return positions


def evaluate(dailies: dict[str,list[dict]]) -> dict:
    common,maps,calendar_stats = make_common_calendar(dailies)
    symbols=freeze_universe()
    outcome={}
    all_events={}
    sp500={}
    for era,begin,end in (
        ("DEV", source.DEV_START, source.VALIDATION_START),
        ("DIAG", source.VALIDATION_START, EMBARGO),
    ):
        # only pre-registered complete-case common calendar; positions are
        # reset across eras, but historical signal may use prior DEV closings.
        dates=[d for d in common if begin<=d<end]
        if len(dates)<150:
            raise ValueError("H3_PERIOD_COMMON_SESSION_SAMPLE_TOO_SHORT_"+era)
        positions={s:0.0 for s in symbols}
        old_date = None
        realized={}
        by_family:dict[str,dict[date,float]]={
            f:defaultdict(float) for f in FAMILIES
        }
        by_symbol={s:0.0 for s in symbols}
        sides=0.
        rebalance_events=0
        entry_tickets=0
        long_counts=Counter()
        short_counts=Counter()
        cash_sessions=0
        total_gross_before_cost=0.
        total_cost=0.
        for step, d in enumerate(dates):
            i=common.index(d)  # at most 2k dates; deterministic; no lookahead
            gross=0.
            family_piece={f:0. for f in FAMILIES}
            symbol_piece={s:0. for s in symbols}
            if old_date is not None:
                if (d-old_date).days>source.MAX_GAP_DAYS:
                    raise ValueError("H3_MARKED_RETURN_MISSING_BETWEEN_COMMON_SESSIONS")
                for symbol in symbols:
                    a=maps[symbol][old_date]["entry_open"]
                    b=maps[symbol][d]["entry_open"]
                    market_move=b/a-1.
                    if not math.isfinite(market_move) or abs(market_move)>0.45:
                        raise ValueError("H3_NONFINITE_OR_IMPLAUSIBLE_DAILY_RETURN")
                    contribution=positions[symbol]*market_move
                    gross+=contribution
                    family_piece[FAMILY_BY_SYMBOL[symbol]]+=contribution
                    symbol_piece[symbol]+=contribution
                sa=maps["SP500"][old_date]["entry_open"]
                sb=maps["SP500"][d]["entry_open"]
                sp500[d]=sb/sa-1.
            old_date=d
            turnover=0.
            if step % HOLD==0 and i>=FORMATION+1:
                target=basket(common,maps,i)
                turnover=sum(abs(target[s]-positions[s]) for s in symbols)
                entry_tickets+=sum(positions[s]!=target[s] for s in symbols)
                positions=target
                rebalance_events+=1
                for s,p in positions.items():
                    if p>0: long_counts[s]+=1
                    if p<0: short_counts[s]+=1
            else:
                if step % HOLD == 0:
                    cash_sessions+=1
            # On last recorded open, include separate liquidation side cost,
            # leaving total market-to-market already attributed to this date.
            if step==len(dates)-1:
                turnover+=sum(abs(positions[s]) for s in symbols)
                entry_tickets+=sum(p!=0 for p in positions.values())
                positions={s:0.0 for s in symbols}
            daily_cost=SIDE_COST*turnover
            if turnover:
                # Transaction cost attributed to instruments that moved:
                # split actual changes by symbol, including liquidation, via
                # aggregate reporting only (portfolio fees stay exact).
                pass
            net=gross-daily_cost
            if not math.isfinite(net) or net <= -1.:
                raise ValueError("H3_NONFINITE_OR_BANKRUPT_PROFIT")
            realized[d]=net
            total_gross_before_cost+=gross
            total_cost+=daily_cost
            sides+=turnover
            for f in FAMILIES:by_family[f][d]+=family_piece[f]
            for s in symbols:by_symbol[s]+=symbol_piece[s]
        # weekday-inclusive cash days, even when missing from the intersection
        calendar=[]
        k=begin
        while k<end:
            if k.weekday()<5:calendar.append(k)
            k+=timedelta(days=1)
        vector=[realized.get(d,0.) for d in calendar]
        # Only actual common matched session marks contribute benchmark pairs.
        matches=[(realized[d],sp500[d]) for d in calendar if d in realized and d in sp500]
        metrics=source.performance(vector)
        outcome[era]={
            **metrics,
            "common_mark_days":len(dates),
            "common_dates_skipped_weekday_cash":len(calendar)-len(dates),
            "portfolio_rebalance_events":rebalance_events,
            "individual_symbol_change_orders_and_final_liquidations":entry_tickets,
            "gross_notional_turnover_sides":sides,
            "assumed_cost_total_capital_fraction_uncompounded":total_cost,
            "assumed_cost_total_bp_of_capital_uncompounded":total_cost*10000.,
            "total_daily_gross_return_sum_uncompounded":total_gross_before_cost,
            "correlation_SP500_CFD_PROXY_NOT_SPX":source.correlation(
                [p[0] for p in matches],[p[1] for p in matches]),
            "SP500_CFD_matching_dates":len(matches),
            "family_pnl_BEFORE_TRANSACTIONS_DESCRIPTIVE_ONLY":{
                f:sum(series.values()) for f,series in by_family.items()},
            "symbol_pnl_BEFORE_TRANSACTIONS_DESCRIPTIVE_ONLY":{
                s:by_symbol[s] for s in sorted(symbols)},
            "long_appearance_count_DESCRIPTIVE_ONLY":dict(sorted(long_counts.items())),
            "short_appearance_count_DESCRIPTIVE_ONLY":dict(sorted(short_counts.items())),
            "initial_insufficient_formation_cash_decisions":cash_sessions,
        }
        all_events[era]={
            "unique_instruments":len(symbols),
            "longs_per_rebalance":LEG_COUNT,
            "shorts_per_rebalance":LEG_COUNT,
            "positions_nonoverlapping_hold_common_sessions":HOLD,
        }
    s=outcome["DIAG"]["annualized_sharpe_252_rf0"]
    verdict=("NO_POSITIVE_SUPPORT" if s is None or s<=0 else
             "WEAK_EXPLORATORY_ONLY" if s<=0.5 else
             "PROMISING_EXPLORATORY_NOT_CERTIFIED")
    return {
        "identity":IDENTITY,
        "preregistered_verdict":verdict,
        "sources_count":33,
        "roster_family_counts":{k:len(v) for k,v in FAMILIES.items()},
        "formation_completed_common_sessions":FORMATION,
        "holding_common_sessions":HOLD,
        "quintile_floor_assets_long_and_short":LEG_COUNT,
        "weight_long":WEIGHT,"weight_short":-WEIGHT,
        "gross_notional_exposure":1.0,"net_notional_exposure":0.0,
        "transaction_cost_bp_per_notional_side":1.0,
        "performance":outcome,
        "calendar_33_complete_case":calendar_stats,
        "basket_rebalance_contract":all_events,
        "SP500_CFD_only_not_SPX_cash":True,
        "2024_09_17_onward_economic_holdout_read":False,
        "real_BIDASK_commissions_funding_and_fills_proven":False,
        "broker_NET_certified":False,
        "research_adaptively_chosen_after_H1_H2":True,
        "certified_traders":0,
        "production_untouched":True,
    }


def run(workdir:Path,output:Path)->dict:
    repo=os.environ.get("GITHUB_REPOSITORY","mezas3238-hue/qore-core")
    token=os.environ.get("GH_TOKEN")
    if not token:raise ValueError("H3_READONLY_ACTIONS_TOKEN_MISSING")
    register=source.get_artifact_register(repo,token)
    workdir.mkdir(parents=True,exist_ok=True)
    dailies={}
    witnesses=[]
    for symbol in sorted(freeze_universe()):
        ref=register[symbol]
        zip_path=workdir/(symbol+".zip")
        try:
            subprocess.run([
                "curl","--fail","--silent","--show-error","--location",
                "--retry","2","-H",f"Authorization: Bearer {token}",
                "-H","Accept: application/vnd.github+json",
                f"https://api.github.com/repos/{repo}/actions/artifacts/{ref['artifact_id']}/zip",
                "--output",str(zip_path)
            ],check=True)
            bars,meta=source.daily_from_zip(zip_path,symbol)
            dailies[symbol]=bars
            meta["original_source_run"]=ref["original_run"]
            meta["original_artifact_name"]=ref["original_name"]
            witnesses.append(meta)
            print("H3_XSREV5_SHA_SOURCE_PASS",symbol,len(bars),flush=True)
        finally:
            zip_path.unlink(missing_ok=True)
    report=evaluate(dailies)
    report["source_reports"]=witnesses
    if (len(witnesses)!=33 or any(
        x.get("source_sha_verified_11_annual_partitions") is not True
        for x in witnesses)):
        raise ValueError("H3_NOT_ALL_ORIGINAL_33_SOURCE_SHA_VALID")
    output.mkdir(parents=True,exist_ok=True)
    p=output/"H3_XSREV5_33_SINGLE_FROZEN_1BP_SIDE_NOT_BROKER_NET.json"
    p.write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
    (output/"SHA256SUMS.txt").write_text(
        source.sha256_bytes(p.read_bytes())+"  "+p.name+"\n")
    print("H3_XSREV5_33_FROZEN_ONE_TEST_ECONOMIC_RESULT",
          json.dumps({"verdict":report["preregistered_verdict"],
              "calendar":report["calendar_33_complete_case"],
              "DEV":{k:report["performance"]["DEV"][k] for k in (
                "annualized_sharpe_252_rf0","annualized_return_252",
                "max_drawdown","portfolio_rebalance_events",
                "assumed_cost_total_bp_of_capital_uncompounded",
                "correlation_SP500_CFD_PROXY_NOT_SPX")},
              "DIAG":{k:report["performance"]["DIAG"][k] for k in (
                "annualized_sharpe_252_rf0","annualized_return_252",
                "max_drawdown","portfolio_rebalance_events",
                "assumed_cost_total_bp_of_capital_uncompounded",
                "correlation_SP500_CFD_PROXY_NOT_SPX")},
              "broker_NET":False,"certified_traders":0},sort_keys=True),flush=True)
    return report


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("temporary_source",type=Path)
    p.add_argument("output",type=Path)
    a=p.parse_args()
    run(a.temporary_source,a.output)


if __name__=="__main__":main()
