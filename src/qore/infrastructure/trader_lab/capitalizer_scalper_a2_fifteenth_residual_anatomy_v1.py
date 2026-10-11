"""Audit15: classify frozen source-anchored causal-first economics by ID.

All nine-market economic rows originate in Audit14 GitHub run 38102352779.
This script never selects, rejects, amends or optimizes a candidate.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_scalper_a2_fourteenth_winner_reconciliation_v1 as original_keys,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    _jsonl,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
    _metrics,
    _portfolio_select,
)

IDENTITY = "QORE_SCALPER_A2_FIFTEENTH_FROZEN_1997_RESIDUAL_ANATOMY_V1"


def read(
    root: Path,
) -> tuple[list[dict[str, Any]], tuple[V49EconomicTrade, ...], tuple[V49EconomicTrade, ...]]:
    rows = [x for p in sorted(root.rglob("scalper-audit14-ids.jsonl")) for x in _jsonl(p)]
    old = tuple(V49EconomicTrade(**x) for p in sorted(
        root.rglob("capitalizer-*-v49-development-economics-trades.jsonl")
    ) for x in _jsonl(p))
    new = tuple(V49EconomicTrade(**x) for p in sorted(
        root.rglob("scalper-audit14-candidates.jsonl")
    ) for x in _jsonl(p))
    if len(rows) != 2876 or len(old) != 2876 or len(new) != 2816:
        raise ValueError("frozen Audit14 nine-market population changed")
    if len({x["source_opportunity_id"] for x in rows}) != 2876:
        raise ValueError("duplicate source ID")
    if len({original_keys.source_key(x) for x in rows}) != 2876:
        raise ValueError("original source trade key collided")
    if len({original_keys.candidate_key(x) for x in rows if x["status"] == "ELIGIBLE"}) != len(new):
        raise ValueError("eligible source candidate key collided")
    return rows, old, new


def partition(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Count by pre-existing provenance only; no optimized subgroup selection."""

    def breakdown(items: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "n": len(items),
            "by_market": dict(sorted(Counter(x["symbol"] for x in items).items())),
            "by_session": dict(sorted(Counter(x["session"] for x in items).items())),
            "by_original_family": dict(sorted(Counter(x["source_family"] for x in items).items())),
            "by_online_family": dict(sorted(Counter(x["online_family"] for x in items).items())),
            "by_family_transition": dict(sorted(Counter(
                x["source_family"]+"->"+x["online_family"] for x in items
            ).items())),
            "online_changed": sum(x["first_online_differs"] for x in items),
            "online_same": sum(not x["first_online_differs"] for x in items),
            "frozen_381": sum(x["frozen_381"] for x in items),
        }
    return {
        "ALL": breakdown(rows),
        "ELIGIBLE": breakdown([x for x in rows if x["status"] == "ELIGIBLE"]),
        "INVALID_M15_STOP": breakdown([
            x for x in rows if x["status"] == "INVALID_M15_STOP_AT_ONLINE_CLOSE"
        ]),
        "NO_H1_TARGET": breakdown([
            x for x in rows if x["status"] == "NO_UNTOUCHED_H1_OBJECTIVE_AT_ONLINE_CLOSE"
        ]),
    }


