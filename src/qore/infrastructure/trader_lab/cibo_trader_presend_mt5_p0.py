"""Pre-submit Trader -> CIBO monetary lotage handshake (P0).

Trader owns signal, side, stop and target. CIBO owns the authorized
MT5 order size through four funding engines. This adapter only PREPARES a
request; the authorized Trader execution gateway must send and reconcile.
Never calls order_send, never invents fills. If the broker rejects the
request the reservation MUST be cancelled, then an adjustment reauthorized.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal as D
from typing import Any

from qore.infrastructure.trader_lab.cibo_fundednext_mt5_lotage_p0 import FundingError
from qore.infrastructure.trader_lab.cibo_four_motor_fundednext_p0 import (
 CoordinatedCiboCapital,ExecutionAuthorization,
)


@dataclass(frozen=True)
class TraderSignal:
    decision_id:str
    trader_id:str
    core_symbol:str
    side:str
    stop_loss:D
    take_profit:D
    correlation_group_id:str
    economic_mode:str


@dataclass(frozen=True)
class PreSendEnvelope:
    decision_id:str
    broker_order_request:dict[str,Any]
    authorization:ExecutionAuthorization
    broker_sent:bool=False
    broker_filled:bool=False
    broker_position_ticket:int|None=None


def prepare_trader_order(*,signal:TraderSignal,
                         cibo:CoordinatedCiboCapital,
                         mt5:Any,price_deviation_points:int=10)->PreSendEnvelope:
    if type(price_deviation_points)!=int or price_deviation_points<0:
        raise FundingError("INVALID_PRICE_DEVIATION")
    if signal.side not in ("BUY","SELL"):
        raise FundingError("TRADER_SIDE_INVALID")
    auth=cibo.authorize(
        trade_id=signal.decision_id,
        trader_id=signal.trader_id,
        core_symbol=signal.core_symbol,
        side=signal.side,
        stop_price=signal.stop_loss,
        group_id=signal.correlation_group_id,
        mode=signal.economic_mode)
    q=auth.quote
    tp=signal.take_profit
    if not isinstance(tp,D) or not tp.is_finite() or tp<=0:
        cibo.cancel_unfilled(signal.decision_id)
        raise FundingError("TRADER_TP_INVALID")
    if (signal.side=="BUY" and tp<=q.entry_price) or (signal.side=="SELL" and tp>=q.entry_price):
        cibo.cancel_unfilled(signal.decision_id)
        raise FundingError("TRADER_TP_DIRECTION_INVALID")
    # Respect actual MT5 enum constant; this payload is NOT sent here.
    action=getattr(mt5,"TRADE_ACTION_DEAL",None)
    if action is None:
        cibo.cancel_unfilled(signal.decision_id)
        raise FundingError("MT5_TRADE_ACTION_ENUM_UNAVAILABLE")
    order={
        "action":action,
        "symbol":q.broker_symbol,
        "type":mt5.ORDER_TYPE_BUY if signal.side=="BUY" else mt5.ORDER_TYPE_SELL,
        "volume":float(q.lots),
        "price":float(q.entry_price),
        "sl":float(q.stop_price),
        "tp":float(tp),
        "deviation":price_deviation_points,
        "comment":"CIBO-P0-"+signal.decision_id[:15],
    }
    return PreSendEnvelope(signal.decision_id,order,auth)


def check_broker_execution(*,presend:PreSendEnvelope,order_result:Any,
                           mt5:Any)->dict[str,Any]:
    """No money is recorded unless MT5 explicitly reports an executed deal."""
    retcode=getattr(order_result,"retcode",None)
    deal=getattr(order_result,"deal",None)
    filled_lots=getattr(order_result,"volume",None)
    expected=presend.authorization.quote.lots
    allowed=getattr(mt5,"TRADE_RETCODE_DONE",None)
    if retcode!=allowed or not deal:
        return {"status":"BROKER_ORDER_NOT_FILLED","certified":False,
                "presend_reservation_must_cancel":True}
    if filled_lots is None:
        return {"status":"EXECUTION_VOLUME_MISSING_NEEDS_RECONCILIATION","certified":False}
    actual=D(str(filled_lots))
    if actual!=expected:
        return {"status":"BROKER_VOLUME_MISMATCH_REQUIRES_REPRICING","certified":False,
                "expected_lots":str(expected),"actual_lots":str(actual)}
    if getattr(order_result,"price",None) is None:
        return {"status":"BROKER_EXECUTION_PRICE_MISSING","certified":False}
    if D(str(order_result.price))!=presend.authorization.quote.entry_price:
        # Could be legitimate slippage; recompute stop risk from actual fill
        # and record/correct immediately before certification.
        return {"status":"BROKER_FILL_PRICE_DIFFERS_RISK_RECALC_REQUIRED",
                "certified":False}
    return {"status":"BROKER_FILLED_VOLUME_AND_PRICE_MATCH_AUTHORIZATION",
            "certified":True,"broker_deal":str(deal),
            "executed_lots":str(actual)}
