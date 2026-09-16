"""Evaluate the tick-corrected consumed VT-31 ledger under predeclared gates.

No rule or threshold is selected here. Terminal trades are evaluated chronologically
at fixed friction 0.05/0.075/0.10R. The gate scenario is 0.10R. Quartiles are four
equal-count chronological slices. Temporal blocks are every non-empty calendar
half-year represented by terminal trades. Monte Carlo is deterministic 10k-path
moving-block bootstrap with block length 5. Passing this file is necessary but
not sufficient for R9 or certification; WFO/provider/prop/fresh remain separate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

FRICTIONS=(Decimal("0.05"),Decimal("0.075"),Decimal("0.10"))
GATE_FRICTION=Decimal("0.10")
MARKETS=("NAS100","SP500","US30")
SIDES=("long","short")
MIN_SAMPLE=150
MIN_MARKET_SAMPLE=30
MIN_PF=Decimal("1.10")
MAX_DD=Decimal("20")
MIN_MC_POSITIVE=Decimal("0.70")
MAX_MC_P95_DD=Decimal("20")
MC_PATHS=10000
BLOCK=5


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _net_rows(trades: list[dict[str,Any]], friction: Decimal) -> list[dict[str,Any]]:
    rows=[]
    for trade in trades:
        row=dict(trade)
        row["net_r"]=format(_d(trade["terminal_r"])-friction,"f")
        rows.append(row)
    return rows


def _metrics(rows: list[dict[str,Any]]) -> dict[str,Any]:
    values=[_d(row["net_r"]) for row in rows]
    total=sum(values,Decimal(0))
    wins=sum((v for v in values if v>0),Decimal(0))
    losses=-sum((v for v in values if v<0),Decimal(0))
    equity=Decimal(0); peak=Decimal(0); dd=Decimal(0)
    max_losing=0; losing=0
    for value in values:
        equity+=value; peak=max(peak,equity); dd=max(dd,peak-equity)
        if value<0:
            losing+=1; max_losing=max(max_losing,losing)
        else:
            losing=0
    return {
        "sample":len(values),
        "wins":sum(v>0 for v in values),
        "losses":sum(v<0 for v in values),
        "flats":sum(v==0 for v in values),
        "total_r":format(total,"f"),
        "mean_r":format(total/Decimal(len(values)),"f") if values else "0",
        "profit_factor":format(wins/losses,"f") if losses>0 else None,
        "max_drawdown_r":format(dd,"f"),
        "max_losing_streak":max_losing,
    }


def _group(rows: list[dict[str,Any]], key: str) -> dict[str,dict[str,Any]]:
    grouped:dict[str,list[dict[str,Any]]]=defaultdict(list)
    for row in rows:
        grouped[str(row[key])].append(row)
    return {name:_metrics(items) for name,items in sorted(grouped.items())}


def _quartiles(rows: list[dict[str,Any]]) -> list[dict[str,Any]]:
    n=len(rows); result=[]
    for q in range(4):
        start=n*q//4; end=n*(q+1)//4
        metrics=_metrics(rows[start:end])
        result.append({"quartile":q+1,"start_index":start,"end_index_exclusive":end,**metrics})
    return result


def _half_year_key(signal: str) -> str:
    dt=datetime.fromisoformat(signal.replace("Z","+00:00"))
    return f"{dt.year}-H{1 if dt.month<=6 else 2}"


def _temporal(rows: list[dict[str,Any]]) -> dict[str,Any]:
    grouped:dict[str,list[dict[str,Any]]]=defaultdict(list)
    for row in rows:
        grouped[_half_year_key(str(row["signal_opened_at"]))].append(row)
    blocks={key:_metrics(grouped[key]) for key in sorted(grouped)}
    positive=sum(_d(value["mean_r"])>0 for value in blocks.values())
    required=math.ceil(Decimal(2)*Decimal(len(blocks))/Decimal(3)) if blocks else 0
    return {"definition":"non-empty calendar half-years","eligible_blocks":len(blocks),"positive_blocks":positive,"required_positive_blocks":required,"blocks":blocks}


def _monte_carlo(trades: list[dict[str,Any]], friction: Decimal) -> dict[str,Any]:
    raw=[_d(row["terminal_r"])-friction for row in trades]
    n=len(raw)
    if n==0:
        return {"paths":MC_PATHS,"block_length":BLOCK,"positive_terminal_probability":"0","p05_terminal_r":"0","p50_terminal_r":"0","p95_max_drawdown_r":"0"}
    terminals=[]; drawdowns=[]
    domain=f"qore:vt31:tick-corrected-economics:v1:{friction}".encode()
    for path_index in range(MC_PATHS):
        sampled=[]; block_index=0
        while len(sampled)<n:
            digest=hashlib.sha256(domain+b":"+str(path_index).encode()+b":"+str(block_index).encode()).digest()
            start=int.from_bytes(digest,"big")%n
            sampled.extend(raw[(start+offset)%n] for offset in range(BLOCK))
            block_index+=1
        equity=Decimal(0); peak=Decimal(0); dd=Decimal(0)
        for value in sampled[:n]:
            equity+=value; peak=max(peak,equity); dd=max(dd,peak-equity)
        terminals.append(equity); drawdowns.append(dd)
    terminals.sort(); drawdowns.sort()
    def q(values:list[Decimal],pct:int)->Decimal:
        return values[(len(values)-1)*pct//100]
    probability=Decimal(sum(value>0 for value in terminals))/Decimal(MC_PATHS)
    return {"paths":MC_PATHS,"block_length":BLOCK,"positive_terminal_probability":format(probability,"f"),"p05_terminal_r":format(q(terminals,5),"f"),"p50_terminal_r":format(q(terminals,50),"f"),"p95_max_drawdown_r":format(q(drawdowns,95),"f")}


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("ledger",type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    ledger=json.loads(args.ledger.read_text())
    if ledger.get("research_only") is not True or ledger.get("opens_new_holdout") is not False:
        raise ValueError("ledger governance guard failed")
    trades=ledger.get("trades")
    if not isinstance(trades,list) or len(trades)!=ledger.get("terminal_trade_count"):
        raise ValueError("terminal ledger malformed")
    if trades!=sorted(trades,key=lambda row:(row["signal_opened_at"],row["market"],row["root_id"])):
        raise ValueError("terminal ledger must be chronological")
    results={}
    for friction in FRICTIONS:
        rows=_net_rows(trades,friction)
        results[format(friction,"f")]={
            "aggregate":_metrics(rows),
            "markets":_group(rows,"market"),
            "sides":_group(rows,"side"),
            "partitions":_group(rows,"partition"),
            "quartiles":_quartiles(rows),
            "temporal":_temporal(rows),
            "monte_carlo":_monte_carlo(trades,friction),
        }
    gate=results[format(GATE_FRICTION,"f")]
    agg=gate["aggregate"]; markets=gate["markets"]; sides=gate["sides"]
    quartiles=gate["quartiles"]; temporal=gate["temporal"]; mc=gate["monte_carlo"]
    gates={
        "aggregate_sample_at_least_150":int(agg["sample"])>=MIN_SAMPLE,
        "each_market_sample_at_least_30":all(name in markets and int(markets[name]["sample"])>=MIN_MARKET_SAMPLE for name in MARKETS),
        "stressed_mean_positive":_d(agg["mean_r"])>0,
        "profit_factor_at_least_1_10":agg["profit_factor"] is not None and _d(agg["profit_factor"])>=MIN_PF,
        "stressed_max_drawdown_at_most_20r":_d(agg["max_drawdown_r"])<=MAX_DD,
        "every_market_stressed_mean_positive":all(name in markets and _d(markets[name]["mean_r"])>0 for name in MARKETS),
        "long_and_short_stressed_mean_positive":all(name in sides and _d(sides[name]["mean_r"])>0 for name in SIDES),
        "at_least_3_of_4_positive_quartiles":sum(_d(row["mean_r"])>0 for row in quartiles)>=3,
        "at_least_2_of_3_temporal_blocks_positive":int(temporal["positive_blocks"])>=int(temporal["required_positive_blocks"]),
        "mc_positive_terminal_at_least_0_70":_d(mc["positive_terminal_probability"])>=MIN_MC_POSITIVE,
        "mc_p95_max_drawdown_at_most_20r":_d(mc["p95_max_drawdown_r"])<=MAX_MC_P95_DD,
    }
    payload={
        "schema":"qore.vt31.tick_corrected_consumed_economics.v1",
        "research_only":True,
        "opens_new_holdout":False,
        "candidate_status":"NO_R9_NOT_CERTIFIED",
        "gate_friction_r_per_trade":format(GATE_FRICTION,"f"),
        "frictions_r_per_trade":[format(x,"f") for x in FRICTIONS],
        "temporal_block_definition":"all non-empty calendar half-years; required positive = ceil(2/3 eligible)",
        "quartile_definition":"four chronological equal-count slices",
        "results":results,
        "gates":gates,
        "consumed_economic_gate_pass":all(gates.values()),
        "not_sufficient_for_certification":["formal governor WFO","provider perturbation robustness","prop-account DD qualification","exact R9 freeze","Full QORE exact HEAD","genuine fresh one-shot","independent validation"],
    }
    args.output.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"gate_friction":"0.10","aggregate":agg,"markets":markets,"sides":sides,"quartiles_positive":sum(_d(row['mean_r'])>0 for row in quartiles),"temporal_positive":f"{temporal['positive_blocks']}/{temporal['eligible_blocks']}","monte_carlo":mc,"gates":gates,"pass":payload['consumed_economic_gate_pass']},sort_keys=True))


if __name__=="__main__":
    main()
