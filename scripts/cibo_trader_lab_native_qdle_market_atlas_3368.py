#!/usr/bin/env python3
"""Trader Lab: CIBO Native MAX + production QDLE + Market Atlas M5 paper study.

CAUTION: historical Market Atlas OHLC is NOT historical broker bid/ask.
A user-supplied October 2026 MT5 bid/ask snapshot supplies FIXED assumed
spreads for the research scenario; do not claim MT5 fills or true manager PF/DD.
The old/legacy QDLE fee model is never used by this script.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import timedelta, datetime
from decimal import Decimal as D
from pathlib import Path
import hashlib
import heapq
import json
import tempfile

from qore.infrastructure.cibo_four_motor_policy import (
    FourMotorObservation, ReconciledQoreCashflow,
)
from qore.infrastructure.cibo_account_sizing_authority import propose_p0_sizing_vote
from qore.infrastructure.cibo_compound_capital import propose_p0_compound_vote
from qore.infrastructure.cibo_core_compound_portfolio import propose_p0_portfolio_vote
from qore.infrastructure.cibo_marginal_leverage_utility import propose_p0_adaptive_leverage_vote
from qore.infrastructure.cibo_four_motor_qdle_proposal import build_four_motor_qdle_intent
from qore.infrastructure.qdle_stellar_instant_costs import (
    STELLAR_HELP_OPEN_ONLY, estimate_per_lot_fees,
)
from qore.infrastructure.qore_dynamic_lot_engine import (
    QDLE, QDLEError, QDLEAccount, QDLESymbol, QDLEIntent,
    BrokerValuation,
)
from qore.infrastructure.cibo_managed_exit_replay import (
    CiboExitPolicy, CiboManagedTrade, ExecutableOhlcBar,
    ManagedReplayError, replay_cibo_managed_position,
)
from qore.infrastructure.trader_lab.cibo_market_atlas_journey_extractor_v1 import (
    load_raw_m5,
)

INITIAL = D("60")
BROKER_INITIAL = D("2000")
MIN_LOT = D("0.01")
STEP = D("0.01")
FIVE = D("0.05")
ZERO = D("0")
# Observed instantaneous October 2026 MT5 snapshot (NOT historic spread data).
# GBPUSD/EURUSD screenshots show zero at that instant; zero is NOT assumed
# representative of FundedNext execution over 2019-22.
SCREENSHOT_SPREAD = {
    "AUDJPY": D("0.014"), "EURUSD": ZERO,
    "GBPJPY": D("0.023"), "GBPUSD": ZERO,
    "XAUUSD": D("0.38"), "NDX100": D("1.60"),
}
SYMBOL_ALIAS = {"NDX100": "NAS100"}
CONTRACTS = {
    "AUDJPY": D("100000"), "EURUSD": D("100000"),
    "GBPJPY": D("100000"), "GBPUSD": D("100000"),
    "XAUUSD": D("100"), "NDX100": D("10"),
}
TICK = {
    "AUDJPY": D(".001"), "EURUSD": D(".00001"),
    "GBPJPY": D(".001"), "GBPUSD": D(".00001"),
    "XAUUSD": D(".01"), "NDX100": D(".01"),
}
MARGIN = {
    "AUDJPY": {"BUY": D("2318.93"), "SELL": D("2318.67")},
    "EURUSD": {"BUY": D("3735.03"), "SELL": D("3734.77")},
    "GBPJPY": {"BUY": D("4407.40"), "SELL": D("4407.40")},
    "GBPUSD": {"BUY": D("4407.63"), "SELL": D("4407.63")},
    "XAUUSD": {"BUY": D("53637.48"), "SELL": D("53629.68")},
    "NDX100": {"BUY": D("61481.98"), "SELL": D("61478.78")},
}
JPY_USDJPY_ANCHOR = D("158.337")  # 2026 screenshot, NOT historical cross rate.


def _d(v):
    return D(str(v))


class ResearchM5Broker:
    def __init__(self):
        self.value_at = None

    def value(self, instrument, intent, now):
        if self.value_at is None or self.value_at.as_of != now:
            raise QDLEError("stale research M5 valuation")
        return self.value_at

    def check_volume(self, instrument, intent, lots):
        if not (instrument.min_lot <= lots <= instrument.max_lot):
            raise QDLEError("paper volume outside broker grid")
        if lots % instrument.lot_step:
            raise QDLEError("paper volume off broker step")


def executable_bar(m5, spread, symbol):
    half = spread / D(2)
    sha = "sha256:" + hashlib.sha256((
        "ATLAS_M5_FIXED_SPREAD_SHADOW|" + symbol + "|" +
        m5.opened_at.isoformat() + "|" +
        "|".join(str(getattr(m5, k)) for k in ("open", "high", "low", "close"))
        + "|" + str(spread)
    ).encode()).hexdigest()
    return ExecutableOhlcBar(
        opened_at=m5.opened_at, closed_at=m5.closed_at,
        bid_open=m5.open-half, bid_high=m5.high-half,
        bid_low=m5.low-half, bid_close=m5.close-half,
        ask_open=m5.open+half, ask_high=m5.high+half,
        ask_low=m5.low+half, ask_close=m5.close+half,
        evidence_sha256=sha,
    )


def price_usd_per_unit(symbol):
    if symbol in ("AUDJPY", "GBPJPY"):
        return CONTRACTS[symbol] / JPY_USDJPY_ANCHOR
    return CONTRACTS[symbol]


def paper_hash(*parts):
    return "sha256:" + hashlib.sha256(
        "|".join(map(str, parts)).encode("utf-8")
    ).hexdigest()


def publish_paper_account(engine, when, cash, sequence):
    nav=max(ZERO,cash)
    engine.publish_account(QDLEAccount(
        account_id="RESEARCH_CIBO_TRADER_LAB",provider="FundedNext",currency="USD",
        sequence=sequence,as_of=when,
        balance=BROKER_INITIAL+nav-INITIAL,equity=BROKER_INITIAL+nav-INITIAL,
        free_margin=max(ZERO,BROKER_INITIAL+nav-INITIAL),
        qore_unreserved_risk_usd=nav,sovereign_free_source_usd=nav,
        cushion_free_source_usd=ZERO,qore_trading_capital_usd=nav,
    ))


def _mode_quote(row,symbol,side,entry,stop,stop_per_lot,opening_fee,
                as_of,nav,active,flows,account_sequence,engine,broker,published):
    """Causal paper economic snapshot, four REAL producer votes, one QDLE.

    CIBO decision remains historical here: Native MAX cognition NOT certified.
    Market Atlas plus 2026 quote/fees are explicitly incomplete research proxies.
    """
    broker.value_at=BrokerValuation(
        stop_per_lot,MARGIN[symbol][side],as_of,
        "ATLAS_M5_FIXED_2026_BIDASK_PAPER_NOT_BROKER")
    if published.get(symbol)!=as_of:
        engine.publish_symbol(QDLESymbol(
            broker_symbol=symbol,
            aliases=(symbol,"NAS100") if symbol=="NDX100" else (symbol,),
            min_lot=MIN_LOT,max_lot=D("50") if symbol=="XAUUSD" else D("40"),
            lot_step=STEP,directional_volume_limit=ZERO,
            tick_size=TICK[symbol],
            tick_value_loss_usd=TICK[symbol]*price_usd_per_unit(symbol),
            contract_size=CONTRACTS[symbol],
            currency_profit="JPY" if symbol.endswith("JPY") else "USD",
            fee_usd_per_lot=opening_fee,
            fee_provenance="STELLAR_INSTANT_OCT_2026_RESEARCH_PROXY",
            as_of=as_of,tradable=True,
        ))
        published[symbol]=as_of
    held_risk=sum((a["risk"] for a in active.values()),ZERO)
    held_margin=sum((a["margin"] for a in active.values()),ZERO)
    correlated=sum((a["risk"] for a in active.values()
                    if a["symbol"]==symbol or
                    (symbol.endswith("JPY") and a["symbol"].endswith("JPY"))),ZERO)
    trader_risk=sum((a["risk"] for a in active.values()
                     if a["trader"]==row["trader"]),ZERO)
    directional_lots=sum((a["lots"] for a in active.values()
                          if a["symbol"]==symbol and a["side"]==side),ZERO)
    observation=FourMotorObservation(
        request_id=row["signal_fingerprint"],trader_id=row["trader"],
        symbol=symbol,side=side,source_lane="SOVEREIGN_BANK",
        observed_at=as_of,account_sequence=account_sequence,
        broker_evidence_sha256=paper_hash("M5_PROXY",symbol,side,as_of,entry,stop,opening_fee),
        initial_qore_nav_usd=INITIAL,reconciled_cashflows=tuple(flows),
        protected_capital_usd=ZERO,floating_loss_reserve_usd=ZERO,
        risk_reservations_usd=min(max(nav,ZERO),held_risk),
        bank_unreserved_usd=max(nav,ZERO),cushion_unreserved_usd=ZERO,
        total_open_stop_risk_usd=held_risk,correlated_open_stop_risk_usd=correlated,
        trader_open_stop_risk_usd=trader_risk,
        broker_free_margin_usd=max(ZERO,BROKER_INITIAL+nav-INITIAL),
        broker_margin_reservations_usd=held_margin,
        stop_loss_usd_per_lot=stop_per_lot,
        roundtrip_fees_usd_per_lot=opening_fee,
        execution_buffer_usd_per_lot=ZERO,stress_extra_loss_usd_per_lot=ZERO,
        broker_margin_usd_per_lot=MARGIN[symbol][side],
        symbol_max_lots=D("50") if symbol=="XAUUSD" else D("40"),
        provider_direction_max_lots=D("50") if symbol=="XAUUSD" else D("40"),
        open_and_reserved_direction_lots=directional_lots,
        broker_quote_at=as_of,research_proxy_only=True,
        broker_fees_complete=False,broker_profit_valuation_complete=False,
        broker_margin_valuation_complete=False,
    )
    votes=(
        propose_p0_sizing_vote(observation),
        propose_p0_compound_vote(observation,research_disable_legacy_haircut=True),
        propose_p0_adaptive_leverage_vote(observation,research_use_full_free_margin=True),
        propose_p0_portfolio_vote(observation,research_disable_legacy_quotas=True),
    )
    frac=_d(row["cibo_max_native_requested_risk_fraction_of_nav"])
    if not ZERO<=frac<=FIVE:
        raise ValueError("native historical instruction exceeds 5pct limit")
    intent=build_four_motor_qdle_intent(
        observation=observation,votes=votes,entry_price=entry,stop_price=stop)
    intent=replace(intent,requested_risk_usd=max(nav,ZERO)*frac)
    result=engine.reserve_for_trader(intent,now=as_of)
    return result,[vote.payload() for vote in votes]


def simulate(manifest, quotes, roots, *, workdir, max_bars=3200):
    source=manifest["opportunities"]
    if len(source)!=3368 or len(set(x["signal_fingerprint"] for x in source))!=3368:
        raise ValueError("Trader Lab requires 3368 unique sealed source opportunities")
    decision_rows=quotes["decisions"]
    if (len(decision_rows)!=3368 or quotes.get("fee_model")!=STELLAR_HELP_OPEN_ONLY
        or quotes.get("native_cibo_bank_medium_attack_instructions_consumed")!=3368
        or quotes.get("real_fundednext_fills")!=0):
        raise ValueError("requires only fresh Native + UPDATED Stellar QDLE scenario")
    decisions={r["signal_fingerprint"]:r for r in decision_rows}
    origins={r["signal_fingerprint"]:r for r in source}
    if set(decisions)!=set(origins) or len(decisions)!=len(decision_rows):
        raise ValueError("CIBO/Trader source identity mismatch")
    atlas={}
    metadata={}
    for symbol in SCREENSHOT_SPREAD:
        atlas_symbol=SYMBOL_ALIAS.get(symbol,symbol)
        corpus, provenance=load_raw_m5(roots[symbol])
        if corpus.symbol!=atlas_symbol:
            raise ValueError("Atlas source symbol drift: "+symbol)
        atlas[symbol]=(corpus.bars,tuple(b.opened_at for b in corpus.bars))
        metadata[symbol]=provenance
    chronological=sorted(decision_rows,key=lambda r:(r["at"],r["signal_fingerprint"]))
    counts=Counter()
    per_mode=defaultdict(Counter)
    per_symbol=defaultdict(Counter)
    active={}
    closings=[]
    rows=[]
    closed=[]
    bank=INITIAL
    peak=INITIAL
    max_dd=ZERO
    net_wins=ZERO
    net_losses=ZERO
    opened_fees=ZERO
    total_lots=ZERO
    worst_intratrade = ZERO
    sequence=0
    flows=[]  # paper cash events, NOT authenticated broker settlements

    def mark_cash():
        nonlocal peak,max_dd
        peak=max(peak,bank)
        if peak>ZERO:
            max_dd=max(max_dd,(peak-bank)/peak)

    def settle(t):
        nonlocal bank,net_wins,net_losses,worst_intratrade
        while closings and closings[0][0] <= t:
            exit_time,sid,gross,net,mode,symbol,reason,worst=heapq.heappop(closings)
            if sid not in active:
                raise ValueError("duplicate closing")
            trade=active.pop(sid)
            engine.finish_research_reservation(
                request_id=sid,
                event_id=paper_hash("CLOSED",sid,exit_time.isoformat(),gross),
                reason="PAPER_CLOSED",now=exit_time,
            )
            flows.append(ReconciledQoreCashflow(
                sid+":paper_settlement",exit_time,gross,
                paper_hash("PAPER_SETTLEMENT",sid,exit_time.isoformat(),gross),True,
            ))
            bank+=gross  # OPEN fee was already debited at entry
            net_wins+=max(net,ZERO)
            net_losses+=max(-net,ZERO)
            worst_intratrade=min(worst_intratrade,worst)
            per_mode[mode]["settled"]+=1
            per_symbol[symbol]["settled"]+=1
            counts["settled"]+=1
            mark_cash()
            closed.append({
                "signal_fingerprint":sid,"mode":mode,"symbol":symbol,
                "entry_at":trade["opened_at"].isoformat(),
                "exit_at":exit_time.isoformat(),"lots":str(trade["lots"]),
                "gross_usd":str(gross),"commission_open_usd":str(trade["fee"]),
                "commission_close_usd":"0","net_usd":str(net),
                "exit_reason":reason,"bank_after_close_usd":str(bank),
            })
    with tempfile.TemporaryDirectory(prefix="cibo-trader-lab-qdle-",
                                     dir=workdir) as tmp:
        td=Path(tmp)
        broker=ResearchM5Broker()
        engine=QDLE(td/"research-account.sqlite",broker,
                    strict_live_fee_evidence=False,strict_four_motor_evidence=False)
        published_symbols={}
        for idx, d in enumerate(chronological):
            sid=d["signal_fingerprint"]
            at=datetime.fromisoformat(d["at"])
            settle(at)
            symbol=d["symbol"]
            original=origins[sid]["trader_opportunity"]
            mode=d["cibo_max_native_management_mode"]
            side="BUY" if original["side"]=="long" else "SELL"
            per_mode[mode]["received"]+=1
            per_symbol[symbol]["received"]+=1
            counts["received"]+=1
            r={"signal_fingerprint":sid,"symbol":symbol,"mode":mode,
               "signal_at":d["signal_at"],"qdle_at":at.isoformat()}
            sequence+=1
            publish_paper_account(engine,at,bank,sequence)

            def reject_unquotable(reason):
                refusal=engine.reject_research_unquotable(
                    request_id=sid,trader_id=d["trader"],
                    symbol=symbol,side=side,reason=reason,now=at,
                )
                counts["qdle_assessed"]+=1
                r["qdle_lots"]=str(refusal.lots)
                r["qdle_state"]=refusal.state
                r["qdle_binding_limits"]=list(refusal.binding_limits)
                r["four_motor_voted_count"]=0

            if bank<=ZERO:
                counts["nav_exhausted"]+=1
                r["status"]="NO_QORE_NAV";reject_unquotable(r["status"])
                rows.append(r);continue
            bars,opened=atlas[symbol]
            pos=bisect_left(opened,at)
            if pos>=len(opened) or opened[pos] > at+timedelta(minutes=5):
                counts["no_executable_atlas_entry"]+=1
                r["status"]="NO_ATLAS_M5_ENTRY";reject_unquotable(r["status"])
                rows.append(r);continue
            first=bars[pos]
            midpoint=first.open
            spread=SCREENSHOT_SPREAD[symbol]
            half=spread/D(2)
            entry=midpoint+half if side=="BUY" else midpoint-half
            original_entry=_d(original["intended_entry"])
            dist=abs(original_entry-_d(original["stop_loss"]))
            econ_dist=abs(original_entry-_d(d["cibo_manager_stop_proposed"]))
            target_dist=abs(original_entry-_d(original["take_profit"]))
            if not (dist>ZERO and ZERO<econ_dist<=dist and target_dist>half):
                counts["invalid_original_geometry"]+=1
                r["status"]="INVALID_GEOMETRY";reject_unquotable(r["status"])
                rows.append(r);continue
            direction=D(1) if side=="BUY" else D(-1)
            # Cross-side stop/target at the historical M5 mid ± fixed observed
            # spread. Do not convert today's absolute price into 2019 price.
            stop_struct=midpoint-direction*dist
            stop_econ=midpoint-direction*econ_dist
            target=midpoint+direction*target_dist
            if (side=="BUY" and not (stop_struct<=stop_econ<entry<target)) or (
                side=="SELL" and not (target<entry<stop_econ<=stop_struct)
            ):
                counts["invalid_cross_side_geometry"]+=1
                r["status"]="INVALID_CROSS_SIDE_GEOMETRY";reject_unquotable(r["status"])
                rows.append(r);continue
            unit=price_usd_per_unit(symbol)
            tariff=estimate_per_lot_fees(
                symbol,entry_price=entry,contract_size=CONTRACTS[symbol],
                model=STELLAR_HELP_OPEN_ONLY,
            )
            risk_per_lot=abs(entry-stop_econ)*unit
            try:
                q,votes=_mode_quote(
                    d,symbol,side,entry,stop_econ,risk_per_lot,
                    tariff.total_usd,at,bank,active,flows,sequence,
                    engine,broker,published_symbols,
                )
            except (QDLEError,ValueError) as exc:
                raise RuntimeError(
                    "P0 four-motor/QDLE attempt cannot silently disappear: "+sid
                ) from exc
            counts["qdle_assessed"]+=1
            counts["four_motor_voted"]+=4
            r["qdle_state"]=q.state
            r["qdle_binding_limits"]=list(q.binding_limits)
            r["four_motor_voted_count"]=len(votes)
            r["four_motor_receipts"]=votes
            r["qdle_lots"]=str(q.lots)
            r["qdle_all_in_risk"]=str(q.total_risk_usd)
            r["bank_at_entry"]=str(bank)
            if q.lots<=ZERO:
                counts["qdle_no_lot"]+=1
                per_mode[mode]["unfundable"]+=1
                r["status"]="QDLE_NO_FINANCEABLE_LOT";rows.append(r);continue
            counts["qdle_quote_positive"]+=1
            per_mode[mode]["quoted"]+=1
            r["qdle_quote_state"]=q.state
            if q.total_risk_usd>bank*_d(d["cibo_max_native_requested_risk_fraction_of_nav"]):
                raise ValueError("mode risk cap breached by QDLE")
            r["price_path_source"]="ATLAS_M5_FIXED_SPREAD_SYNTHETIC_EXECUTABLE_SIDES"
            # Build consecutive 5-min synthetic bid/ask until a natural market
            # discontinuity; never create candles across a missing time period.
            path=[]
            horizon=first.opened_at+timedelta(days=14)
            for m5 in bars[pos:pos+max_bars]:
                if m5.opened_at>=horizon: break
                if path and path[-1].closed_at != m5.opened_at: break
                try:path.append(executable_bar(m5,spread,symbol))
                except ManagedReplayError:break
            try:
                trade=CiboManagedTrade(
                    signal_id=sid,symbol=symbol,side=side,
                    entry_at=first.opened_at,entry_price=entry,
                    trader_structural_stop_price=stop_struct,
                    economic_stop_price=stop_econ,trader_take_profit_price=target,
                    lots=q.lots,min_lot=MIN_LOT,lot_step=STEP,
                    price_pnl_usd_per_lot_per_unit=unit,
                    roundtrip_commission_usd_per_lot=tariff.total_usd,
                    maximum_all_in_risk_usd=bank*_d(d["cibo_max_native_requested_risk_fraction_of_nav"]),
                )
                policy=CiboExitPolicy(**{
                    k:_d(v) for k,v in d["cibo_max_native_proposed_exit_management"].items()
                })
                outcome=replay_cibo_managed_position(trade,tuple(path),policy=policy)
            except (ManagedReplayError, ValueError, ArithmeticError) as exc:
                counts["exit_policy_error"]+=1
                r["status"]="EXIT_POLICY_ERROR";r["error"]=str(exc)[:150]
                engine.finish_research_reservation(
                    request_id=sid,
                    event_id=paper_hash("PAPER_PATH_INVALID",sid,at.isoformat(),str(exc)),
                    reason="PAPER_PATH_INVALID",now=at,
                )
                rows.append(r);continue
            fee=q.lots*tariff.opening_usd
            # Research entry occurs before outcome is known; missing future
            # prices DO NOT cause a fake settlement nor restore an opening fee.
            bank-=fee
            flows.append(ReconciledQoreCashflow(
                sid+":paper_open_fee",at,-fee,
                paper_hash("PAPER_OPEN_FEE",sid,at.isoformat(),fee),True,
            ))
            opened_fees+=fee
            total_lots+=q.lots
            mark_cash()
            active[sid]={
                "risk":q.total_risk_usd,"margin":q.margin_usd,
                "lots":q.lots,"fee":fee,"opened_at":first.opened_at,
                "mode":mode,"symbol":symbol,
                "trader":d["trader"],"side":side,
            }
            r["status"]="PAPER_OPEN"
            r["paper_entry_at"]=first.opened_at.isoformat()
            r["paper_entry_price"]=str(entry)
            r["paper_open_fee_usd"]=str(fee)
            r["path_bars_considered"]=len(path)
            r["managed_exit_status"]=outcome.status
            counts["paper_open"]+=1
            per_mode[mode]["opened"]+=1
            if outcome.status=="SHADOW_SETTLED":
                gross=outcome.gross_pnl_usd_proxy
                net=gross-fee
                if outcome.exit_at < first.opened_at:
                    raise ValueError("exit chronology violation")
                heapq.heappush(closings,(
                    outcome.exit_at,sid,gross,net,mode,symbol,
                    outcome.exit_reason,outcome.intratrade_worst_pnl_usd_proxy or ZERO,
                ))
                r["scheduled_paper_close_at"]=outcome.exit_at.isoformat()
                r["exit_policy_actions"]=list(outcome.actions)
            else:
                counts["unresolved_after_paper_open"]+=1
                r["status"]="PAPER_OPEN_UNRESOLVED_NO_EXIT_PATH"
            rows.append(r)
            if (idx+1)%500==0:
                print("TRADER_LAB_CIBO_QDLE_PROGRESS",idx+1,
                      "closed",counts["settled"],"paper_open",counts["paper_open"],
                      "QORE_cash",str(bank),flush=True)
        settle(datetime.max.replace(tzinfo=chronological[-1] and datetime.fromisoformat(chronological[-1]["at"]).tzinfo))
    if counts["received"]!=3368 or counts["qdle_assessed"]!=3368:
        raise ValueError("universal QDLE assessment cardinality mismatch")
    winners=sum(_d(x["net_usd"])>ZERO for x in closed)
    losing=sum(_d(x["net_usd"])<ZERO for x in closed)
    final_complete=(not active and counts["no_executable_atlas_entry"]==0
                    and counts["exit_policy_error"]==0)
    return {
        "schema":"qore.trader-lab.cibo-native-qdle-market-atlas-fixed-spread.v1",
        "research_only":True,"broker_fills":0,"certified":False,
        "financial_certification":"REJECTED_COUNTERFACTUAL_FIXED_2026_SPREAD",
        "execution_data":"HISTORICAL_MARKET_ATLAS_M5_OHLC_PLUS_USER_2026_SPREAD_FIXED",
        "bid_ask_verified_2019_2022":False,
        "commission_model":"FUNDEDNEXT_STELLAR_INSTANT_OPEN_ONLY",
        "legacy_fee_model_used":False,
        "usd_jpy_cross_historical":False,
        "usd_jpy_fixed_2026_anchor":str(JPY_USDJPY_ANCHOR),
        "spreads_fixed_by_symbol":{k:str(v) for k,v in SCREENSHOT_SPREAD.items()},
        "atlas_provenance":metadata,
        "signal_count":3368,"counts":dict(counts),
        "research_persistent_qdle_single_account":True,
        "research_recomputed_four_motor_votes":counts["four_motor_voted"],
        "full_native_max_cognition_recomputed":False,
        "research_account_nav_is_cash_not_equity_mtm":True,
        "by_mode":{k:dict(v) for k,v in per_mode.items()},
        "by_symbol":{k:dict(v) for k,v in per_symbol.items()},
        "qore_initial_nav_usd":str(INITIAL),
        "shadow_paper_cash_balance_after_known_events_usd":str(bank),
        "shadow_projected_closed_cash_max_dd_pct":str(max_dd*100),
        "shadow_projected_closed_cash_max_dd_usd":None,
        "shadow_projected_settled_profit_factor":str(net_wins/net_losses) if net_losses>ZERO else None,
        "shadow_projected_settled_win_rate_pct":str(D(winners)*100/D(len(closed))) if closed else None,
        "shadow_projected_settled_net_pnl_usd":str(sum((_d(x["net_usd"]) for x in closed),ZERO)),
        "shadow_open_fees_debited_usd":str(opened_fees),
        "shadow_total_lots_opened":str(total_lots),
        "shadow_profitable_settled_trades":winners,
        "shadow_losing_settled_trades":losing,
        "shadow_max_single_trade_adverse_usd":str(worst_intratrade),
        "open_positions_missing_full_path":len(active),
        "full_cibo_managed_final_nav_usd":str(bank) if final_complete else None,
        "full_cibo_managed_drawdown_pct":None,
        "full_cibo_managed_profit_factor":None,
        "full_cibo_manager_risk_certified":False,
        "closed_trades":closed,"signal_decisions":rows,
        "limitations":[
            "Snapshot spread from October 2026 is not historical 2019-2022 spread",
            "Atlas M5 unknown bid/ask side; executable bid/ask modeled via constant offset",
            "USDJPY uses October 2026 conversion anchor, not historical cross rate",
            "Singleton research QDLE holds and releases paper risk/margin on modeled terminal events; never an MT5 fill",
            "Four new economic motor proposals per quotable signal, not recycled NAV60 caps",
            "Unquotable signals have typed QDLE rejection but no four-motor votes; full P0 coverage gate still FAILED",
            "Native MAX entry instruction and exit policy are still historical presets: cognition gate FAILED",
            "Research-only broker economics (2019-22 M5 plus 2026 fixed quotes), completeness flags FALSE",
            "Paper fill next eligible M5 open; original LIMIT order fills not reconstructed",
            "Incomplete market paths kept OPEN and reserve funds, no fabricated result",
            "Intratrade global portfolio MTM drawdown cannot be certified",
            "Historical broker actual swap, margin, slippage and gap path not verified",
            "No MT5 real fills and no LIVE operation",
        ],
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",required=True,type=Path)
    p.add_argument("--native-stellar-qdle",required=True,type=Path)
    p.add_argument("--atlas-root",action="append",required=True)
    p.add_argument("--workdir",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--max-bars",type=int,default=3200)
    args=p.parse_args()
    roots={}
    for v in args.atlas_root:
        s,_,loc=v.partition("=")
        if not loc or s not in SCREENSHOT_SPREAD or s in roots:
            p.error("exact six SYMBOL=ATLAS_ROOT required")
        roots[s]=Path(loc)
    if set(roots)!=set(SCREENSHOT_SPREAD):
        p.error("all six Market Atlas M5 roots required")
    if args.max_bars<1 or args.max_bars>20000:
        p.error("max bars out of bounded research range")
    args.workdir.mkdir(parents=True,exist_ok=True)
    result=simulate(json.loads(args.manifest.read_text()),
                    json.loads(args.native_stellar_qdle.read_text()),
                    roots,workdir=args.workdir,max_bars=args.max_bars)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("TRADER_LAB_NATIVE_QDLE_FIXED_SPREAD_RESULT",json.dumps({
        k:result[k] for k in (
            "signal_count","counts","shadow_paper_cash_balance_after_known_events_usd",
            "shadow_projected_closed_cash_max_dd_pct",
            "shadow_projected_settled_profit_factor",
            "shadow_projected_settled_win_rate_pct",
            "shadow_projected_settled_net_pnl_usd",
            "open_positions_missing_full_path","full_cibo_managed_final_nav_usd",
            "full_cibo_managed_drawdown_pct",
        )
    },sort_keys=True),flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
