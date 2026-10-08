"""H29 CIBO native monetary Sizing experiment: 2.95 USD seed stop-risk.

Research code compares two full original 3368 signal replays. A sizing target
is NOT a broker fill. Report actual model stop allocation and funding limits,
never label 2.95 fully executed unless every entry verifies it.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
from decimal import Decimal as D
from pathlib import Path
import argparse,json,statistics

START=datetime(2019,7,1,tzinfo=timezone.utc)
PERIODS={1:datetime(2019,8,1,tzinfo=timezone.utc),
         3:datetime(2019,10,1,tzinfo=timezone.utc),
         6:datetime(2020,1,1,tzinfo=timezone.utc),
         12:datetime(2020,7,1,tzinfo=timezone.utc)}
TARGET=D("2.95")


def evaluate(p):
    assert p["trade_count"]==p["decision_count"]==len(p["trade_receipts"])==3368, "missing Trader entry"
    assert p["economic_group_report"]["all_entries_preserved"], "entry not preserved"
    rs=p["trade_receipts"]
    net=sum((D(x["realized_net_pnl_usd"]) for x in rs),D(0))
    total=D(p["ending_total_capital_usd"])
    assert abs(total-D(60)-net)<D("0.00000001"),"missing/fabricated money"
    first=rs[0]
    july=[r for r in rs if START<=datetime.fromisoformat(r["decision_at"])<PERIODS[1]]
    one_year=[r for r in rs if datetime.fromisoformat(r["realized_exit_at"])<PERIODS[12]]
    def stop_stat(rows):
        amounts=[D(x["stop_risk_usd"]) for x in rows]
        below=sum(x<TARGET-D(".005") for x in amounts)
        within=sum(abs(x-TARGET)<=D(".005") for x in amounts)
        above=sum(x>TARGET+D(".005") for x in amounts)
        return {
          "entries":len(rows),"risk_below_2p95_count":below,
          "risk_exact_2p95_within_half_cent_count":within,
          "risk_above_2p95_count":above,
          "risk_median_usd":str(statistics.median(amounts)),
          "risk_mean_usd":str(sum(amounts,D(0))/len(amounts)),
          "trade_modes":dict(Counter(x["mode"] for x in rows)),
          "multiplier_hist":dict(Counter(str(x["multiplier"]) for x in rows)),
        }
    horizons={}
    for m,end in PERIODS.items():
        chosen=[r for r in rs if START<=datetime.fromisoformat(r["realized_exit_at"])<end]
        pnl=sum((D(r["realized_net_pnl_usd"]) for r in chosen),D(0))
        horizons[str(m)]={"closed_trades":len(chosen),"net_profit_usd":str(pnl),
                           "end_settled_balance_usd":str(D(60)+pnl)}
    return {
      "first_trade":{"trader_id":first.get("trader_id"),"mode":first["mode"],
                     "risk_at_stop_usd":str(first["stop_risk_usd"]),
                     "multiplier":first["multiplier"],"decision_at":first["decision_at"]},
      "first_calendar_month_entries":stop_stat(july),
      "first_12_months_closed":stop_stat(one_year),
      "full_three_year_entries":stop_stat(rs),
      "first_1_3_6_12_months":horizons,
      "initial_capital_usd":"60","ending_capital_usd":str(total),
      "net_profit_usd":str(net),
      "max_drawdown_pct":str(D(p["max_drawdown_fraction"])*D(100)),
      "sovereign_floor_breach_usd":p["sovereign_floor_breach_usd"],
      "bank_end_usd":p["ending_sovereign_bank_usd"],
      "gross_loss_usd":p["economic_group_report"]["portfolio_loss_report"]["total_gross_loss_usd"],
      "provider_cost_usd":str(sum((D(t["provider_cost_usd"]) for t in rs),D(0))),
      "all_3368_original_entries_preserved":True,
    }


def main():
    a=argparse.ArgumentParser()
    a.add_argument("--control",type=Path,required=True)
    a.add_argument("--attempt",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    x=a.parse_args()
    control=evaluate(json.loads(x.control.read_text()))
    attempt=evaluate(json.loads(x.attempt.read_text()))
    assert abs(D(control["ending_capital_usd"])-D("3589.260487255495141276366310"))<D(".00000001"),"canonical H21 drift"
    assert abs(D(control["max_drawdown_pct"])-D("34.35372258175292259029897896"))<D(".00000001"),"historical replay DD drift"
    contrast={
      "ending_capital_delta_usd":str(D(attempt["ending_capital_usd"])-D(control["ending_capital_usd"])),
      "max_drawdown_delta_percentage_points":str(D(attempt["max_drawdown_pct"])-D(control["max_drawdown_pct"])),
      "first_month_exact_target_delta_count":attempt["first_calendar_month_entries"]["risk_exact_2p95_within_half_cent_count"]-control["first_calendar_month_entries"]["risk_exact_2p95_within_half_cent_count"],
      "target_compliant_all_trades":attempt["full_three_year_entries"]["risk_below_2p95_count"]==0 and attempt["full_three_year_entries"]["risk_above_2p95_count"]==0,
      "initial_target_compliant":abs(D(attempt["first_trade"]["risk_at_stop_usd"])-TARGET)<=D(".005"),
      "sovereign_bank_zero_breach":D(attempt["sovereign_floor_breach_usd"])==0,
      "dd_at_most_25pct":D(attempt["max_drawdown_pct"])<=D(25),
    }
    out={
       "status":"RESEARCH_NONCERTIFIED",
       "experiment":"2.95 initial monetary stop budget, native CIBO source, hard original economic and liquidity limits",
       "control_original_H21":control,"variant_2p95_sizing_attempt":attempt,"comparison":contrast,
       "risk_contract_note":"Target was a seed minimum only while equity permits 5%: later entries retain original 5% compounding budget; multiplying to 2.95 is attempted only within existing cash/margin/candidate maximum. Currency values are original model not real broker legal lot fills. If a stop-risk differs from 2.95, claim only attempted target.",
       "caveat":"Not a fully FundedNext/fundability-certified USD2.95 fill replay, original CIBO native fees, no actual broker lot/contract specs, original 3y non-blind dataset."
    }
    x.output.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print("CIBO_H29_295_RESULT="+json.dumps(out,sort_keys=True))
    print("CIBO_H29_3368_REPLAY_LEDGER_RECONCILED=YES")


if __name__=="__main__": main()