def anatomy(root: Path) -> dict[str, Any]:
    rows, old, new = read(root)
    source_by_old = {original_keys.source_key(x): x for x in rows}
    source_by_new = {original_keys.candidate_key(x): x for x in rows if x["status"] == "ELIGIBLE"}
    if ({original_keys.original_key(t) for t in old} != set(source_by_old)
            or {original_keys.original_key(t) for t in new} != set(source_by_new)):
        raise ValueError("source-ID joins incomplete; never infer IDs from PnL")
    old_selected = tuple(t for _, t in _portfolio_select(old))
    new_selected = tuple(t for _, t in _portfolio_select(new))
    if len(old_selected) != 2020 or len(new_selected) != 1997:
        raise ValueError("frozen MAX3 selection changed")
    old_map = {source_by_old[original_keys.original_key(t)]["source_opportunity_id"]: t
               for t in old_selected}
    new_map = {source_by_new[original_keys.original_key(t)]["source_opportunity_id"]: t
               for t in new_selected}
    if len(old_map) != 2020 or len(new_map) != 1997:
        raise ValueError("MAX3 IDs collided")
    all_by_id = {x["source_opportunity_id"]:x for x in rows}
    old_ids, new_ids = set(old_map),set(new_map)
    kept,removed,added=old_ids&new_ids,old_ids-new_ids,new_ids-old_ids
    if (len(kept),len(removed),len(added))!=(1947,73,50):
        raise ValueError("frozen MAX3 churn identities mismatch")
    transitions=partition(rows)
    def cohort(ids:set[str])->dict[str,Any]:
        value: dict[str, Any] = partition(
            [all_by_id[sid] for sid in sorted(ids)]
        )
        return dict(value["ALL"])
    changed_winners={sid for sid in kept
                     if Decimal(old_map[sid].realized_gross_r)>0
                     and Decimal(new_map[sid].realized_gross_r)<0}
    if len(changed_winners)!=32:
        raise ValueError("previously audited 32 winners-to-losers changed")
    flips=[]
    for sid in sorted(changed_winners):
        earlier=datetime.fromisoformat(new_map[sid].entry_at)-datetime.fromisoformat(
            old_map[sid].entry_at
        )
        old_t,new_t=old_map[sid],new_map[sid]
        flips.append({
            "id":sid,"market":new_t.symbol,"session":new_t.session,
            "original_family":old_t.trigger_family,"new_family":new_t.trigger_family,
            "entry_shift_minutes":str(Decimal(str(earlier.total_seconds()))/Decimal(60)),
            "original_exit_reason":old_t.exit_reason,
            "new_exit_reason":new_t.exit_reason,
            "original_target_r":old_t.planned_reward_r,
            "new_target_r":new_t.planned_reward_r,
            "original_result_r":old_t.realized_gross_r,
            "new_result_r":new_t.realized_gross_r,
            "entry_changed":new_t.entry_at!=old_t.entry_at,
            "entry_price_changed":new_t.entry_price!=old_t.entry_price,
            "target_changed":new_t.target_price!=old_t.target_price,
            "stop_price_changed":new_t.stop_price!=old_t.stop_price,
        })
    shifts=[
        Decimal(f["entry_shift_minutes"]) for f in flips
    ]
    if any(x>0 for x in shifts):
        raise ValueError("first streaming cannot be later than frozen V49 entry")
    orig_winner={sid for sid,t in old_map.items() if Decimal(t.realized_gross_r)>0}
    new_winner={sid for sid,t in new_map.items() if Decimal(t.realized_gross_r)>0}
    if len(orig_winner)!=1167 or len(new_winner)!=1154:
        raise ValueError("winner counts changed")
    metrics_old=_metrics(old_selected)
    metrics_new=_metrics(new_selected)
    if (
        abs(
            Decimal(metrics_old.profit_factor or "0")-Decimal("0.6644630742216047")
        )>Decimal("0.000001")
        or abs(
            Decimal(metrics_new.profit_factor or "0")-Decimal("0.8425240504779709")
        )>Decimal("0.000001")
    ):
        raise ValueError("primary Audit14 P&L must reproduce exactly")
    def summarize_trades(trades:tuple[V49EconomicTrade,...])->dict[str,Any]:
        if not trades:
            return {"n":0}
        result=_metrics(trades)
        wins=[Decimal(t.realized_gross_r) for t in trades
              if Decimal(t.realized_gross_r)>0]
        losses=[Decimal(t.realized_gross_r) for t in trades
                if Decimal(t.realized_gross_r)<0]
        rrs=[Decimal(t.planned_reward_r) for t in trades]
        return {
            "n":len(trades),"gross_pf":result.profit_factor,
            "gross_dd_r":result.max_drawdown_r,
            "gross_total_r":result.total_r,
            "wins":len(wins),"losses":len(losses),
            "mean_win_r":str(sum(wins,Decimal(0))/len(wins)) if wins else None,
            "mean_loss_magnitude_r":str(-sum(losses,Decimal(0))/len(losses)) if losses else None,
            "median_planned_target_r":str(median(rrs)),
            "planned_target_at_least_1r":sum(v>=1 for v in rrs),
            "planned_target_below_0_5r":sum(v<Decimal("0.5") for v in rrs),
            "stop_exit_n":result.stop_exits,
            "target_exit_n":result.target_exits,
            "session_exit_n":result.session_exits,
        }
    family={}
    for name in sorted({t.trigger_family for t in old_selected+new_selected}):
        family[name]={
            "v49":summarize_trades(tuple(t for t in old_selected if t.trigger_family==name)),
            "online":summarize_trades(tuple(t for t in new_selected if t.trigger_family==name)),
        }
    markets={}
    for sym in sorted({t.symbol for t in old_selected+new_selected}):
        markets[sym]={
            "v49":summarize_trades(tuple(t for t in old_selected if t.symbol==sym)),
            "online":summarize_trades(tuple(t for t in new_selected if t.symbol==sym)),
        }
    sessions={}
    for name in sorted({t.session for t in old_selected+new_selected}):
        sessions[name]={
            "v49":summarize_trades(tuple(t for t in old_selected if t.session==name)),
            "online":summarize_trades(tuple(t for t in new_selected if t.session==name)),
        }
    by_reason=dict(sorted(Counter(
        f["original_exit_reason"]+"->"+f["new_exit_reason"] for f in flips
    ).items()))
    return {
        "identity":IDENTITY,
        "source_ids":2876,"baseline_max3":2020,"online_max3":1997,
        "invalid_source_breakdown":transitions,
        "max3_removed":cohort(removed),"max3_added":cohort(added),
        "max3_retained":cohort(kept),
        "winner_to_loser_n":len(flips),
        "winner_to_loser_classification":cohort(changed_winners),
        "winner_to_loser_exit_reason_transitions":by_reason,
        "winner_to_loser_entry_shift_earlier_n":sum(v<0 for v in shifts),
        "winner_to_loser_entry_shift_same_n":sum(v==0 for v in shifts),
        "winner_to_loser_median_shift_min":str(median(shifts)),
        "winner_to_loser_changed_target_n":sum(x["target_changed"] for x in flips),
        "winner_to_loser_changed_stop_n":sum(x["stop_price_changed"] for x in flips),
        "winner_to_loser_receipts":flips,
        "old_average_win_r":summarize_trades(old_selected)["mean_win_r"],
        "new_average_win_r":summarize_trades(new_selected)["mean_win_r"],
        "old_average_loss_r":summarize_trades(old_selected)["mean_loss_magnitude_r"],
        "new_average_loss_r":summarize_trades(new_selected)["mean_loss_magnitude_r"],
        "target_and_stop_geometry":{"all_original":summarize_trades(old_selected),
                                    "all_online":summarize_trades(new_selected),
                                    "by_market":markets,"by_session":sessions,
                                    "by_family":family},
        "outcome_based_filtering":False,
        "physical_bid_ask_replay":False,
        "universe_regenerated_from_raw_H1_M15":False,
        "certified":False,
    }


def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("inputs",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    report=anatomy(args.inputs)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"scalper-a2-audit15-residual-anatomy-nine-market.json").write_text(
        json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print(json.dumps({key:value for key,value in report.items()
                      if key not in ("winner_to_loser_receipts",
                                     "baseline_max3_source_ids",
                                     "online_max3_source_ids")},sort_keys=True))


if __name__=="__main__":
    main()
