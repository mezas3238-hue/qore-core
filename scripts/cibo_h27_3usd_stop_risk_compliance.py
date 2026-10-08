"""H27 audit: exact $3 at-stop micro-budget versus original CIBO receipts.

No synthetic fills, altered market exits, fabricated fees, or dropped entries.
The user approved >=$3 stop-risk at $60, 5% of starting equity, not $0.69.
A historical stop unit is determined from stop_risk_usd/multiplier.
Proof of numeric infeasibility under integer 1x units does NOT establish
exact live broker lot minimum/margin; those require broker data.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal as D, ROUND_CEILING
from pathlib import Path
from statistics import median

EPOCH = datetime(2019,7,1,tzinfo=timezone.utc)
FIRST_END = datetime(2019,8,1,tzinfo=timezone.utc)
YEAR_END = datetime(2020,7,1,tzinfo=timezone.utc)


def _calc(rows: list[dict], target: D) -> dict:
    outcomes=[]
    for r in rows:
        unit=D(str(r["stop_risk_usd"]))/D(int(r["multiplier"]))
        if not unit.is_finite() or unit<=0: raise AssertionError("bad stop unit")
        size=int(r["multiplier"])
        stop=unit*size
        q=target/unit
        req=int(q.to_integral_value(rounding=ROUND_CEILING))
        at_req=unit*req
        outcomes.append((r,unit,size,stop,req,at_req))
    if not outcomes: raise AssertionError("no rows")
    under=[x for x in outcomes if x[3] < target]
    exact=[x for x in outcomes if x[5]==target]
    need_native_more=[x for x in outcomes if x[4]>x[2]]
    return {
        "total_entries":len(outcomes),
        "amount_goal_stop_usd":str(target),
        "currently_risk_less_than_target":len(under),
        "currently_risk_at_or_above_target":len(outcomes)-len(under),
        "less_than_target_pct":str(D(100)*len(under)/len(outcomes)),
        "median_actual_stop_usd":str(median(x[3] for x in outcomes)),
        "mean_actual_stop_usd":str(sum((x[3] for x in outcomes),D(0))/len(outcomes)),
        "median_required_integer_multiplier_for_at_least_goal":str(median(x[4] for x in outcomes)),
        "need_size_increase_vs_original_multiplier":len(need_native_more),
        "requiring_gt_10x_unit_to_hit_target":sum(x[4]>10 for x in outcomes),
        "exact_target_mathematically_possible_by_integer_multiplier":len(exact),
        "exact_target_mathematically_impossible_by_integer_multiplier":len(outcomes)-len(exact),
        "modes":dict(Counter(x[0]["mode"] for x in outcomes)),
        "first_three_examples":[{
            "trader":x[0]["trader_id"],
            "at":x[0]["decision_at"],
            "original_multiplier":x[2],
            "one_x_stop_usd":str(x[1]),
            "actual_stop_usd":str(x[3]),
            "requested_stop_usd":str(target),
            "required_integer_multiplier_at_least_target":x[4],
            "required_fractional_multiplier_for_exact_target":str(target/x[1]),
            "risk_if_rounded_integer_up_usd":str(x[5]),
            "overshoot_vs_target_usd":str(x[5]-target),
        } for x in outcomes[:3]]
    }


def audit(payload: dict) -> dict:
    original=payload["trade_receipts"]
    assert payload["initial_capital_usd"]=="60"
    assert payload["decision_count"]==payload["trade_count"]==len(original)==3368
    assert payload["economic_group_report"]["all_entries_preserved"] is True
    closed=[r for r in original if datetime.fromisoformat(r["realized_exit_at"])<YEAR_END]
    first=[r for r in original if EPOCH<=datetime.fromisoformat(r["decision_at"])<FIRST_END]
    assert len(closed)==1109 and len(first)==84
    all_a=_calc(original,D(3))
    july=_calc(first,D(3))
    year=_calc(closed,D(3))
    net_yr=sum((D(r["realized_net_pnl_usd"]) for r in closed),D(0))
    net_all=sum((D(r["realized_net_pnl_usd"]) for r in original),D(0))
    assert abs(net_yr-D("408.14184887909376990669055668136"))<D(".00000001")
    assert abs(net_all+D(60)-D(payload["ending_total_capital_usd"]))<D(".00000001")
    # This is an actual falsified claim, not a proposal for growth.
    assert july["currently_risk_less_than_target"]>0
    assert july["exact_target_mathematically_impossible_by_integer_multiplier"]>0
    return {
       "status":"NONCOMPLIANT_WITH_3USD_STOP_REQUEST",
       "replay_status":"ORIGINAL_CIBO_FULL_3368_SUCCESS_BUT_RISK_SPEC_FAIL",
       "first_july_entries":july,
       "first_year_closed_trades":year,
       "all_3year_trades":all_a,
       "first_year_net_profit_usd_original_noncompliant_model":str(net_yr),
       "first_year_average_realized_net_usd_per_closed_trade":str(net_yr/len(closed)),
       "all_3year_original_net_profit_usd":str(net_all),
       "all_3year_original_average_realized_net_usd_per_trade":str(net_all/len(original)),
       "risk_3usd_at_usd60_fraction":"0.05",
       "conclusion":"Original $60->$468 first-year model is NOT an answer to owner-specified $3 actual stop risk. Exact $3 stop is unrepresentable on most entries with native integer multipliers. Do not simply mark desired cap=5% and call it executed. Fractional position unit/verified broker minimum, accurate pre-entry floating equity and margin are prerequisites for an honest complete *3USD executed* replay.",
       "methodological_limits":"USD3 is a FIXED first-seed dollar reference across full receipt corpus, not proof of per-decision 5% dynamic risk; snapshots of floating equity would be needed for that. No modified strategy or fabricated PnL."
    }


def main():
    a=argparse.ArgumentParser()
    a.add_argument("--input",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    x=a.parse_args()
    result=audit(json.loads(x.input.read_text()))
    x.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("CIBO_H27_3USD_RISK_COMPLIANCE="+json.dumps(result,sort_keys=True))
    print("CIBO_H27_STRICT_3USD_COMPLIANCE=FAIL_CONFIRMED")
    print("CIBO_H27_MODEL_REPLAY_3368_CLOSED_RECEIPTS=PASS")


if __name__=="__main__": main()
