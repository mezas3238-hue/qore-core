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
from datetime import timedelta, datetime
from decimal import Decimal as D
from pathlib import Path
import hashlib
import heapq
import json
import sqlite3
import tempfile

from qore.infrastructure.qdle_stellar_instant_costs import (
    STELLAR_HELP_OPEN_ONLY, estimate_per_lot_fees,
)
from qore.infrastructure.qore_dynamic_lot_engine import (
    QDLE, QDLEError, QDLEAccount, QDLESymbol, QDLEIntent,
    BrokerValuation, QDLEResult,
)
from qore.infrastructure.qdle_paper_book import PaperQDLE
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


class PaperQdleSession:
    """ONE PAPER account QDLE and SQLite reservation ledger for the entire run.

    Synthetic paper ticket IDs are NEVER MT5 tickets and cannot be used for
    LIVE. Every fill is confirmed exclusively by this research simulator.
    The normal QDLE reservation -> fill -> covered-position reconciliation
    protocol is exercised instead of resetting QDLE for each opportunity.
    This is not, by itself, a certified CIBO cognition or MTM engine.
    """

    def __init__(self, database: Path):
        self.broker = ResearchM5Broker()
        # Only the canonical #745 PaperQDLE owns reservations and PAPER fills.
        self.qdle = PaperQDLE(database, self.broker)
        self.sequence = 0
        self.last_symbol_at = {}

    def publish_snapshot(self, *, at, nav, active):
        """Publish economic resources, leaving PAPER holds inside QDLE.

        Never double-subtract active simulated risk/margin from this snapshot:
        PAPER_OPEN rows in the same SQLite ledger carry the commitments.
        """
        self.sequence += 1
        nav = max(nav, ZERO)
        broker_equity_proxy = max(BROKER_INITIAL + nav - INITIAL, ZERO)
        self.qdle.publish_account(QDLEAccount(
            account_id="RESEARCH_CIBO_TRADER_LAB",
            provider="FundedNext", currency="USD",
            sequence=self.sequence, as_of=at,
            balance=broker_equity_proxy, equity=broker_equity_proxy,
            free_margin=broker_equity_proxy,
            qore_unreserved_risk_usd=nav,
            sovereign_free_source_usd=nav,
            cushion_free_source_usd=ZERO,
            qore_trading_capital_usd=nav,
            # Synthetic PAPER fills are NOT verified broker positions.
            positions=(), covered_fill_tickets=(),
        ))
        return self.sequence

    def publish_symbol(self, *, at, symbol, fee):
        previous = self.last_symbol_at.get(symbol)
        if previous is not None and at < previous[0]:
            raise QDLEError("noncausal symbol timestamp in PAPER QDLE")
        if previous is not None and at == previous[0]:
            if fee != previous[1]:
                raise QDLEError("conflicting fee for same-symbol same-time PAPER quote")
            return
        self.qdle.publish_symbol(QDLESymbol(
            broker_symbol=symbol,
            aliases=(symbol, "NAS100") if symbol == "NDX100" else (symbol,),
            min_lot=MIN_LOT,
            max_lot=D("50") if symbol == "XAUUSD" else D("40"),
            lot_step=STEP, directional_volume_limit=ZERO,
            tick_size=TICK[symbol],
            tick_value_loss_usd=TICK[symbol] * price_usd_per_unit(symbol),
            contract_size=CONTRACTS[symbol],
            currency_profit="JPY" if symbol.endswith("JPY") else "USD",
            fee_usd_per_lot=fee,
            fee_provenance="FUNDEDNEXT_STELLAR_INSTANT_FAQ_ACCOUNT_SAMPLE_2026_PROXY",
            as_of=at, tradable=True,
        ))
        self.last_symbol_at[symbol] = (at, fee)

    def paper_fill(self, *, sid, at, nav, active):
        """Persist a synthetic fill WITHOUT calling broker receipt APIs."""
        ticket=self.qdle.paper_fill(sid, at)
        if ticket != "PAPER:"+sid:
            raise QDLEError("invalid canonical PAPER ticket after fill")

    def paper_settle(self, *, sid, at, gross):
        """Persist one PAPER settlement; never attribute it to an MT5 deal."""
        self.qdle.paper_settle(sid, at, gross)

    def paper_no_fill(self, *, sid, at, reason):
        """Release a held PAPER quote without a broker rejection."""
        self.qdle.paper_cancel(sid, at, reason)

    def paper_unassessable(self, *, sid, reason, at, nav, active):
        seq=self.publish_snapshot(at=at, nav=nav, active=active)
        self.qdle.paper_unassessable(sid, at, reason)
        return QDLEResult(
            sid, "RESEARCH_UNASSESSABLE_NOT_QUOTED", "", ZERO,
            ZERO, ZERO, ZERO, ZERO, seq, (reason,),
            "Canonical PaperQDLE unpriceable event, never broker quote",
        )



