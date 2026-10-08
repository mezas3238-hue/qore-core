"""3-year predecision manifest forensic lotage, FundedNext published-cost proxy.

This is NOT executable-by-broker proof. The historical manifest is read-only
and has 3368 opportunities in 6 symbols. Every signal gets an individual
correct cost-inclusive dollar-risk lot computation. A real MT5 run must
replace historical USD/lot and margin/lot values with order_calc_* server data.
A lack of MT5 verification is an explicit UNKNOWN flag; never label FILLED.
"""
from __future__ import annotations
from collections import Counter
from decimal import Decimal as D, ROUND_FLOOR
from pathlib import Path
import argparse,csv,json

MARKETS={"AUDJPY":"FOREX","EURUSD":"FOREX","GBPJPY":"FOREX",
 "GBPUSD":"FOREX","NAS100":"INDEX","XAUUSD":"METAL"}
BROKER_MAP_STATUS={
 "NAS100":"NDX100 PUBLISHED_MAP_NOT_SERVER_CONFIRMED",
 "AUDJPY":"AUDJPY_SERVER_NAME_UNVERIFIED",
 "EURUSD":"EURUSD_SERVER_NAME_UNVERIFIED",
 "GBPJPY":"GBPJPY_SERVER_NAME_UNVERIFIED",
 "GBPUSD":"GBPUSD_SERVER_NAME_UNVERIFIED",
 "XAUUSD":"XAUUSD_SERVER_NAME_UNVERIFIED",
}


def risk_and_lots(row:dict,budget:D)->dict:
 opp=row["trader_opportunity"]
 symbol=row["qore_symbol"]
 if symbol not in MARKETS:raise ValueError("UNSUPPORTED_SYMBOL "+symbol)
 m=MARKETS[symbol]
 volmin=D(str(opp["minimum_volume"]))
 volmax=D(str(opp["maximum_volume"]))
 step=D(str(opp["volume_step"]))
 perstop=D(str(opp["stop_loss_per_volume"]))
 permargin=D(str(opp["margin_per_volume"]))
 assert 0<volmin<=volmax and step>0 and perstop>0 and permargin>=0
 ask=D(str(row["market_predecision_state"]["provider_observation"]["ask"]))
 bid=D(str(row["market_predecision_state"]["provider_observation"]["bid"]))
 prov=row["market_predecision_state"]["provider_observation"]
 slippage_perlot=D(str(prov.get("slippage_reserve_per_volume_usd","0")))
 tickval=D(str(prov["tick_value"]))
 ticksize=D(str(prov["tick_size"]))
 assert ask>=bid and ticksize>0 and tickval>0 and slippage_perlot>=0
 # Conservative proxy: historical raw stop-loss figure + bid/ask cost,
 # potentially double counts spread when source already prices it.
 # Must be reconciled with broker order_calc_profit, NOT a live certificate.
 spread_perlot=(ask-bid)/ticksize*tickval
 commission=(D("7") if m=="FOREX" else ask*D("100")*D("0.000016")
             if m=="METAL" else D(0))
 adverse_perlot=perstop+spread_perlot+commission+slippage_perlot
 if adverse_perlot<=0:raise ValueError("NONPOSITIVE_STOP_MODEL")
 theoretical=budget/adverse_perlot
 integer_steps=int((min(theoretical,volmax)/step).to_integral_value(rounding=ROUND_FLOOR))
 volume=D(integer_steps)*step
 if volume<volmin:volume=D(0)
 stop_money=volume*perstop
 cost_money=volume*(spread_perlot+commission+slippage_perlot)
 predicted_risk=stop_money+cost_money
 assert predicted_risk<=budget+D("0.0000000000001")
 reason=("HISTORICAL_PROXY_RISK_BELOW_BROKER_MIN_VOLUME"
         if volume==0 else "OFFLINE_PROXY_VOLUME_BROKER_MARGIN_UNVERIFIED")
 # Compare independent BASE-CASH screening ONLY, not causal capital evolving
 # portfolio. Never promote this screen as financed per-trade result.
 return {
   "signal_fingerprint":str(row["signal_fingerprint"]),
   "trader_id":str(row["trader_id"]),
   "symbol_core":symbol,
   "broker_symbol_status":BROKER_MAP_STATUS[symbol],
   "decision_at":str(row.get("market_decision_at","")),
   "side":str(opp["side"]),
   "entry_price":str(opp["intended_entry"]),
   "stop_loss":str(opp["stop_loss"]),
   "take_profit":str(opp["take_profit"]),
   "min_lots_historical":str(volmin),
   "step_lots_historical":str(step),
   "theoretical_lots":str(theoretical),
   "offline_proxy_lots":str(volume),
   "stop_only_usd_at_proxy_lots":str(stop_money),
   "commission_spread_slippage_usd_at_proxy_lots":str(cost_money),
   "total_stop_risk_usd_at_proxy_lots":str(predicted_risk),
   "margin_proxy_usd":str(volume*permargin),
   "margin_proxy_fits_static_60usd":bool(volume>0 and volume*permargin<=D(60)),
   "margin_proxy_fits_static_2000usd":bool(volume>0 and volume*permargin<=D(2000)),
   "risk_budget_usd":str(budget),
   "status":reason,
   "broker_mt5_order_calc_profit_verified":False,
   "broker_mt5_order_calc_margin_verified":False,
   "broker_executed_lots":None,
   "actual_realized_profit_usd":None,
   "actual_broker_execution_certified":False,
 }


