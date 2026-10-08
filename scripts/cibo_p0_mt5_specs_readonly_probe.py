"""Read-only authenticated FundedNext MetaTrader5 symbol/margin specification probe.

Run ON THE APPROVED MT5 VPS TERMINAL (already signed into the right account).
No account passwords, login IDs, tokens, orders or market mutations are
printed or saved. An unconnected MT5 terminal produces UNVERIFIED, not a spec.
Example: python scripts/cibo_p0_mt5_specs_readonly_probe.py --output specs.json
"""
from __future__ import annotations
from datetime import datetime,timezone
from decimal import Decimal as D
from pathlib import Path
import argparse,json,sys

SYMBOLS=("AUDJPY","EURUSD","GBPJPY","GBPUSD","NAS100","XAUUSD")
PUBLIC={"NAS100":"NDX100","AUDJPY":"AUDJPY","EURUSD":"EURUSD",
        "GBPJPY":"GBPJPY","GBPUSD":"GBPUSD","XAUUSD":"XAUUSD"}


def _val(value):
    if value is None:return None
    return str(value)


def probe(mt5,account_model_label:str="STELLAR_INSTANT"):
    out={"timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "account_model_label_unverified":account_model_label,
        "read_only":True,"certified":False,
        "source":"AUTHENTICATED_MT5_CONNECTED_SERVER_READ_ONLY",
        "market_symbol_specifications":{}}
    if not mt5.initialize():
        raise RuntimeError("MT5_INITIALIZE_FAILED (no authenticated terminal)")
    try:
        a=mt5.account_info()
        if a is None:raise RuntimeError("MT5_ACCOUNT_INFO_MISSING")
        if str(getattr(a,"currency","")).upper()!="USD":
            raise RuntimeError("ACCOUNT_CURRENCY_NOT_USD")
        equity=D(str(getattr(a,"equity","0")))
        if equity<=0:raise RuntimeError("MT5_EQUITY_INVALID")
        # No login/server name disclosed; can be verified by operator.
        out["account_status"]={"currency":"USD","equity_usd":str(equity),
              "free_margin_usd":_val(getattr(a,"margin_free",None)),
              "used_margin_usd":_val(getattr(a,"margin",None)),
              "account_leverage":_val(getattr(a,"leverage",None))}
        for core in SYMBOLS:
            requested=PUBLIC[core]
            found=[name for name in (requested,core)
                   if mt5.symbol_info(name) is not None]
            if not found:
                out["market_symbol_specifications"][core]={
                    "status":"SERVER_SYMBOL_NOT_FOUND","published_reference":requested}
                continue
            # An alias is selected only if the connected server actually has
            # it. A successful contract probe MUST still be reviewed before
            # mapping and actual CIBO pre-trade execution.
            sym=found[0]
            # No symbol_select: avoid mutating even Market Watch configuration.
            info=mt5.symbol_info(sym)
            tick=mt5.symbol_info_tick(sym)
            if info is None or tick is None:
                out["market_symbol_specifications"][core]={
                    "status":"SYMBOL_TICK_UNAVAILABLE","server_candidate":sym}
                continue
            side=mt5.ORDER_TYPE_BUY
            mn=D(str(info.volume_min))
            ask=D(str(tick.ask))
            point=D(str(info.point))
            if mn<=0 or point<=0 or ask<=0:
                out["market_symbol_specifications"][core]={
                    "status":"BROKER_SPEC_INVALID","server_candidate":sym}
                continue
            # Use a sample adverse price, not an actual order or live stop.
            sample_sl=ask-D(10)*point
            if sample_sl<=0:raise RuntimeError("SAMPLE_STOP_NONPOSITIVE")
            profit=mt5.order_calc_profit(side,sym,float(mn),float(ask),float(sample_sl))
            margin=mt5.order_calc_margin(side,sym,float(mn),float(ask))
            out["market_symbol_specifications"][core]={
                "status":"CONNECTED_MT5_SERVER_SPEC_QUOTE_RETRIEVED" if profit is not None and margin is not None else "MT5_CALC_UNAVAILABLE",
                "server_symbol":sym,
                "contract_size":_val(info.trade_contract_size),
                "volume_min":_val(info.volume_min),
                "volume_step":_val(info.volume_step),
                "volume_max":_val(info.volume_max),
                "tick_size":_val(info.trade_tick_size),
                "tick_value_profit":_val(getattr(info,"trade_tick_value_profit",None)),
                "tick_value_loss":_val(getattr(info,"trade_tick_value_loss",None)),
                "currency_profit":_val(getattr(info,"currency_profit",None)),
                "currency_margin":_val(getattr(info,"currency_margin",None)),
                "point":_val(info.point),
                "bid":_val(tick.bid),"ask":_val(tick.ask),
                "spread_points":_val(getattr(info,"spread",None)),
                "trade_stops_level":_val(getattr(info,"trade_stops_level",None)),
                "trade_freeze_level":_val(getattr(info,"trade_freeze_level",None)),
                "volume_limit":_val(getattr(info,"volume_limit",None)),
                "sample_stop_move_points":10,
                "sample_minlot_loss_usd":_val(-D(str(profit))) if profit is not None else None,
                "sample_minlot_margin_usd":_val(margin),
            }
        out["all_six_readable"]=all(
            out["market_symbol_specifications"][s]["status"]=="CONNECTED_MT5_SERVER_SPEC_QUOTE_RETRIEVED"
            for s in SYMBOLS)
        # Server symbols alone don't establish commission or slip, nor
        # guarantee trade_allowed/FundedNext model identity.
        out["needs_human_instrument_and_account_validation"]=True
        out["commission_and_swap_account_specific_verified"]=False
        out["certified"]=False
        return out
    finally:mt5.shutdown()


def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--output",required=True,type=Path)
 args=parser.parse_args()
 try:
  import MetaTrader5 as mt5
 except ImportError:
  raise SystemExit("MT5_PYTHON_PACKAGE_NOT_CONNECTED; no broker specification certified")
 result=probe(mt5)
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps(result,indent=2)+"\n")
 print(json.dumps({"status":"READ_ONLY_SERVER_PROBE", "six_quotes":result["all_six_readable"],
                   "spec_status_by_core_symbol":{
                     s:result["market_symbol_specifications"][s]["status"]
                     for s in SYMBOLS},"certified":False},sort_keys=True))


if __name__=="__main__":main()