def _mode_quote(row, symbol, side, entry, stop, stop_per_lot,
                opening_fee, as_of, nav, active, session):
    """Physical QDLE quote with ONE durable PAPER ledger.

    Caps remain historical rescalings, NOT independent fresh motor votes.
    The experiment stays incomplete until genuine four-motor recomputation.
    """
    session.broker.value_at = BrokerValuation(
        stop_per_lot, MARGIN[symbol][side], as_of,
        "TRADER_LAB_ATLAS_M5_CEO_2026_FIXED_SPREAD_RESEARCH",
    )
    sequence = session.publish_snapshot(at=as_of, nav=nav, active=active)
    session.publish_symbol(at=as_of, symbol=symbol, fee=opening_fee)
    caps = row["four_engine_caps_usd"]
    scale = max(nav, ZERO) / INITIAL
    fraction = _d(row["cibo_max_native_requested_risk_fraction_of_nav"])
    if fraction not in (D("0.0125"), D("0.025"), D("0.05")):
        raise ValueError("native risk mode fraction invalid")
    sid = row["signal_fingerprint"]
    free_margin = max(BROKER_INITIAL + nav - INITIAL, ZERO)
    intent = QDLEIntent(
        request_id=sid, trader_id=row["trader"], symbol=symbol, side=side,
        entry_price=entry, stop_price=stop,
        requested_risk_usd=max(nav, ZERO) * fraction,
        sizing_cap_usd=min(max(nav, ZERO) * FIVE, _d(caps["SIZING"]) * scale),
        cibo_compound_cap_usd=min(max(nav, ZERO) * FIVE,
                                  _d(caps["CIBO_COMPOUND"]) * scale),
        portfolio_cap_usd=min(max(nav, ZERO) * FIVE,
                               _d(caps["PORTFOLIO_COMPOUND_AVAILABLE_SOURCE"]) * scale),
        leverage_cap_lots=max(ZERO, _d(row["leverage_max_lots"])),
        margin_cap_usd=min(free_margin, _d(row["leverage_margin_budget_usd"])),
        source_lane="SOVEREIGN_BANK", slippage_usd_per_lot=ZERO,
        expected_account_sequence=sequence,
    )
    return session.qdle.reserve_for_trader(intent, now=as_of)

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
            session.paper_settle(sid=sid, at=exit_time, gross=gross)
            trade=active.pop(sid)
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
        session=PaperQdleSession(td / 'account-qdle.sqlite')
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
            if bank<=ZERO:
                counts["nav_exhausted"]+=1
                r["status"]="NO_QORE_NAV"
                unquoted=session.paper_unassessable(
                    sid=sid, reason="NO_QORE_NAV", at=at, nav=bank, active=active)
                r["qdle_assessment_state"]=unquoted.state
                r["qdle_lots"]="0"
                r["qdle_physical_quote_computed"]=False
                r["qdle_physical_assessment"]={
                    "request_id":sid,"state":unquoted.state,"lots":"0",
                    "account_sequence":unquoted.account_sequence,
                    "binding_limits":list(unquoted.binding_limits),
                    "physical_quote_computed":False,
                }
                counts["qdle_unassessable"]+=1
                rows.append(r);continue
            bars,opened=atlas[symbol]
            pos=bisect_left(opened,at)
            if pos>=len(opened) or opened[pos] > at+timedelta(minutes=5):
                counts["no_executable_atlas_entry"]+=1
                r["status"]="NO_ATLAS_M5_ENTRY"
                unquoted=session.paper_unassessable(
                    sid=sid, reason="NO_ATLAS_M5_ENTRY", at=at, nav=bank, active=active)
                r["qdle_assessment_state"]=unquoted.state
                r["qdle_lots"]="0"
                r["qdle_physical_quote_computed"]=False
                r["qdle_physical_assessment"]={
                    "request_id":sid,"state":unquoted.state,"lots":"0",
                    "account_sequence":unquoted.account_sequence,
                    "binding_limits":list(unquoted.binding_limits),
                    "physical_quote_computed":False,
                }
                counts["qdle_unassessable"]+=1
                rows.append(r);continue
            first=bars[pos]
            if first.opened_at > at:
                # The next M5 OPEN is a future paper fill candidate, never a
                # predecision QDLE market observation or cognitive evidence.
                counts["future_entry_price_unobservable"]+=1
                r["status"]="FUTURE_M5_PRICE_NOT_CAUSALLY_OBSERVABLE"
                missing=session.paper_unassessable(
                    sid=sid,reason="FUTURE_M5_PRICE_NOT_CAUSALLY_OBSERVABLE",
                    at=at,nav=bank,active=active)
                r["qdle_assessment_state"]=missing.state
                r["qdle_lots"]="0"
                r["qdle_physical_quote_computed"]=False
                r["qdle_physical_assessment"]={
                    "request_id":sid,"state":missing.state,"lots":"0",
                    "account_sequence":missing.account_sequence,
                    "binding_limits":list(missing.binding_limits),
                    "physical_quote_computed":False,
                }
                counts["qdle_unassessable"]+=1
                rows.append(r);continue
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
                r["status"]="INVALID_GEOMETRY"
                unquoted=session.paper_unassessable(
                    sid=sid, reason="INVALID_ORIGINAL_GEOMETRY", at=at, nav=bank, active=active)
                r["qdle_assessment_state"]=unquoted.state
                r["qdle_lots"]="0"
                r["qdle_physical_quote_computed"]=False
                r["qdle_physical_assessment"]={
                    "request_id":sid,"state":unquoted.state,"lots":"0",
                    "account_sequence":unquoted.account_sequence,
                    "binding_limits":list(unquoted.binding_limits),
                    "physical_quote_computed":False,
                }
                counts["qdle_unassessable"]+=1
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
                r["status"]="INVALID_CROSS_SIDE_GEOMETRY"
                unquoted=session.paper_unassessable(
                    sid=sid, reason="INVALID_CROSS_SIDE_GEOMETRY", at=at, nav=bank, active=active)
                r["qdle_assessment_state"]=unquoted.state
                r["qdle_lots"]="0"
                r["qdle_physical_quote_computed"]=False
                r["qdle_physical_assessment"]={
                    "request_id":sid,"state":unquoted.state,"lots":"0",
                    "account_sequence":unquoted.account_sequence,
                    "binding_limits":list(unquoted.binding_limits),
                    "physical_quote_computed":False,
                }
                counts["qdle_unassessable"]+=1
                rows.append(r);continue
            unit=price_usd_per_unit(symbol)
            tariff=estimate_per_lot_fees(
                symbol,entry_price=entry,contract_size=CONTRACTS[symbol],
                model=STELLAR_HELP_OPEN_ONLY,
            )
            risk_per_lot=abs(entry-stop_econ)*unit
            held_risk=sum(x["risk"] for x in active.values())
            held_margin=sum(x["margin"] for x in active.values())
            try:
                q=_mode_quote(d,symbol,side,entry,stop_econ,risk_per_lot,
                              tariff.total_usd,at,bank,
                              active,session)
                sequence+=1
            except (QDLEError,ValueError) as exc:
                counts["qdle_rejected"]+=1
                r["status"]="QDLE_ERROR"
                r["error"]=str(exc)[:120]
                rows.append(r);continue
            r["qdle_assessment_state"]=q.state
            r["qdle_physical_quote_computed"]=True
            r["qdle_physical_assessment"]={
                "request_id":sid,"state":q.state,"lots":str(q.lots),
                "account_sequence":q.account_sequence,
                "binding_limits":list(q.binding_limits),
                "all_in_stop_risk_usd":str(q.total_risk_usd),
                "margin_usd":str(q.margin_usd),
                "physical_quote_computed":True,
            }
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
                session.paper_no_fill(sid=sid, at=first.opened_at,
                                      reason="EXIT_POLICY_ERROR")
                rows.append(r);continue
            fee=q.lots*tariff.opening_usd
            # Research entry occurs before outcome is known; missing future
            # prices DO NOT cause a fake settlement nor restore an opening fee.
            bank-=fee
            opened_fees+=fee
            total_lots+=q.lots
            mark_cash()
            active[sid]={
                "risk":q.total_risk_usd,"margin":q.margin_usd,
                "lots":q.lots,"fee":fee,"opened_at":first.opened_at,
                "mode":mode,"symbol":symbol,"side":side,
                "paper_ticket":"PAPER:"+sid,
            }
            session.paper_fill(sid=sid,at=first.opened_at,nav=bank,active=active)
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

        # Export the durable per-account QDLE PAPER journal before the isolated
        # SQLite directory is disposed. Missing/unpriceable != viable zero lots.
        with sqlite3.connect(session.qdle.path) as db:
            quoted_rows = db.execute(
                "SELECT request_id,state,lots,risk,margin,snapshot_seq FROM reservations ORDER BY request_id"
            ).fetchall()
            no_quote_rows = db.execute(
                "SELECT request_id,reason,observed_at FROM paper_unassessable ORDER BY request_id"
            ).fetchall()
            journal_events = dict(db.execute(
                "SELECT event,COUNT(*) FROM audit GROUP BY event ORDER BY event"
            ).fetchall())
            # Preserve an auditable copy beyond this run's temporary SQLite.
            # SQLite backup is consistent and cannot mutate the live account.
            export_db=Path(workdir)/"cibo-paper-qdle-account-ledger.sqlite"
            with sqlite3.connect(export_db) as archived:
                db.backup(archived)
        account_receipts = [
            {"signal_fingerprint":sid,"state":state,"lots":lots,
             "risk_usd":risk,"margin_usd":margin,"account_sequence":seq,
             "physically_quoted":True}
            for sid,state,lots,risk,margin,seq in quoted_rows
        ] + [
            {"signal_fingerprint":sid,"state":"RESEARCH_UNASSESSABLE_NOT_QUOTED",
             "reason":reason,"account_sequence":None,"observed_at":at,
             "physically_quoted":False,"lots":"0"}
            for sid,reason,at in no_quote_rows
        ]
        account_receipts.sort(key=lambda r:r["signal_fingerprint"])
        journal_ids=[r["signal_fingerprint"] for r in account_receipts]
        journal_complete=(len(journal_ids)==3368
                          and len(set(journal_ids))==3368
                          and set(journal_ids)==set(origins))
        paper_states=dict(Counter(r["state"] for r in account_receipts))
        if paper_states.get("PAPER_SETTLED",0)!=len(closed):
            raise ValueError("PAPER QDLE settled ledger diverged from closed trades")
        if paper_states.get("PAPER_FILLED",0)!=len(active):
            raise ValueError("canonical PAPER QDLE filled ledger diverged from active trades")
        session.qdle.assert_paper_positions(active)
        canonical_coverage=session.qdle.paper_coverage()
        canonical_digest=session.qdle.paper_audit_digest()
        if canonical_coverage["received_accounted"]!=3368:
            raise ValueError("canonical PAPER source coverage incomplete")

    paper_ledger_archive_sha256="sha256:"+hashlib.sha256(export_db.read_bytes()).hexdigest()
    # Event outcomes are PAPER only, not broker-confirmed orders.
    paper_outcomes = {
        "NO_QORE_NAV": "PAPER_UNFUNDABLE",
        "NO_ATLAS_M5_ENTRY": "NO_EXECUTABLE_ENTRY",
        "FUTURE_M5_PRICE_NOT_CAUSALLY_OBSERVABLE": "INCOMPLETE_EVIDENCE",
        "INVALID_GEOMETRY": "INCOMPLETE_EVIDENCE",
        "INVALID_CROSS_SIDE_GEOMETRY": "INCOMPLETE_EVIDENCE",
        "QDLE_ERROR": "INCOMPLETE_EVIDENCE",
        "QDLE_NO_FINANCEABLE_LOT": "PAPER_UNFUNDABLE",
        "EXIT_POLICY_ERROR": "PAPER_UNFILLED",
        "PAPER_OPEN": "PAPER_OPEN",
        "PAPER_OPEN_UNRESOLVED_NO_EXIT_PATH": "INCOMPLETE_PRICE_PATH",
    }
    for receipt in rows:
        sid = receipt["signal_fingerprint"]
        state = receipt["status"]
        if state not in paper_outcomes:
            raise ValueError("unrecognized PAPER research execution state: "+state)
        receipt["execution_outcome"] = {
            "request_id":sid,
            "paper_status":paper_outcomes[state],
            "source_status":state,
            "broker_confirmed":False,
        }
    # Research-only QDLE_ERROR rows cannot claim a genuine priced quote.
    # Each such failure is counted independently rather than replaced with a
    # zero-lot physical response or swept under the 3368 acceptance count.
    if counts["received"]!=3368:
        raise ValueError("unexpected native input cardinality")
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
        "paper_qdle_account_ledger_scope":"ONE_SQLITE_ONE_CANONICAL_PaperQDLE_PER_SIMULATION",
        "canonical_paper_authority":"PaperQDLE_V1_SINGLE_RESERVATION_BOOK",
        "canonical_paper_coverage":canonical_coverage,
        "canonical_paper_audit_digest":canonical_digest,
        "paper_qdle_account_snapshots":session.sequence,
        "paper_qdle_account_receipts":account_receipts,
        "paper_qdle_ledger_complete_3368":journal_complete,
        "paper_qdle_physical_quote_count":len(quoted_rows),
        "paper_qdle_unassessable_count":len(no_quote_rows),
        "paper_qdle_state_counts":paper_states,
        "paper_qdle_event_counts":journal_events,
        "paper_qdle_archive_sha256":paper_ledger_archive_sha256,
        "paper_qdle_broker_tickets_are_synthetic":True,
        "paper_qdle_uses_broker_receipt_api":False,
        "signal_count":3368,"counts":dict(counts),
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
            "One persistent QDLE PAPER account; 4 motor caps scaled from original 60 USD quote evidence, not freshly reissued motor votes",
            "Paper lifecycle uses isolated research-only receipts; NO broker fill or settlement attestation",
            "Missing prices/geometry have durable QDLE research UNASSESSABLE receipts, NOT physical executable lot quotes",
            "PAPER physical lot quote never uses an M5 open after the decision time",
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