def main():
 p=argparse.ArgumentParser()
 p.add_argument("--manifest",required=True,type=Path)
 p.add_argument("--output",required=True,type=Path)
 p.add_argument("--csv",required=True,type=Path)
 args=p.parse_args()
 manifest=json.loads(args.manifest.read_text())
 source=manifest["opportunities"]
 if len(source)!=3368:raise AssertionError("NOT_3368_SIGNALS")
 out={}
 for cap in (D("3.00"),D("2.95")):
  rows=[risk_and_lots(row,cap) for row in source]
  if set(x["symbol_core"] for x in rows)!=set(MARKETS):
   raise AssertionError("MISSING_CORE_SYMBOL")
  if len({x["signal_fingerprint"] for x in rows})!=3368:
   raise AssertionError("DUPLICATE_FINGERPRINT")
  by_symbol={}
  for sym in MARKETS:
   subset=[x for x in rows if x["symbol_core"]==sym]
   by_symbol[sym]={
    "signals":len(subset),
    "offline_proxy_stop_budget_valid":sum(D(x["offline_proxy_lots"])>0 for x in subset),
    "zero_volume_because_of_minimum_or_costs":sum(D(x["offline_proxy_lots"])==0 for x in subset),
    "static_60_margin_proxy_possible":sum(x["margin_proxy_fits_static_60usd"] for x in subset),
    "static_2000_margin_proxy_possible":sum(x["margin_proxy_fits_static_2000usd"] for x in subset),
    "mt5_verified_executable":0,
   }
  out[str(cap)]={
    "signal_count":3368,"summary_by_core_symbol":by_symbol,
    "native_mt5_executed_order_count":0,
    "certifiable_execution_count":0,
    "all_inputs_broker_spec_status":"MISSING_AUTHENTICATED_MT5_SERVER_QUOTES",
    "financial_outcome_after_resizing":None,
    "broker_commission_reference":"Stellar Instant $7 Forex LOT at opening, metal .0016% opening notional, indices 0; server tariffs override",
    "actual_margin_was_verified":False,
    "rows":rows,
  }
  if cap==D("3.00"):
   args.csv.parent.mkdir(parents=True,exist_ok=True)
   with args.csv.open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys())
    w.writeheader();w.writerows(rows)
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps({
   "experiment":"CIBO P0 OFFLINE THREE YEAR FUNDING INVESTIGATION",
   "status":"COMPLETE_INPUT_AUDIT_NOT_BROKER_EXECUTION_CERTIFICATION",
   "signal_total":3368,
   "broker_mt5_access":"UNAVAILABLE",
   "risk_budgets":out,
   "warning":"Currency converted to USD using historical manifest USD-per-volume; not server order_calc_profit. Historical margin does not prove current MT5 margin. 2019-2022 baseline PnL DOES NOT carry over to rescaled lotage. No revised DD/PnL certified.",
 },indent=2)+"\n")
 for key,v in out.items():
  print("CIBO_P0_OFFLINE_3YEAR_USD"+key+"="+json.dumps(v["summary_by_core_symbol"],sort_keys=True))
 print("CIBO_P0_3368_ALL_SIGNALS_AUDITED_NO_FAKE_MT5_FILLS=YES")


if __name__=="__main__":main()
