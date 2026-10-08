#!/usr/bin/env python3
"""Research-only 3368-intent QDLE replay with dual capital ledgers.

Pinned burned 2019-2022 research opportunity source, NO MT5 broker fills.
Broker USD2000 initial margin; proprietary QORE NAV USD60 initial, 5% risk.
Observed 2026 MT5 mobile margin/symbol grids are STATIC COST PROXIES, not
historical provider conditions. Structural R outcome consumed ONLY at exit.
"""
from __future__ import annotations

import argparse
import heapq
import json
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal as D
from pathlib import Path

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
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--min-policy", choices=["original_trader", "broker_grid"], default="original_trader")
    args = p.parse_args()
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
    sym_counts: dict[str, Counter] = defaultdict(Counter)
    total_cost = ZERO
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
            assumed_floor = broker_peak - D("120")
            headroom = max(ZERO, broker_equity - assumed_floor)
            if broker_equity <= assumed_floor:
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
            while exits and exits[0][0] <= at:
                when, ticket = heapq.heappop(exits)
                trade = active.pop(ticket)
                gross = trade["lots"] * trade["stop_per_lot"] * trade["r"]
                cost = trade["lots"] * trade["fee_per_lot"]
                pnl = gross - cost
                realized_gains += pnl
                # Entry commission was already removed from NAV at hypothetical fill.
                nav += gross
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
                if START_BROKER + nav - START_QORE <= broker_peak - D("120"):
                    provider_closed_at = when.isoformat()
                    unresolved_at_breach = len(active)
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
            settle_until(at)  # only outcomes with known exits at/before entry time.
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
                if at > last_spec_time.get(symbol, datetime.min.replace(tzinfo=at.tzinfo)):
                    # A synthetic constant screenshot-based lot grid.
                    qdle.publish_symbol(QDLESymbol(
                        broker_symbol=symbol, aliases=(symbol, "NAS100") if symbol == "NDX100" else (symbol,),
                        min_lot=D(".01"), max_lot=D("50") if symbol == "XAUUSD" else D("40"),
                        lot_step=D(".01"), directional_volume_limit=ZERO,
                        tick_size=TICKS[symbol], tick_value_loss_usd=D("1"),
                        contract_size=CONTRACTS[symbol], currency_profit=PROFIT[symbol],
                        fee_usd_per_lot=D("0"), fee_provenance="SCREENSHOT_RESEARCH_PROXY",
                        as_of=at, tradable=True,
                    ))
                    last_spec_time[symbol] = at
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
                # Forex entry commission from MT5 screenshot; XAU commission
                # screenshot percent of unknown basis approximated as notional;
                # NDX100 commission unknown -> ZERO optimistic lower bound.
                if symbol in {"AUDJPY", "GBPJPY", "GBPUSD", "EURUSD"}:
                    fee = D("7")
                elif symbol == "XAUUSD":
                    fee = D("0.000016") * CONTRACTS[symbol] * entry
                else:
                    fee = ZERO
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
                result = qdle.reserve_for_trader(requested, now=at)
                event.update(status=result.state, lots=str(result.lots),
                             planned_stop_usd=str(result.total_risk_usd),
                             margin_usd=str(result.margin_usd),
                             risk_budget_usd=str(risk_budget),
                             nav_at_decision_usd=str(nav))
                if result.lots == 0:
                    source_counts["NO_VALID_LOTS_OR_MARGIN"] += 1
                    sym_counts[symbol]["unfundable"] += 1
                else:
                    # Research-only hypothetical fill at supplied structural entry,
                    # NEVER counts as broker-confirmed trade execution.
                    synthetic_ticket = "RESEARCH:" + rid
                    qdle.acknowledge_fill(rid, synthetic_ticket)
                    # Fee debited at entry, not at settlement: immediate QORE
                    # NAV and broker equity reduction feeds subsequent decisions.
                    entry_fee = result.lots * fee
                    nav -= entry_fee
                    total_cost += entry_fee
                    peak_nav = max(peak_nav, nav)
                    dd_at_entry = max(ZERO, peak_nav - nav)
                    maximum_absolute_dd = max(maximum_absolute_dd, dd_at_entry)
                    if peak_nav > ZERO:
                        max_dd_ratio = max(max_dd_ratio, dd_at_entry / peak_nav)
                    expiration = datetime.fromisoformat(row["settlement_outcome_research_only"]["exit_at"])
                    if expiration < at:
                        raise QDLEError("HISTORICAL_EXIT_PRECEDES_DECISION")
                    active[synthetic_ticket] = {
                        "symbol": symbol, "side": side, "lots": result.lots,
                        "margin": result.margin_usd, "planned_risk": result.total_risk_usd,
                        "stop_per_lot": stop_per_lot, "fee_per_lot": fee,
                        "r": D(row["settlement_outcome_research_only"]["gross_structural_outcome_r"]),
                    }
                    publish(at)
                    qdle.reconcile_fill(rid)
                    heapq.heappush(exits, (expiration, synthetic_ticket))
                    if START_BROKER + nav - START_QORE <= broker_peak - D("120"):
                        provider_closed_at = at.isoformat()
                        unresolved_at_breach = len(active)
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
            "provider_loss_limit_model": "RESEARCH_SENSITIVITY_TRAILING_120_USD_NOT_VERIFIED",
            "commission_model": "FOREX_ENTRY_ONLY_7USD_LOT__XAU_NOTIONAL_PROXY__NDX_ZERO_UNKNOWN",
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
            "profit_factor_proxy": str(wins / losses) if losses > 0 else None,
            "max_closed_equity_drawdown_usd": str(maximum_absolute_dd),
            "max_closed_equity_drawdown_pct": str(max_dd_ratio * 100),
            "intratrade_drawdown_measured": False,
            "provider_floor_proxy_breach_sample_count": provider_floor_breach,
            "by_symbol": {k: dict(v) for k, v in sorted(sym_counts.items())},
            "reasons": dict(source_counts.most_common()),
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
                "Closed-equity-only DD understates possible intratrade DD",
                "Pnl from realized structural R after exit, not actual MT5 transactions",
                "Four-module limits are same 5% ceiling, not historically replayed independent decisions",
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
