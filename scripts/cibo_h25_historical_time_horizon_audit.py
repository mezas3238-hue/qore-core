"""H25: independent calendar-horizon forensic audit of FULL CIBO replay receipts.

Never backfill unknown mark-to-market equity, truncate failing entries,
or treat a cumulative portfolio result as guaranteed brokerage income.
Each horizon is the sum of *realized* net trade receipts with the original
provider costs already subtracted. Date windows are UTC calendar months.
"""
from __future__ import annotations

import argparse
import calendar
import json
from datetime import datetime
from decimal import Decimal, localcontext
from pathlib import Path

D = Decimal


def add_months(t: datetime, count: int) -> datetime:
    index = t.year * 12 + t.month - 1 + count
    year, mm = divmod(index, 12)
    return t.replace(
        year=year, month=mm + 1, day=min(t.day, calendar.monthrange(year, mm + 1)[1])
    )


def audit(payload: dict) -> dict:
    receipts = payload["trade_receipts"]
    assert len(receipts) == payload["trade_count"] == payload["decision_count"] == 3368
    assert payload["economic_group_report"]["all_entries_preserved"] is True
    initial = D(payload["initial_capital_usd"])
    assert initial == D("60")

    closed = sorted(
        (datetime.fromisoformat(r["realized_exit_at"]),
         D(r["realized_net_pnl_usd"]), D(r["provider_cost_usd"]),
         r["mode"])
        for r in receipts
    )
    starts = [datetime.fromisoformat(r["decision_at"]) for r in receipts]
    first = min(starts)
    anchor = first.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last = max(r[0] for r in closed)
    period_close = add_months(anchor, 36)
    assert anchor.year == 2019 and anchor.month == 7, "replay anchor changed"
    assert last < period_close, "extra settlements beyond 36 months"
    assert last >= add_months(anchor,35), "missing final month"

    with localcontext() as context:
        context.prec=90
        monthly = []
        for index in range(36):
            left=add_months(anchor,index)
            right=add_months(anchor,index+1)
            rows=[x for x in closed if left <= x[0] < right]
            monthly.append({
                "month_utc":left.strftime("%Y-%m"),
                "trade_count":len(rows),
                "net_profit_usd":str(sum((x[1] for x in rows),D(0))),
                "already_deducted_provider_cost_usd":str(sum((x[2] for x in rows),D(0)))
            })
        assert sum(x["trade_count"] for x in monthly)==3368
        settled_sum = sum((D(x["net_profit_usd"]) for x in monthly),D(0))
        cap=D(payload["ending_total_capital_usd"])
        assert abs(initial+settled_sum-cap) < D("0.00000001"),"PNL!=real capital"
        horizon={}
        for months in [1,3,6,12]:
            window=monthly[:months]
            net=sum((D(x["net_profit_usd"]) for x in window),D(0))
            horizon[str(months)]={
                "months":months,
                "from_utc":anchor.isoformat(),
                "to_exclusive_utc":add_months(anchor,months).isoformat(),
                "closed_trades":sum(x["trade_count"] for x in window),
                "profit_usd":str(net),
                "capital_end_usd_settlement_only":str(initial+net),
                "provider_cost_included_usd":str(sum((D(x["already_deducted_provider_cost_usd"]) for x in window),D(0))),
                "gain_on_initial_capital_pct":str(net/initial*D(100))
            }
        rolling={}
        for months in [1,3,6,12]:
            windows=[sum((D(monthly[j]["net_profit_usd"]) for j in range(i,i+months)),D(0))
                     for i in range(37-months)]
            sv=sorted(windows)
            n=len(sv)
            median=sv[n//2] if n%2 else (sv[n//2-1]+sv[n//2])/2
            minimum=min(range(n),key=lambda i:windows[i])
            maximum=max(range(n),key=lambda i:windows[i])
            rolling[str(months)]={
                "observed_rolling_windows":n,
                "median_profit_usd":str(median),
                "least_profit_usd":str(windows[minimum]),
                "least_profit_start_month_utc":monthly[minimum]["month_utc"],
                "most_profit_usd":str(windows[maximum]),
                "most_profit_start_month_utc":monthly[maximum]["month_utc"],
                "windows_with_loss":sum(v<0 for v in windows),
                "windows_with_gain":sum(v>0 for v in windows)
            }
        annual=[]
        for i in range(3):
            xs=monthly[i*12:(i+1)*12]
            pn=sum((D(x["net_profit_usd"]) for x in xs),D(0))
            total_to_date=sum((D(x["net_profit_usd"]) for x in monthly[:(i+1)*12]),D(0))
            annual.append({
                "from":xs[0]["month_utc"],"through":xs[-1]["month_utc"],
                "profit_usd":str(pn),"capital_end_usd_settlement_only":str(initial+total_to_date)
            })
        return {
            "window_method":"UTC calendar boundaries, first trade month 2019-07; profits booked by causal realized_exit_at timestamps; NO positions artificially restarted or reset",
            "starting_capital_usd":str(initial),
            "first_entry":first.isoformat(),
            "last_realized_exit":last.isoformat(),
            "ending_capital_usd":str(cap),
            "max_drawdown_pct":str(D(payload["max_drawdown_fraction"])*D(100)),
            "sovereign_floor_breach_usd":payload["sovereign_floor_breach_usd"],
            "trades":len(receipts),
            "from_initial_horizons":horizon,
            "calendar_years_of_replay":annual,
            "rolling_windows":rolling,
            "monthly_profit_36":monthly,
            "warning":"Historical $60 CIBO 5pct research with native provider cost assumptions. Settled-PnL only, NOT mark-to-market snapshots, broker-legal margin, funded 2000 USD or 14 USD/lot costs. Rolling windows share the same growing account, not new independent 60 USD accounts."
        }


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--h21",type=Path,required=True)
    p.add_argument("--h24",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    full={}
    for label,file in [("H21_max_capital",args.h21),("H24_min_drawdown",args.h24)]:
        full[label]=audit(json.loads(file.read_text()))
    assert abs(D(full["H21_max_capital"]["ending_capital_usd"])-D("3589.260487255495141276366310"))<D(".00000001"),"H21 differs from independently verified baseline"
    assert abs(D(full["H24_min_drawdown"]["ending_capital_usd"])-D("3304.366913245765764906010596"))<D(".00000001"),"H24 differs from independently verified baseline"
    assert all(D(v["sovereign_floor_breach_usd"])==0 for v in full.values()), "bank breach"
    result={"status":"RESEARCH_NO_FUNDING_CERTIFICATION",
            "provenance":"Full GitHub Actions replay of complete CIBO method in two tested monetary sizing/stop configurations",
            "variants":full}
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True))
    for label,v in full.items():
        print(f"CIBO_H25_{label}_HORIZONS="+json.dumps(v["from_initial_horizons"],sort_keys=True))
        print(f"CIBO_H25_{label}_YEARS="+json.dumps(v["calendar_years_of_replay"],sort_keys=True))
        print(f"CIBO_H25_{label}_ROLLING="+json.dumps(v["rolling_windows"],sort_keys=True))
    print("CIBO_H25_HORIZONS_RECONCILED_TWO_FULL_REPLAYS=YES")


if __name__=="__main__":
    main()
