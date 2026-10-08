"""CIBO P0 four-motor financial authorization before Trader MT5 order send.

Trader chooses signal/side/SL/TP. CIBO authorizes VOLUME, not signal.
Every engine receives a separate receipt but there is one funded account.
- SIZING computes loss-to-SL and ≤USD3 including opening costs.
- CIBO_COMPOUND releases only realized, unreserved BANK profits.
- PORTFOLIO_COMPOUND authorizes only the correct BANK/CUSHION lane plus
  open risk, concentration, shared margin and unique trade identifier.
- ADAPTIVE_LEVERAGE accepts only actual order_calc_margin MT5 cash capacity.
Never assumes profit/settlement before broker reports a close.
"""
from __future__ import annotations

from dataclasses import dataclass,replace
from decimal import Decimal as D
from threading import RLock
from typing import Any

from qore.infrastructure.trader_lab.cibo_fundednext_mt5_lotage_p0 import (
 AtomicPortfolioReservations,FundedNextMT5Calculator,FundingError,Quote,
 RiskPolicy,
)


@dataclass(frozen=True)
class MotorDecision:
    motor:str
    authorized_usd:D
    approved_lots:D
    reason:str


@dataclass(frozen=True)
class ExecutionAuthorization:
    quote:Quote
    decisions:tuple[MotorDecision,...]
    funding_lane:str
    can_submit_to_broker:bool
    broker_order_sent:bool=False


class CoordinatedCiboCapital:
    """Research authorization: never sends MT5 order, never fabricates fill."""
    def __init__(self,calculator:FundedNextMT5Calculator,
                 policy:RiskPolicy,*,realized_bank_usd:D,
                 realized_cushion_usd:D=D(0),
                 complete_broker_positions_reconciled:bool=False):
        if not isinstance(realized_bank_usd,D) or not isinstance(realized_cushion_usd,D):
            raise FundingError("CAPITAL_MUST_BE_DECIMAL")
        if realized_bank_usd<0 or realized_cushion_usd<0:
            raise FundingError("NEGATIVE_INITIAL_REALIZED_CAPITAL")
        self.policy=policy
        self.complete_broker_positions_reconciled=complete_broker_positions_reconciled
        self.bank=realized_bank_usd
        self.cushion=realized_cushion_usd
        self.ledger=AtomicPortfolioReservations(calculator,policy)
        self._guard=RLock()
        self._mode:dict[str,str]={}
        self._authorizations:dict[str,ExecutionAuthorization]={}
        self._settled:set[str]=set()

    def wallet(self)->dict[str,D]:
        with self._guard:
            pending=self.ledger.pending()
            bank_reserved=sum((p.total_stop_risk_usd for p in pending
                               if self._mode.get(p.trade_id)=="MEDIUM"),D(0))
            attack_reserved=sum((p.total_stop_risk_usd for p in pending
                               if self._mode.get(p.trade_id)=="ATTACK"),D(0))
            return {"BANK_REALIZED":self.bank,"PORTFOLIO_CUSHION_REALIZED":self.cushion,
                    "BANK_RESERVED":bank_reserved,"CUSHION_RESERVED":attack_reserved,
                    "BANK_AVAILABLE":max(D(0),self.bank-bank_reserved-self.policy.sovereign_floor_usd),
                    "CUSHION_AVAILABLE":max(D(0),self.cushion-attack_reserved)}
    def authorize(self,*,trade_id:str,trader_id:str,core_symbol:str,
                  side:str,stop_price:D,group_id:str,mode:str)->ExecutionAuthorization:
        with self._guard:
            if mode not in ("MEDIUM","ATTACK"):raise FundingError("BANK_NEVER_TRADES")
            if trade_id in self._settled:raise FundingError("SETTLED_TRADE_ID_REUSE")
            if trade_id in self._authorizations:
                existing=self._authorizations[trade_id]
                if (existing.funding_lane,existing.quote.trader_id,existing.quote.core_symbol,
                    existing.quote.side,existing.quote.stop_price,existing.quote.group_id)!=(
                    mode,trader_id,core_symbol,side,stop_price,group_id):
                    raise FundingError("DUPLICATE_TRADE_ID_DIFFERENT_REQUEST")
                return existing
            snapshot=self.wallet()
            source=("BANK_AVAILABLE" if mode=="MEDIUM" else "CUSHION_AVAILABLE")
            cash=snapshot[source]
            if cash<=0:raise FundingError("COMPOUND_SOURCE_HAS_NO_REALIZED_UNRESERVED_FUNDS")
            budget=min(self.policy.per_entry_usd,cash)
            # Risk to stop + fees must be funded by its own wallet; never
            # authorize an ATTACK from the sovereign BANK.
            quote=self.ledger.authorize(
                trade_id=trade_id,trader_id=trader_id,
                core_symbol=core_symbol,side=side,stop_price=stop_price,
                group_id=group_id,policy_override=replace(
                    self.policy,per_entry_usd=budget,
                    sovereign_floor_usd=self.policy.sovereign_floor_usd
                )
            )
            self._mode[trade_id]=mode
            out=ExecutionAuthorization(
                quote=quote,funding_lane=mode,
                decisions=(
                    MotorDecision("SIZING",self.policy.per_entry_usd,quote.lots,
                        "SL_PROFIT_AND_OPENING_COST_AND_SLIPPAGE"),
                    MotorDecision("CIBO_COMPOUND",cash,quote.lots,
                        "REALIZED_BANK_CASH_ONLY" if mode=="MEDIUM" else "REALIZED_CUSHION_ONLY"),
                    MotorDecision("COMPOUND_PORTFOLIO",budget,quote.lots,
                        "SINGLE_ATOMIC_WALLET_RISK_SYMBOL_TRADER_GROUP_LIMITS"),
                    MotorDecision("ADAPTIVE_LEVERAGE",quote.margin_free_before_usd,
                        quote.lots,"BROKER_MT5_ORDER_CALC_MARGIN_AND_MARGIN_LEVEL"),
                ),can_submit_to_broker=self.complete_broker_positions_reconciled)
            self._authorizations[trade_id]=out
            return out

    def cancel_unfilled(self,trade_id:str)->None:
        """Failed broker submission: do not count it as a filled order."""
        with self._guard:
            if trade_id not in self._authorizations:
                raise FundingError("UNRESERVED_TRADE")
            self.ledger.release(trade_id)
            del self._authorizations[trade_id]
            self._settled.add(trade_id)

    def close_after_broker_receipt(self,trade_id:str,*,realized_net_usd:D,
                                   broker_execution_proven:bool)->dict[str,D]:
        """Only a proven broker close can change realized BANK/CUSHION."""
        with self._guard:
            if not broker_execution_proven:raise FundingError("BROKER_CLOSE_RECEIPT_MISSING")
            if trade_id not in self._authorizations:
                raise FundingError("UNKNOWN_OR_DUPLICATE_CLOSE")
            if not isinstance(realized_net_usd,D) or not realized_net_usd.is_finite():
                raise FundingError("BAD_BROKER_REALIZED_PNL")
            lane=self._mode[trade_id]
            projected_bank=self.bank+(realized_net_usd if lane=="MEDIUM" else D(0))
            projected_cushion=self.cushion+(realized_net_usd if lane=="ATTACK" else D(0))
            if projected_bank<0 or projected_cushion<0:
                raise FundingError("REALIZED_LOSS_VIOLATES_CAPITAL_SOLVENCY")
            self.ledger.release(trade_id)
            self.bank=projected_bank
            self.cushion=projected_cushion
            del self._authorizations[trade_id]
            self._settled.add(trade_id)
            return self.wallet()
