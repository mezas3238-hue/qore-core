"""Audit15 stop/noise 2x2 on fixed selected Audit14 MAX3 (1997 only).

No optimization, no new source selection or MAX3 reselection. Recompute
hypothetical pivot-stop outcomes from causal completed M1; missing pivots are
reported, never silently converted to a M15 win. All metrics are GROSS-R.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_scalper_a2_fourteenth_winner_reconciliation_v1 as keys,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEFAULT_LOOKBACK,
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_trader_v49 import (
    materialize_trade_intent,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_stop_noise_factorial_v1 import (
    Arm,
    analyze_source_geometry,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    _jsonl,
    source_id,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
    _replay_one,
    _session_bars,
)

IDENTITY="QORE_SCALPER_A2_FIFTEENTH_FIXED_MAX3_M15_M1_STOP_NOISE_2X2_V1"


def market(
    sel:Path,source:Path,econ:Path,native_root:Path,
)->tuple[dict[str,Any],tuple[dict[str,Any],...]]:
    pick=list(sel.rglob("scalper-a2-audit15-residual-anatomy-nine-market.json"))
    frozen=list(source.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl"))
    alt=list(econ.rglob("scalper-audit14-candidates.jsonl"))
    receipt=list(econ.rglob("scalper-audit14-ids.jsonl"))
    if any(len(x)!=1 for x in (pick,frozen,alt,receipt)):
        raise ValueError("requires one frozen source, alternative, and MAX3 selection ledger")
    chosen=set(json.loads(pick[0].read_text(encoding="utf-8"))["online_max3_source_ids"])
    if len(chosen)!=1997:
        raise ValueError("must preserve exact first-online MAX3 selection")
    source_rows=tuple(V49Opportunity(**x) for x in _jsonl(frozen[0]))
    candidate_rows=tuple(V49EconomicTrade(**x) for x in _jsonl(alt[0]))
    mapping=tuple(_jsonl(receipt[0]))
    if not source_rows or len(source_rows)!=len(mapping):
        raise ValueError("original market source count mismatch")
    symbol=source_rows[0].symbol
    source_by_id={source_id(x):x for x in source_rows}
    selected_by_trade={keys.candidate_key(x):x["source_opportunity_id"]
                       for x in mapping if x["status"]=="ELIGIBLE"}
    selected=tuple((selected_by_trade[keys.original_key(t)],t) for t in candidate_rows
                   if selected_by_trade[keys.original_key(t)] in chosen)
    if len({sid for sid,t in selected})!=len(selected):
        raise ValueError("duplicate selected source IDs")
    bars=tuple(x for x in iter_cibo_m1(native_root)
               if DEV_WINDOW_START-DEFAULT_LOOKBACK<=x.opened_at<DEV_WINDOW_END)
    if not bars or any(x.symbol!=symbol for x in bars):
        raise ValueError("provider M1 wrong market")
    opened=tuple(x.opened_at for x in bars)
    econbars=tuple(x for x in bars if x.opened_at>=DEV_WINDOW_START)
    econopened=tuple(x.opened_at for x in econbars)
    rows=[]
    counts:Counter[str]=Counter()
    for sid,trade in selected:
        source_op=source_by_id[sid]
        new_source=replace(
            source_op,
            m1_trigger_confirmed_at=trade.entry_at,
            m1_trigger_family=trade.trigger_family,
            decision_reference_price=trade.entry_price,
            structural_target_witness_price=trade.target_price,
        )
        intent=materialize_trade_intent(new_source)
        if (trade.entry_price!=str(intent.entry_price) or
                trade.stop_price!=str(intent.stop_price) or
                trade.target_price!=str(intent.target_price)):
            raise ValueError("source-anchored fixed economic intent not reconciled")
        session_bars=_session_bars(econbars,econopened,intent=intent)
        previous=_replay_one(session_bars,intent)
        if previous != trade:
            raise ValueError("factorial M15 baseline must reproduce 1997 selected trades")
        alt_m1:V49EconomicTrade|None=None
        try:
            gate=analyze_source_geometry(new_source,bars,opened)
            if gate.m1_anchor_available and gate.m1_anchor_price is not None:
                new_stop=Decimal(gate.m1_anchor_price)
                viable=(
                    new_stop<intent.entry_price<intent.target_price
                    if trade.direction=="LONG"
                    else intent.target_price<intent.entry_price<new_stop
                )
                if viable:
                    alternate=replace(intent,stop_price=new_stop)
                    alt_m1=_replay_one(session_bars,alternate)
                else:
                    counts["M1_PIVOT_BAD_PRICE_GEOMETRY"]+=1
            else:
                counts["M1_PIVOT_NO_CAUSAL_WITNESS"]+=1
            noise_pass=Arm.M15_NOISE_VETO.value in gate.eligible_arms
            noise_reason=gate.m1_noise_reason
        except ValueError:
            counts["M1_STRUCTURAL_OBSERVER_UNKNOWN"]+=1
            noise_pass=False
            noise_reason="CAUSAL_OBSERVER_UNAVAILABLE"
        arms:dict[str,str|None]={
            Arm.M15_NOISE_OFF.value:trade.realized_gross_r,
            Arm.M15_NOISE_VETO.value:trade.realized_gross_r if noise_pass else None,
            Arm.M1_NOISE_OFF.value:alt_m1.realized_gross_r if alt_m1 else None,
            Arm.M1_NOISE_VETO.value:
                alt_m1.realized_gross_r if alt_m1 and noise_pass else None,
        }
        if alt_m1 is not None:
            counts["M1_PIVOT_EXECUTION_REPLAYED"]+=1
        rows.append({
            "source_opportunity_id":sid,"symbol":symbol,"session":trade.session,
            "family":trade.trigger_family,"entry_at":trade.entry_at,
            "baseline_realized_gross_r":trade.realized_gross_r,
            "stop_M15_price":trade.stop_price,
            "stop_M1_price":alt_m1.stop_price if alt_m1 else None,
            "noise_reason":noise_reason,
            "factorial_gross_R":arms,"entry_target_unchanged":True,
            "fixed_max3_no_reselection":True,"outcome_used_for_entry":False,
        })
    return ({
        "identity":IDENTITY,"symbol":symbol,"fixed_selected":len(selected),
        "counts":dict(sorted(counts.items())),
        "no_new_trade_or_filter_authority":True,
        "costs_bid_ask_missing":True,
    },tuple(rows))


def matrix(root:Path)->dict[str,Any]:
    reports=[json.loads(p.read_text(encoding="utf-8"))
             for p in sorted(root.rglob("audit15-factorial-market.json"))]
    if len(reports)!=9 or len({r["symbol"] for r in reports})!=9:
        raise ValueError("9-market factorial outputs incomplete")
    rows=[x for p in sorted(root.rglob("audit15-factorial-ids.jsonl"))
          for x in _jsonl(p)]
    if len(rows)!=1997 or len({x["source_opportunity_id"] for x in rows})!=1997:
        raise ValueError("MAX3 fixed selected ID population not 1997")
    arms:dict[str,Any]={}
    for arm in Arm:
        values=[Decimal(x["factorial_gross_R"][arm.value])
                for x in rows if x["factorial_gross_R"][arm.value] is not None]
        plus=sum((v for v in values if v>0),Decimal(0))
        minus=-sum((v for v in values if v<0),Decimal(0))
        arms[arm.value]={
            "fixed_original_MAX3":1997,
            "covered":len(values),
            "not_covered":1997-len(values),
            "gross_profit_R":str(plus),"gross_loss_R":str(minus),
            "gross_PF":str(plus/minus) if minus else None,
            "gross_total_R":str(plus-minus),
            "NOT_reselected_portfolio":True,
        }
    base=arms[Arm.M15_NOISE_OFF.value]
    if (
        base["covered"]!=1997 or
        abs(Decimal(base["gross_PF"] or "0")-Decimal("0.8425240504779709"))>
        Decimal("0.000001")
    ):
        raise ValueError("factorial reference did not reproduce causal-first economics")
    return {
        "identity":IDENTITY,"fixed_online_MAX3":1997,"markets":9,
        "arms":arms,
        "source_causal_geometry_not_outcome_fit":True,
        "no_rule_promoted_to_trading":True,
        "broker_costs_applied":False,"trader_certified":False,
    }


def main()->None:
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="mode",required=True)
    m=sub.add_parser("market")
    for arg in ("selection","source","economic","native","output"):
        m.add_argument(arg,type=Path)
    a=sub.add_parser("matrix")
    a.add_argument("inputs",type=Path)
    a.add_argument("output",type=Path)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    if args.mode=="market":
        report,rows=market(args.selection,args.source,args.economic,args.native)
        (args.output/"audit15-factorial-market.json").write_text(
            json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
        )
        with (args.output/"audit15-factorial-ids.jsonl").open("w",encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row,sort_keys=True)+"\n")
    else:
        report=matrix(args.inputs)
        (args.output/"audit15-factorial-nine-market.json").write_text(
            json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
        )
    print(json.dumps(report,sort_keys=True))


if __name__=="__main__":
    main()
