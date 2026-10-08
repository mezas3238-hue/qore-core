#!/usr/bin/env python3
"""Research-only 3368-intent QDLE replay with dual capital ledgers.

Pinned burned 2019-2022 research opportunity source, NO MT5 broker fills.
Broker USD2000 initial margin; proprietary QORE NAV USD60 initial, 5% risk.
Observed 2026 MT5 mobile margin/symbol grids are STATIC COST PROXIES, not
historical provider conditions. Structural R outcome consumed ONLY at exit.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
from datetime import timedelta
from dataclasses import replace
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal as D
from pathlib import Path

from qore.infrastructure.cibo_account_sizing_authority import propose_p0_sizing_vote
from qore.infrastructure.cibo_compound_capital import propose_p0_compound_vote
from qore.infrastructure.cibo_marginal_leverage_utility import propose_p0_adaptive_leverage_vote
from qore.infrastructure.cibo_core_compound_portfolio import propose_p0_portfolio_vote
from qore.infrastructure.cibo_four_motor_policy import FourMotorObservation, ReconciledQoreCashflow
from qore.infrastructure.cibo_four_motor_qdle_proposal import build_four_motor_qdle_intent
from qore.infrastructure.qore_dynamic_lot_engine import (
    BrokerValuation, Position, QDLE, QDLEAccount, QDLEError, QDLEIntent, QDLESymbol,
)

ZERO = D("0")
FIVE = D("0.05")
START_QORE = D("60")
START_BROKER = D("2000")
# Screenshot fields, not broker-historical order_calc_margin().
CONTRACTS = {"AUDJPY": D("100000"), "EURUSD": D("100000"),
             "GBPJPY": D("100000"), "GBPUSD": D("100000"),
             "XAUUSD": D("100"), "NDX100": D("10")}
MARGINS = {
    "AUDJPY": {"BUY": D("2318.93"), "SELL": D("2318.67")},
    "EURUSD": {"BUY": D("3735.03"), "SELL": D("3734.77")},
    "GBPJPY": {"BUY": D("4407.40"), "SELL": D("4407.40")},
    "GBPUSD": {"BUY": D("4407.63"), "SELL": D("4407.63")},
    "XAUUSD": {"BUY": D("53637.48"), "SELL": D("53629.68")},
    "NDX100": {"BUY": D("61481.98"), "SELL": D("61478.78")},
}
TICKS = {"AUDJPY": D(".001"), "EURUSD": D(".00001"),
         "GBPJPY": D(".001"), "GBPUSD": D(".00001"),
         "XAUUSD": D(".01"), "NDX100": D(".01")}
PROFIT = {"AUDJPY": "JPY", "GBPJPY": "JPY", "EURUSD": "USD",
          "GBPUSD": "USD", "XAUUSD": "USD", "NDX100": "USD"}
# Swap points and triple-rollover day transcribed from mobile MT5 (2026).
# RESEARCH UTC midnight proxy ONLY: historical rate/server rollover not known.
SWAP = {
    "AUDJPY": {"BUY": D("-11.27"), "SELL": D("-19.841")},
    "EURUSD": {"BUY": D("-13.472"), "SELL": D("0.107")},
    "GBPJPY": {"BUY": D("-25.806"), "SELL": D("-44.278")},
    "GBPUSD": {"BUY": D("-17.13"), "SELL": D("-2.977")},
    "XAUUSD": {"BUY": D("-107.151"), "SELL": D("-46.917")},
    "NDX100": {"BUY": D("-372.912"), "SELL": D("-57.6")},
}
SWAP_TRIPLE_WEEKDAY = {"NDX100": 4, "XAUUSD": 2,
                        "AUDJPY": 2, "EURUSD": 2, "GBPJPY": 2, "GBPUSD": 2}
TICK_VALUES_PER_LOT_USD = {"XAUUSD": D("1"), "NDX100": D("0.10")}


def utc_midnight_swap_proxy(trade: dict, exit_at: datetime) -> D:
    # Count rollovers on the previous UTC weekday. An MT5 server may
    # have a different rollover clock, so this MUST NOT imply real swaps.
    day = trade["opened_at"].date()
    last = exit_at.date()
    swaps = ZERO
    while day < last:
        multiple = 3 if day.weekday() == SWAP_TRIPLE_WEEKDAY[trade["symbol"]] else 1
        swaps += trade["lots"] * trade["swap_usd_per_lot"] * multiple
        day += timedelta(days=1)
    return swaps


class HistoricalProxy:
    """Immutable decision-time research proxy. Never calls MT5 order_send."""
    def __init__(self) -> None:
        self.quote: BrokerValuation | None = None

    def value(self, instrument: QDLESymbol, intent: QDLEIntent, now: datetime) -> BrokerValuation:
        if self.quote is None or self.quote.as_of != now:
            raise QDLEError("MISSING_DECISION_TIME_RESEARCH_VALUATION")
        return self.quote

    def check_volume(self, instrument: QDLESymbol, intent: QDLEIntent, lots: D) -> None:
        if not (instrument.min_lot <= lots <= instrument.max_lot):
            raise QDLEError("RESEARCH_VOLUME_NOT_ON_BROKER_GRID")
        if lots % instrument.lot_step:
            raise QDLEError("RESEARCH_VOLUME_OFF_BROKER_GRID")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--motor-policy", choices=["shared_proxy", "independent_four_motors"], default="shared_proxy")
    p.add_argument("--target-lots", type=D, default=None, help="Optional maximum broker lots requested, never additional risk authorization")
    p.add_argument("--ndx-roundtrip-fee-proxy-usd-per-lot", type=D, default=None,
                   help="Explicit research sensitivity only; unknown NDX fee never inferred")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--min-policy", choices=["original_trader", "broker_grid"], default="original_trader")
    p.add_argument("--swap-proxy", choices=["off", "utc_midnight"], default="utc_midnight")
    p.add_argument("--provider-trailing-usd", type=str, default="120",
                   help="USD loss threshold sensitivity; disabled = provider rule NOT modeled")
    args = p.parse_args()
    if args.target_lots is not None and (not args.target_lots.is_finite() or args.target_lots <= ZERO):
        raise SystemExit("Invalid target lots")
    if args.motor_policy == "independent_four_motors" and (
        args.ndx_roundtrip_fee_proxy_usd_per_lot is None
        or not args.ndx_roundtrip_fee_proxy_usd_per_lot.is_finite()
        or args.ndx_roundtrip_fee_proxy_usd_per_lot < ZERO
    ):
        raise SystemExit("Independent replay requires explicit NDX all-in fee sensitivity; zero permitted only as optimistic sensitivity")
    provider_limit = None if args.provider_trailing_usd == "disabled" else D(args.provider_trailing_usd)
    if provider_limit is not None and provider_limit <= 0:
        raise SystemExit("Invalid trailing USD model")
    raw = json.loads(args.manifest.read_text(encoding="utf-8"))
    opportunities = raw["opportunities"]
    if len(opportunities) != 3368 or len({x["signal_fingerprint"] for x in opportunities}) != 3368:
        raise SystemExit("FAIL CLOSED: 3368 unique original signals required")
    if any(opportunities[i]["market_decision_at"] > opportunities[i + 1]["market_decision_at"]
           for i in range(len(opportunities) - 1)):
        raise SystemExit("FAIL CLOSED: sealed opportunity order not chronological")

    nav = START_QORE
    peak_nav = nav
    broker_peak = START_BROKER
    realized_gains = ZERO
    wins = ZERO
    losses = ZERO
    peak_to_trough = ZERO
    maximum_absolute_dd = ZERO
    max_dd_ratio = ZERO
    active: dict[str, dict] = {}
    exits: list[tuple[datetime, str]] = []
    source_counts = Counter()
    rejection_binding_counts = Counter()
    module_binding_ties = Counter()
    module_summed_limits_usd = defaultdict(lambda: ZERO)
    module_audit_present = Counter()
    sym_counts: dict[str, Counter] = defaultdict(Counter)
    total_cost = ZERO
    entry_commission_paid = ZERO
    closing_commission_paid = ZERO
    recent_settlements: list[tuple[datetime, str, D]] = []
    swap_pnl = ZERO
    rollover_count = 0
    realized_count = 0
    provider_floor_breach = 0
    provider_closed_at = None
    unresolved_at_breach = 0
    decisions = []
    last_spec_time: dict[str, datetime] = {}

    with tempfile.TemporaryDirectory() as t:
        broker = HistoricalProxy()
        qdle = QDLE(Path(t) / "qdle_3368_sealed.sqlite", broker)
        sequence = 0
        def publish(at: datetime) -> None:
            nonlocal sequence, broker_peak, provider_floor_breach
            sequence += 1
            broker_equity = START_BROKER + nav - START_QORE
            broker_peak = max(broker_peak, broker_equity)
            # Sensitivity proxy ONLY, not independently verified account rules.
            assumed_floor = broker_peak - provider_limit if provider_limit is not None else ZERO
            headroom = max(ZERO, broker_equity - assumed_floor)
            if provider_limit is not None and broker_equity <= assumed_floor:
                provider_floor_breach += 1
            open_risk = sum((x["planned_risk"] for x in active.values()), ZERO)
            open_margin = sum((x["margin"] for x in active.values()), ZERO)
            available_qore = max(ZERO, nav - open_risk)
            broker_free_margin = max(ZERO, broker_equity - open_margin)
            qdle.publish_account(QDLEAccount(
                account_id="SEALED_RESEARCH_2000", provider="FundedNext", currency="USD",
                sequence=sequence, as_of=at,
                balance=max(ZERO, broker_equity), equity=max(ZERO, broker_equity),
                free_margin=broker_free_margin,
                qore_unreserved_risk_usd=min(available_qore, headroom),
                sovereign_free_source_usd=available_qore,
                cushion_free_source_usd=ZERO,
                qore_trading_capital_usd=max(ZERO, nav),
                positions=tuple(Position(k, v["symbol"], v["side"], v["lots"])
                                for k, v in sorted(active.items())),
                covered_fill_tickets=tuple(sorted(active)),
            ))
        def settle_until(at: datetime) -> None:
            nonlocal nav, peak_nav, max_dd_ratio, maximum_absolute_dd
            nonlocal provider_closed_at, unresolved_at_breach
            nonlocal realized_count, total_cost, wins, losses, realized_gains
            nonlocal closing_commission_paid
            nonlocal swap_pnl, rollover_count
            if provider_closed_at is not None:
                return
            while exits and exits[0][0] <= at:
                when, ticket = heapq.heappop(exits)
                trade = active.pop(ticket)
                gross = trade["lots"] * trade["stop_per_lot"] * trade["r"]
                cost = trade["lots"] * trade["fee_per_lot"]
                swap = utc_midnight_swap_proxy(trade, when) if args.swap_proxy == "utc_midnight" else ZERO
                if swap != ZERO:
                    rollover_count += 1
                swap_pnl += swap
                pnl = gross - cost + swap
                trade["decision_event"].update(
                    realized_pnl_usd_proxy=str(pnl),
                    pnl_gross_usd_proxy=str(gross),
                    realized_exit_at=when.isoformat(),
                    swap_usd_proxy=str(swap),
                )
                realized_gains += pnl
                # Entry commission was already removed from NAV at hypothetical fill.
                nav += gross + swap - trade.get("deferred_close_fee", ZERO)
                closing_commission_paid += trade.get("deferred_close_fee", ZERO)
                recent_settlements.append((when, ticket, pnl))
                wins += max(ZERO, pnl)
                losses += max(ZERO, -pnl)
                realized_count += 1
                peak_nav = max(peak_nav, nav)
                dd = max(ZERO, peak_nav - nav)
                maximum_absolute_dd = max(maximum_absolute_dd, dd)
                if peak_nav > 0:
                    max_dd_ratio = max(max_dd_ratio, dd / peak_nav)
                sym_counts[trade["symbol"]]["research_settlements"] += 1
                publish(when)
                if provider_limit is not None and START_BROKER + nav - START_QORE <= broker_peak - provider_limit:
                    provider_closed_at = when.isoformat()
                    unresolved_at_breach = len(active)
                    source_counts["PROVIDER_CLOSED_EQUITY_TRAILING_BREACH"] += 1
                    # Provider breach: stop accounting future hypothetical gains;
                    # actual forced-close PnL requires missing intratrade ticks.
                    return
                # synthetic lifecycle: NOT a verified broker ticket/deal.
                # Do not call record_broker_settlement: that method requires
                # authentic broker settlement receipts not present in source.

        # The original manifest orders decisions, not hypothetical fills.
        # Historical entry_at can lag a limit decision by >2 days.
        # Evaluate economic/margin capacity when a hypothetical entry would fill.
        chronological = sorted(enumerate(opportunities),
                               key=lambda x: (x[1]["settlement_outcome_research_only"]["entry_at"], x[0]))
        for index, row in chronological:
            at = datetime.fromisoformat(row["settlement_outcome_research_only"]["entry_at"])
            decision_at = datetime.fromisoformat(row["market_decision_at"])
            if provider_closed_at is None:
                settle_until(at)  # no PnL after provider shutdown; no future leakage.
            t = row["trader_opportunity"]
            symbol = "NDX100" if row["qore_symbol"] == "NAS100" else row["qore_symbol"]
            side = "BUY" if t["side"] == "long" else "SELL"
            entry, stop = D(t["intended_entry"]), D(t["stop_loss"])
            rid = row["signal_fingerprint"]
            event = {"index": index, "signal_fingerprint": rid, "at": at.isoformat(),
                     "signal_at": decision_at.isoformat(),
                     "research_entry_type": t["entry_type"],
                     "symbol": symbol, "trader": row["trader_id"],
                     "status": "UNFUNDABLE", "lots": "0"}
            sym_counts[symbol]["original_signals"] += 1
            if provider_closed_at is not None:
                event["status"] = "BLOCKED_AFTER_PROVIDER_LIMIT"
                event["reason"] = "PROVIDER_TRAILING_LIMIT_TRIGGERED_CLOSED_EQUITY_PROXY"
                decisions.append(event)
                sym_counts[symbol]["unfundable"] += 1
                source_counts["BLOCKED_AFTER_PROVIDER_LIMIT"] += 1
                continue
            publish(at)
            try:
                if entry <= 0 or stop <= 0:
                    raise QDLEError("INVALID_HISTORICAL_ENTRY_OR_STOP")
                if (side == "BUY" and stop >= entry) or (side == "SELL" and stop <= entry):
                    raise QDLEError("INVALID_DIRECTIONAL_STOP")
                if nav <= 0:
                    raise QDLEError("QORE_PROPRIETARY_NAV_EXHAUSTED")
                # FXJPY uses USD-per-lot proxy captured in original research
                # manifest; EUR/GBPUSD recompute from USD quote; XAU/NDX
                # contract economics come from user screenshots.
                stop_per_lot = (
                    abs(entry - stop) * CONTRACTS[symbol] if symbol in
                    {"EURUSD", "GBPUSD", "XAUUSD", "NDX100"}
                    else D(t["stop_loss_per_volume"])
                )
                if stop_per_lot <= 0:
                    raise QDLEError("INVALID_RESEARCH_STOP_VALUATION")
                # Explicit scenario fees are all-in *proxies*, not broker proof.
                # FX opening $7 + closing $7 per lot, as requested by the user.
                # XAU 0.0016% screenshot: unknown base/side, model 2 symmetric legs.
                # NDX has NO observed fee; caller must supply a scenario assumption.
                if symbol in {"AUDJPY", "GBPJPY", "GBPUSD", "EURUSD"}:
                    fee = (D("14") if args.motor_policy == "independent_four_motors"
                           else D("7"))
                elif symbol == "XAUUSD":
                    fee = D("0.000016") * CONTRACTS[symbol] * entry
                    if args.motor_policy == "independent_four_motors":
                        fee *= 2
                elif args.motor_policy == "independent_four_motors":
                    fee = args.ndx_roundtrip_fee_proxy_usd_per_lot
                else:
                    fee = ZERO
                if at > last_spec_time.get(symbol, datetime.min.replace(tzinfo=at.tzinfo)):
                    qdle.publish_symbol(QDLESymbol(
                        broker_symbol=symbol, aliases=(symbol, "NAS100") if symbol == "NDX100" else (symbol,),
                        min_lot=D(".01"), max_lot=D("50") if symbol == "XAUUSD" else D("40"),
                        lot_step=D(".01"), directional_volume_limit=ZERO,
                        tick_size=TICKS[symbol], tick_value_loss_usd=D("1"),
                        contract_size=CONTRACTS[symbol], currency_profit=PROFIT[symbol],
                        # Price-dependent XAU costs travel as a per-entry extra
                        # allowance below; fixed FX/NDX fees live in broker spec.
                        fee_usd_per_lot=(fee if args.motor_policy == "independent_four_motors"
                                         and symbol != "XAUUSD" else ZERO),
                        fee_provenance="SCENARIO_COST_PROXY_UNVERIFIED",
                        as_of=at, tradable=True,
                    ))
                    last_spec_time[symbol] = at
                broker.quote = BrokerValuation(
                    stop_per_lot, MARGINS[symbol][side], at, "SCREENSHOT_2026_STATIC_MARGIN_RESEARCH_PROXY",
                )
                risk_budget = max(ZERO, nav) * FIVE
                free_qore = max(ZERO, nav - sum((x["planned_risk"] for x in active.values()), ZERO))
                free_broker = max(ZERO, START_BROKER + nav - START_QORE -
                                  sum((x["margin"] for x in active.values()), ZERO))
                limit_lots = D("40") if symbol != "XAUUSD" else D("50")
                policy_min = D(t["minimum_volume"]) * D(t.get("minimum_execution_steps", 1))
                if args.min_policy == "broker_grid":
                    policy_min = D(".01")
                event["stop_loss_usd_per_lot"] = str(stop_per_lot)
                event["commission_roundtrip_proxy_per_lot"] = str(fee) if args.motor_policy == "independent_four_motors" else None
                event["commission_entry_usd_per_lot_proxy"] = str(fee)
                if args.motor_policy == "independent_four_motors":
                    open_stop = sum((x["planned_risk"] for x in active.values()), ZERO)
                    open_margin = sum((x["margin"] for x in active.values()), ZERO)
                    same_symbol_stop = sum((x["planned_risk"] for x in active.values()
                                            if x["symbol"] == symbol), ZERO)
                    same_trader_stop = sum((x["planned_risk"] for x in active.values()
                                            if x.get("trader") == row["trader_id"]), ZERO)
                    same_direction = sum((x["lots"] for x in active.values()
                                          if x["symbol"] == symbol and x["side"] == side), ZERO)
                    # Simulated cashbook is NOT a broker settlement statement.
                    digest = "sha256:" + hashlib.sha256(
                        (rid + at.isoformat() + str(nav) + str(fee)).encode()
                    ).hexdigest()
                    # Keep 3 most recent completed trade settlements distinct,
                    # so Compound's three-loss defense can really activate.
                    # Aggregate earlier cashflows + already debited opening fees
                    # in a prior synthetic cashbook receipt without inventing profit.
                    recent = recent_settlements[-3:]
                    previous_amount = nav - START_QORE - sum(
                        (v for _, _, v in recent), ZERO
                    )
                    prior_time = (recent[0][0] - timedelta(microseconds=1)
                                  if recent else at)
                    simulated_flows = (
                        ((ReconciledQoreCashflow(
                            "REPLAY_PRIOR_CASHBOOK:" + rid, prior_time,
                            previous_amount, digest, True),)
                         if previous_amount != ZERO else ())
                        + tuple(ReconciledQoreCashflow(
                            "REPLAY_SETTLED:" + trade_id, completed_at,
                            net, digest, True,
                        ) for completed_at, trade_id, net in recent)
                    )
                    obs = FourMotorObservation(
                        request_id=rid, trader_id=row["trader_id"], symbol=symbol, side=side,
                        source_lane="SOVEREIGN_BANK", observed_at=at,
                        account_sequence=sequence, broker_evidence_sha256=digest,
                        initial_qore_nav_usd=START_QORE, reconciled_cashflows=simulated_flows,
                        protected_capital_usd=ZERO, floating_loss_reserve_usd=ZERO,
                        risk_reservations_usd=open_stop, bank_unreserved_usd=free_qore,
                        cushion_unreserved_usd=ZERO, total_open_stop_risk_usd=open_stop,
                        correlated_open_stop_risk_usd=same_symbol_stop,
                        trader_open_stop_risk_usd=same_trader_stop,
                        broker_free_margin_usd=START_BROKER + nav - START_QORE,
                        broker_margin_reservations_usd=open_margin,
                        stop_loss_usd_per_lot=stop_per_lot,
                        roundtrip_fees_usd_per_lot=fee,
                        execution_buffer_usd_per_lot=ZERO,
                        stress_extra_loss_usd_per_lot=ZERO,
                        broker_margin_usd_per_lot=MARGINS[symbol][side],
                        symbol_max_lots=limit_lots, provider_direction_max_lots=limit_lots,
                        open_and_reserved_direction_lots=same_direction,
                        broker_quote_at=at, broker_fees_complete=True,
                        broker_profit_valuation_complete=True,
                        broker_margin_valuation_complete=True,
                    )
                    votes = (propose_p0_sizing_vote(obs),
                             propose_p0_compound_vote(obs),
                             propose_p0_adaptive_leverage_vote(obs),
                             propose_p0_portfolio_vote(obs))
                    requested = build_four_motor_qdle_intent(
                        observation=obs, votes=votes, entry_price=entry,
                        stop_price=stop, methodology_min_lots=policy_min,
                    )
                    # XAU percent fee is price-dependent in this sensitivity,
                    # carried through QDLE's per-entry buffer. FX fees in Symbol.
                    if symbol == "XAUUSD":
                        requested = replace(requested, slippage_usd_per_lot=fee)
                    event["four_engine_reason_codes"] = {
                        v.producer: list(v.reason_codes) for v in votes
                    }
                    event["four_engine_caps_usd"] = {
                        "SIZING": votes[0].limits["approved_risk_usd"],
                        "CIBO_COMPOUND": votes[1].limits["approved_risk_usd"],
                        "PORTFOLIO_COMPOUND_AVAILABLE_SOURCE": votes[3].limits["approved_source_funds_usd"],
                    }
                    event["leverage_margin_budget_usd"] = votes[2].limits["approved_margin_usd"]
                    event["leverage_max_lots"] = votes[2].limits["approved_max_lots"]
                else:
                    event["four_engine_caps_usd"] = {
                        "SIZING": str(risk_budget),
                        "CIBO_COMPOUND": str(risk_budget),
                        "PORTFOLIO_COMPOUND_AVAILABLE_SOURCE": str(free_qore),
                    }
                    event["leverage_margin_budget_usd"] = str(free_broker)
                    event["leverage_max_lots"] = str(limit_lots)
                    requested = QDLEIntent(
                        request_id=rid, trader_id=row["trader_id"], symbol=symbol, side=side,
                        entry_price=entry, stop_price=stop,
                        requested_risk_usd=risk_budget, sizing_cap_usd=risk_budget,
                        cibo_compound_cap_usd=risk_budget,
                        portfolio_cap_usd=free_qore,
                        leverage_cap_lots=limit_lots,
                        margin_cap_usd=free_broker,
                        source_lane="SOVEREIGN_BANK",
                        slippage_usd_per_lot=fee, expected_account_sequence=sequence,
                        methodology_min_lots=policy_min,
                    )
                if args.target_lots is not None:
                    requested = replace(requested, requested_target_lots=args.target_lots)
                for label, value in event["four_engine_caps_usd"].items():
                    module_summed_limits_usd[label] += D(value)
                    module_audit_present[label] += 1
                module_audit_present["ADAPTIVE_LEVERAGE"] += 1
                result = qdle.reserve_for_trader(requested, now=at)
                event.update(status=result.state, lots=str(result.lots),
                             bound_modules=list(result.binding_limits),
                             fees_entry_usd_proxy=str(result.cost_usd),
                             planned_stop_usd=str(result.total_risk_usd),
                             margin_usd=str(result.margin_usd),
                             risk_budget_usd=str(risk_budget),
                             nav_at_decision_usd=str(nav))
                if result.lots > 0:
                    for bound in result.binding_limits:
                        module_binding_ties[bound] += 1
                if result.lots == 0:
                    primary_constraint = result.binding_limits[0] if result.binding_limits else "UNKNOWN_BROKER_GRID"
                    rejection_binding_counts[primary_constraint] += 1
                    event["reason"] = "BROKER_MINIMUM_UNFINANCEABLE_BY_" + primary_constraint
                    source_counts[event["reason"]] += 1
                    sym_counts[symbol]["unfundable"] += 1
                else:
                    if result.total_risk_usd > risk_budget or result.margin_usd > free_broker:
                        raise QDLEError("QDLE_INTERNAL_RISK_OR_MARGIN_BREACH")
                    # Research-only hypothetical fill at supplied structural entry,
                    # NEVER counts as broker-confirmed trade execution.
                    synthetic_ticket = "RESEARCH:" + rid
                    qdle.acknowledge_fill(rid, synthetic_ticket)
                    # Fee debited at entry, not at settlement: immediate QORE
                    # NAV and broker equity reduction feeds subsequent decisions.
                    # Broker-style simulated timing: opening fee at entry;
                    # closing fee ONLY at the modeled exit. QDLE pre-reserves
                    # the full two-leg cost before entry in both cases.
                    full_fee = result.lots * fee
                    entry_fee = (full_fee / D("2") if args.motor_policy == "independent_four_motors"
                                 else full_fee)
                    close_fee = full_fee - entry_fee
                    nav -= entry_fee
                    entry_commission_paid += entry_fee
                    total_cost += full_fee
                    peak_nav = max(peak_nav, nav)
                    dd_at_entry = max(ZERO, peak_nav - nav)
                    maximum_absolute_dd = max(maximum_absolute_dd, dd_at_entry)
                    if peak_nav > ZERO:
                        max_dd_ratio = max(max_dd_ratio, dd_at_entry / peak_nav)
                    expiration = datetime.fromisoformat(row["settlement_outcome_research_only"]["exit_at"])
                    if expiration < at:
                        raise QDLEError("HISTORICAL_EXIT_PRECEDES_DECISION")
                    # Tick values observed for metals/index; FX conversion
                    # from the historical research manifest loss-per-volume.
                    if symbol in TICK_VALUES_PER_LOT_USD:
                        usd_per_swap_point_per_lot = TICK_VALUES_PER_LOT_USD[symbol]
                    else:
                        usd_per_swap_point_per_lot = (
                            stop_per_lot * TICKS[symbol] / abs(entry - stop))
                    active[synthetic_ticket] = {
                        "decision_event": event,
                        "opened_at": at,
                        "swap_usd_per_lot": SWAP[symbol][side] * usd_per_swap_point_per_lot,
                        "symbol": symbol, "side": side, "trader": row["trader_id"], "lots": result.lots,
                        "margin": result.margin_usd, "planned_risk": result.total_risk_usd,
                        "stop_per_lot": stop_per_lot, "fee_per_lot": fee,
                        "deferred_close_fee": close_fee,
                        "r": D(row["settlement_outcome_research_only"]["gross_structural_outcome_r"]),
                    }
                    publish(at)
                    qdle.reconcile_fill(rid)
                    heapq.heappush(exits, (expiration, synthetic_ticket))
                    if provider_limit is not None and START_BROKER + nav - START_QORE <= broker_peak - provider_limit:
                        provider_closed_at = at.isoformat()
                        unresolved_at_breach = len(active)
                        source_counts["PROVIDER_ENTRY_FEE_TRAILING_BREACH"] += 1
                    source_counts["RESEARCH_HYPOTHETICAL_FUNDED"] += 1
                    sym_counts[symbol]["research_financed"] += 1
            except (QDLEError, ValueError, KeyError) as exc:
                source_counts[str(exc)[:110]] += 1
                event["reason"] = str(exc)
                sym_counts[symbol]["unfundable"] += 1
            decisions.append(event)
            if (index + 1) % 500 == 0:
                print("QDLE_PROGRESS", index + 1, "NAV", str(nav), "active", len(active), flush=True)
        if provider_closed_at is None:
            settle_until(datetime.max.replace(tzinfo=at.tzinfo))
        # Restore original manifest index order in the independent audit output.
        decisions.sort(key=lambda x: x["index"])
        broker_end = START_BROKER + nav - START_QORE
        report = {
            "schema": "qore.qdle.3368.dual-capital-research.v1",
            "certified": False,
            "broker_execution_proven": False,
            "real_fundednext_fills": 0,
            "physical_broker_MT5_probe_used": False,
            "source": "PINNED_WALK_FORWARD_MANIFEST_2019_2022_BURNED_RESEARCH",
            "risk_policy": "CONSTANT_5PCT_QORE_NAV_DYNAMIC_USD",
            "broker_initial_equity_usd": "2000",
            "qore_initial_capital_usd": "60",
            "historical_exposure_model": "STATIC_2026_SCREENSHOT_MARGIN_NOT_HISTORICAL_BROKER",
            "provider_loss_limit_model": ("RESEARCH_SENSITIVITY_TRAILING_" + str(provider_limit) + "_USD_NOT_VERIFIED") if provider_limit is not None else "NO_VERIFIED_PROVIDER_LIMIT_NOT_SIMULATED",
            "commission_model": ("FOREX_7_OPEN_PLUS_7_CLOSE_PER_LOT__XAU_SYMMETRIC_2_LEG_NOTIONAL_PROXY__NDX_EXPLICIT_SENSITIVITY" if args.motor_policy == "independent_four_motors" else "FOREX_ENTRY_ONLY_7USD_LOT__XAU_NOTIONAL_PROXY__NDX_ZERO_UNKNOWN"),
            "ndx_assumed_total_fee_usd_per_lot": str(args.ndx_roundtrip_fee_proxy_usd_per_lot) if args.motor_policy == "independent_four_motors" else None,
            "module_caps_provenance": ("SIMULATED_INDEPENDENT_FOUR_MOTOR_VOTES" if args.motor_policy == "independent_four_motors" else "PROXY_SHARED_5PCT_NOT_INDEPENDENT_MOTOR_DECISIONS"),
            "economic_motor_mode": args.motor_policy,
            "requested_target_lots": str(args.target_lots) if args.target_lots is not None else None,
            "module_binding_ties_on_funded": dict(module_binding_ties),
            "module_audit_observations": dict(module_audit_present),
            "module_summed_approved_usd_not_disbursed": {k: str(v) for k,v in module_summed_limits_usd.items()},
            "module_pnl_attribution_usd": None,
            "pnl_model": "POST_EXIT_STRUCTURAL_R_TIMES_CAUSAL_STOP_LOSS_PROXY_MINUS_ENTRY_COST",
            "research_volume_policy": args.min_policy,
            "signal_count": len(opportunities),
            "unique_signal_count": len({x["signal_fingerprint"] for x in opportunities}),
            "research_financed_proposals": sum(v["research_financed"] for v in sym_counts.values()),
            "research_unfundable_or_invalid": sum(v["unfundable"] for v in sym_counts.values()),
            "settled_research_outcomes": realized_count,
            "open_at_end": len(active),
            "qore_ending_capital_usd": str(nav),
            "broker_ending_equity_usd": str(broker_end),
            "net_research_pnl_usd": str(nav - START_QORE),
            "settled_trade_net_pnl_excluding_open_fee_effect_usd": str(realized_gains),
            "provider_trailing_closed_equity_stop_at": provider_closed_at,
            "provider_unresolved_positions_at_stop": unresolved_at_breach,
            "provider_stopped": provider_closed_at is not None,
            "risk_revaluation_epoch": "HYPOTHETICAL_ENTRY_AT_NOT_SIGNAL_AT",
            "gross_wins_usd": str(wins),
            "gross_losses_usd": str(losses),
            "entry_cost_proxy_usd": str(total_cost),
            "roundtrip_total_commission_committed_proxy_usd": str(total_cost),
            "opening_commission_paid_proxy_usd": str(entry_commission_paid),
            "closing_commission_paid_proxy_usd": str(closing_commission_paid),
            "unsettled_future_close_fee_not_charged_usd": str(sum((x.get("deferred_close_fee", ZERO) for x in active.values()), ZERO)),
            "net_swap_pnl_utc_midnight_proxy_usd": str(swap_pnl),
            "swap_rollover_position_count_proxy": rollover_count,
            "swap_model": "SCREENSHOT_2026_POINTS_AT_UTC_MIDNIGHT_PROXY" if args.swap_proxy == "utc_midnight" else "OMITTED_NO_DATA",
            "profit_factor_proxy": str(wins / losses) if losses > 0 else None,
            "max_closed_equity_drawdown_usd": str(maximum_absolute_dd),
            "max_closed_equity_drawdown_pct": str(max_dd_ratio * 100),
            "intratrade_drawdown_measured": False,
            "provider_floor_proxy_breach_sample_count": provider_floor_breach,
            "by_symbol": {k: dict(v) for k, v in sorted(sym_counts.items())},
            "reasons": dict(source_counts.most_common()),
            "unfundable_binding_constraints": dict(rejection_binding_counts.most_common()),
            "decisions": decisions,
            "limitations": [
                "Not historical MT5 symbol/margin or account-specific fees",
                "USDJPY currency-conversion uses original manifest research risk proxy",
                "NDX100 replaces USTEC: contract/strategy equivalence not established",
                "Historical research entry_at used as hypothetical fill: no tick/path proof",
                "Broker stop triggered on sampled closed equity only; unresolved forced liquidation",
                "At stop, capital is mark from last settlement/fee, NOT liquidation cash",
                "Original limit-order fill/partial fills not reconstructed",
                "Broker actual deals/spreads/slippage/swaps not measured",
                "Swap rollover model uses UTC midnight and current screenshot points, NOT historical broker records",
                "Closed-equity-only DD understates possible intratrade DD",
                "Pnl from realized structural R after exit, not actual MT5 transactions",
                "Four-module decisions are research policies calculated on simulated cashflows/quotes, not authentic historical broker votes",
                "Independent 4-motor mode assumes fee completeness for RESEARCH ONLY; fake evidence must never be used for live authorization",
                "No per-trader allocation receipts proved independently of the replay scenario",
                "Binding cap ties do NOT establish incremental independent module performance",
                "Research proxy is NOT a certified 36-month broker-financed backtest",
            ],
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True))
        print("QDLE_3368_REPORT_SUMMARY", json.dumps(
            {k: v for k, v in report.items() if k not in {"decisions", "limitations", "by_symbol", "reasons"}},
            sort_keys=True), flush=True)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
