"""FundedNext Stellar Instant P0: executable MT5 lot sizing and single-source risk.

No broker API calls are made without an explicitly supplied MT5-like client.
This never sends orders or creates fills. Use order_calc_profit and
order_calc_margin from the connected ACCOUNT SERVER as source of truth.
FundedNext public contract sizes/leverage are references, not live specs.
Costs use help-center 2026-09 $7/forex lot ON OPEN ONLY, metals
0.0016% opening notional, indices $0 (verify exact account tariff).
Orders without server specs/funds are rejected before broker submission.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal as D, ROUND_FLOOR
from threading import RLock
from typing import Any, Protocol

SYMBOL_CLASSES = {
    "AUDJPY":"FOREX","EURUSD":"FOREX","GBPJPY":"FOREX",
    "GBPUSD":"FOREX","NAS100":"INDEX","XAUUSD":"METAL",
}
CONTRACT_REFERENCES = {
    "AUDJPY":D("100000"),"EURUSD":D("100000"),
    "GBPJPY":D("100000"),"GBPUSD":D("100000"),
    "NAS100":D("10"),"XAUUSD":D("100"),
}
INSTANT_MAX_LEVERAGE = {"FOREX":D(30),"INDEX":D(5),"METAL":D("7.5")}


class FundingError(ValueError):
    """Source-of-truth MT5 accounting cannot authorize executable volume."""


class Mt5Like(Protocol):
    ORDER_TYPE_BUY: int
    ORDER_TYPE_SELL: int
    def symbol_info(self,symbol:str) -> Any: ...
    def symbol_info_tick(self,symbol:str) -> Any: ...
    def account_info(self) -> Any: ...
    def order_calc_profit(self,order_type:int,symbol:str,volume:float,open_price:float,close_price:float) -> float | None: ...
    def order_calc_margin(self,order_type:int,symbol:str,volume:float,price:float) -> float | None: ...


def dec(v:Any,name:str,*,allow_zero:bool=False) -> D:
    if isinstance(v,bool) or v is None:
        raise FundingError(name+" missing or invalid")
    try: a=D(str(v))
    except Exception as e: raise FundingError(name+" not numeric") from e
    if not a.is_finite() or a<0 or (a==0 and not allow_zero):
        raise FundingError(name+" nonpositive or nonfinite")
    return a


def valid_grid(volume:D,minimum:D,step:D,maximum:D)->bool:
    return minimum<=volume<=maximum and (volume/step)==(volume/step).to_integral_value()


@dataclass(frozen=True)
class RiskPolicy:
    per_entry_usd:D=D("3.00")
    max_portfolio_open_stop_usd:D=D("9.00")
    max_symbol_open_stop_usd:D=D("6.00")
    max_trader_open_stop_usd:D=D("6.00")
    max_group_open_stop_usd:D=D("9.00")
    slippage_points:D=D("0")
    adverse_extra_usd_per_lot:D=D("0")
    min_margin_level_pct:D=D("150")
    sovereign_floor_usd:D=D("0")
    policy_version:str="stellar-instant-p0-fixed-3usd-v1"


@dataclass(frozen=True)
class Quote:
    trade_id:str
    trader_id:str
    core_symbol:str
    broker_symbol:str
    side:str
    entry_price:D
    stop_price:D
    lots:D
    price_stop_risk_usd:D
    commission_usd:D
    adverse_cost_usd:D
    total_stop_risk_usd:D
    margin_usd:D
    margin_free_before_usd:D
    margin_free_after_usd:D
    equity_before_usd:D
    total_open_risk_after_usd:D
    theoretical_lots:D
    contract_size:D
    volume_step:D
    provider_snapshot_status:str
    policy_version:str
    group_id:str


class FundedNextMT5Calculator:
    """No synthetic prices: all monetary stop PnL and margin from MT5."""
    def __init__(self,client:Mt5Like,symbol_map:dict[str,str],*,max_quote_age_s:int=30):
        self.client=client
        self.symbol_map=dict(symbol_map)
        self.max_quote_age_s=max_quote_age_s

    def snapshot(self,core_symbol:str)->dict[str,Any]:
        if core_symbol not in SYMBOL_CLASSES:
            raise FundingError("UNSUPPORTED_CORE_SYMBOL")
        broker_symbol=self.symbol_map.get(core_symbol)
        if not broker_symbol: raise FundingError("MT5_SYMBOL_MAPPING_UNVERIFIED")
        info=self.client.symbol_info(broker_symbol)
        tick=self.client.symbol_info_tick(broker_symbol)
        account=self.client.account_info()
        if info is None or tick is None or account is None:
            raise FundingError("MT5_SPECS_OR_TICK_OR_ACCOUNT_UNAVAILABLE")
        for k in ("volume_min","volume_step","volume_max","trade_contract_size","trade_tick_size"):
            dec(getattr(info,k,None),k)
        mn,st,mx=(dec(getattr(info,k),k) for k in ("volume_min","volume_step","volume_max"))
        if mx<mn or (mn/st)!=(mn/st).to_integral_value():
            raise FundingError("MT5_LOT_GRID_INVALID")
        bid=dec(getattr(tick,"bid",None),"bid")
        ask=dec(getattr(tick,"ask",None),"ask")
        if ask<bid:raise FundingError("MT5_BID_ASK_CROSSED")
        equity=dec(getattr(account,"equity",None),"equity")
        free=dec(getattr(account,"margin_free",None),"margin_free",allow_zero=True)
        held=dec(getattr(account,"margin",None),"margin",allow_zero=True)
        if str(getattr(account,"currency","")).upper()!="USD":
            raise FundingError("ACCOUNT_CURRENCY_NOT_USD_ORDER_CALC_PROFIT_NOT_USD")
        return dict(core_symbol=core_symbol,broker_symbol=broker_symbol,
                    info=info,tick=tick,account=account,
                    volume_min=mn,volume_step=st,volume_max=mx,
                    contract_size=dec(info.trade_contract_size,"trade_contract_size"),
                    point=dec(getattr(info,"point",None),"point"),
                    bid=bid,ask=ask,equity=equity,margin_free=free,
                    margin_held=held)

    def quote(self,*,trade_id:str,trader_id:str,core_symbol:str,side:str,
              stop_price:D,policy:RiskPolicy,group_id:str="UNCLASSIFIED",
              currently_open_risk:D=D(0),symbol_open_risk:D=D(0),
              trader_open_risk:D=D(0),group_open_risk:D=D(0),
              reserved_margin:D=D(0),broker_trading_allowed:bool=True) -> Quote:
        if not trade_id or not trader_id or side not in ("BUY","SELL") or not group_id:
            raise FundingError("TRADE_IDENTIFIERS_OR_SIDE_INVALID")
        if not broker_trading_allowed:raise FundingError("SERVER_TRADE_DISABLED")
        s=self.snapshot(core_symbol)
        stop=dec(stop_price,"stop_price")
        if side=="BUY" and stop>=s["ask"]:raise FundingError("BUY_STOP_NOT_BELOW_ASK")
        if side=="SELL" and stop<=s["bid"]:raise FundingError("SELL_STOP_NOT_ABOVE_BID")
        order_type=self.client.ORDER_TYPE_BUY if side=="BUY" else self.client.ORDER_TYPE_SELL
        entry=s["ask"] if side=="BUY" else s["bid"]
        c=SYMBOL_CLASSES[core_symbol]
        leverage=INSTANT_MAX_LEVERAGE[c]
        if leverage<=0:raise FundingError("LEVERAGE_INVALID")
        for attr in ("per_entry_usd","max_portfolio_open_stop_usd",
                     "max_symbol_open_stop_usd","max_trader_open_stop_usd",
                     "max_group_open_stop_usd","min_margin_level_pct"):
            dec(getattr(policy,attr),attr)
        for attr in ("slippage_points","adverse_extra_usd_per_lot",
                     "sovereign_floor_usd"):
            dec(getattr(policy,attr),attr,allow_zero=True)
        for v in (currently_open_risk,symbol_open_risk,trader_open_risk,
                  group_open_risk,reserved_margin):
            dec(v,"already_committed",allow_zero=True)
        available_budget=min(
            policy.per_entry_usd,
            policy.max_portfolio_open_stop_usd-currently_open_risk,
            policy.max_symbol_open_stop_usd-symbol_open_risk,
            policy.max_trader_open_stop_usd-trader_open_risk,
            policy.max_group_open_stop_usd-group_open_risk,
            max(D(0),s["equity"]-policy.sovereign_floor_usd-currently_open_risk),
        )
        if available_budget<=0:raise FundingError("RISK_BUDGET_EXHAUSTED")
        # Enter on ask for BUY, bid for SELL. SL adverse slippage in points.
        execution_at_sl=(stop-policy.slippage_points*s["point"]
                         if side=="BUY" else stop+policy.slippage_points*s["point"])
        if execution_at_sl<=0:raise FundingError("ADVERSE_STOP_PRICE_INVALID")
        free=s["margin_free"]-reserved_margin
        if free<=0:raise FundingError("MT5_FREE_MARGIN_EXHAUSTED")
        if s["equity"]<=policy.sovereign_floor_usd:
            raise FundingError("SOVEREIGN_FLOOR_REACHED")
        step=s["volume_step"];mn=s["volume_min"];mx=s["volume_max"]
        # Each lot is priced with the account server: JPY->USD is handled
        # inside order_calc_profit, not by a guessed USDJPY spot rate.
        def evaluate(lots:D)->tuple[D,D,D,D]:
            vol=float(lots)
            p=self.client.order_calc_profit(order_type,s["broker_symbol"],
                vol,float(entry),float(execution_at_sl))
            mar=self.client.order_calc_margin(order_type,s["broker_symbol"],
                vol,float(entry))
            if p is None or mar is None:raise FundingError("MT5_PROFIT_OR_MARGIN_UNAVAILABLE")
            price_stop=max(D(0),-D(str(p)))
            margin=dec(mar,"calculated_margin",allow_zero=True)
            if c=="FOREX":
                fee=lots*D("7") # opening commission; verify account tariff
            elif c=="METAL":
                fee=lots*s["contract_size"]*entry*D("0.000016")
            else:fee=D(0)
            adverse=lots*policy.adverse_extra_usd_per_lot
            return price_stop,fee,adverse,margin
        # Bracket volume with monotone risk, then binary search legal steps.
        unit_pnl,unit_fee,unit_adv,_=evaluate(mn)
        unit_total=unit_pnl+unit_fee+unit_adv
        if unit_total<=0:raise FundingError("INVALID_STOP_RISK_PER_MIN_LOT")
        theoretical=available_budget*mn/unit_total
        maxsteps=int((mx/step).to_integral_value(rounding=ROUND_FLOOR))
        minsteps=int((mn/step).to_integral_value(rounding=ROUND_FLOOR))
        if minsteps<1:raise FundingError("MIN_LOT_NOT_STEP_ALIGNED")
        upper=min(maxsteps,int((theoretical/step).to_integral_value(rounding=ROUND_FLOOR))+1)
        upper=max(minsteps,upper)
        best=None;low=minsteps;high=upper
        while low<=high:
            mid=(low+high)//2;lots=D(mid)*step
            stop_risk,fees,adverse,margin=evaluate(lots)
            total=stop_risk+fees+adverse
            prospective_level=(s["equity"]/(s["margin_held"]+reserved_margin+margin)*D(100)
                if s["margin_held"]+reserved_margin+margin>0 else D("Infinity"))
            ok=(total<=available_budget and margin<=free and
                prospective_level>=policy.min_margin_level_pct and
                s["equity"]-total>=policy.sovereign_floor_usd)
            if ok:best=(lots,stop_risk,fees,adverse,margin,total);low=mid+1
            else:high=mid-1
        if best is None:
            first=evaluate(mn)
            if first[0]+first[1]+first[2]>available_budget:
                raise FundingError("MIN_LOT_RISK_EXCEEDS_BUDGET_INCLUDING_FEES")
            if first[3]>free:raise FundingError("MIN_LOT_MARGIN_EXCEEDS_FREE_MARGIN")
            raise FundingError("MIN_LOT_UNFUNDED_BY_MARGIN_LEVEL_OR_SOVEREIGN_FLOOR")
        lots,stop_risk,fee,adverse,margin,total=best
        if not valid_grid(lots,mn,step,mx):
            raise FundingError("BROKER_VOLUME_GRID_INVALID")
        if lots>theoretical and total>available_budget:
            raise FundingError("INTERNAL_RISK_BUDGET_BREACH")
        return Quote(
            trade_id=trade_id,trader_id=trader_id,core_symbol=core_symbol,
            broker_symbol=s["broker_symbol"],side=side,entry_price=entry,
            stop_price=stop,lots=lots,price_stop_risk_usd=stop_risk,
            commission_usd=fee,adverse_cost_usd=adverse,
            total_stop_risk_usd=total,margin_usd=margin,
            margin_free_before_usd=free,margin_free_after_usd=free-margin,
            equity_before_usd=s["equity"],total_open_risk_after_usd=currently_open_risk+total,
            theoretical_lots=theoretical,contract_size=s["contract_size"],
            volume_step=step,provider_snapshot_status="MT5_LIVE_ACCOUNT_CALC",
            policy_version=policy.policy_version,group_id=group_id,
        )


class AtomicPortfolioReservations:
    """Atomic idempotent allocation against one account; NO broker orders.

    The MT5 account_info() margin_free includes broker-open positions. Our
    local reserved_margin covers authorizations not yet visible there.
    After execution, reconcile ticket/filled volume and remove reservation
    when broker margin is reflected; no exposure can be 'released' twice.
    """
    def __init__(self,calculator:FundedNextMT5Calculator,policy:RiskPolicy):
        self.calculator=calculator;self.policy=policy;self._lock=RLock()
        self._reserved:dict[str,Quote]={}
        self._closed:set[str]=set()
    def authorize(self,*,trade_id:str,trader_id:str,core_symbol:str,side:str,
                  stop_price:D,group_id:str,
                  policy_override:RiskPolicy|None=None)->Quote:
        with self._lock:
            if trade_id in self._closed:raise FundingError("TRADE_ID_ALREADY_CLOSED")
            if trade_id in self._reserved:
                p=self._reserved[trade_id]
                if (trader_id,core_symbol,side,stop_price,group_id)!=(
                   p.trader_id,p.core_symbol,p.side,p.stop_price,p.group_id):
                    raise FundingError("DUPLICATE_TRADE_ID_DIFFERENT_PAYLOAD")
                return p
            values=list(self._reserved.values())
            kw=dict(currently_open_risk=sum((v.total_stop_risk_usd for v in values),D(0)),
                symbol_open_risk=sum((v.total_stop_risk_usd for v in values if v.core_symbol==core_symbol),D(0)),
                trader_open_risk=sum((v.total_stop_risk_usd for v in values if v.trader_id==trader_id),D(0)),
                group_open_risk=sum((v.total_stop_risk_usd for v in values if v.group_id==group_id),D(0)),
                reserved_margin=sum((v.margin_usd for v in values),D(0)))
            q=self.calculator.quote(trade_id=trade_id,trader_id=trader_id,
                    core_symbol=core_symbol,side=side,stop_price=stop_price,
                    group_id=group_id,policy=policy_override or self.policy,**kw)
            self._reserved[trade_id]=q
            return q
    def release(self,trade_id:str)->Quote:
        with self._lock:
            if trade_id not in self._reserved:raise FundingError("UNKNOWN_OR_ALREADY_RELEASED")
            r=self._reserved.pop(trade_id)
            self._closed.add(trade_id)
            return r
    def pending(self)->tuple[Quote,...]:
        with self._lock:return tuple(self._reserved.values())
