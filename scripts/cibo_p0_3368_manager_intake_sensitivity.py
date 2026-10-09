#!/usr/bin/env python3
"""CEO P0: ALL 3368 Trader signals -> CIBO management (NO CIBO selection gate).

Sealed research signal geometry only; starting NAV USD60 fixed sensitivity,
NOT a sequential NAV replay, NOT broker-funded QDLE lots, NO REAL MT5 fills.
Proxies exactly labeled; never assert profit factor or drawdown for changed SL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal as D, localcontext
from pathlib import Path

from qore.infrastructure.cibo_trader_signal_administration import (
    EconomicStopBudget, TraderSignalIntake, propose_received_trader_management,
)

TICKS = {"AUDJPY": D(".001"), "EURUSD": D(".00001"),
         "GBPJPY": D(".001"), "GBPUSD": D(".00001"),
         "XAUUSD": D(".01"), "NDX100": D(".01")}
USD_PRICE_LOSS_PER_LOT = {"EURUSD": D("100000"),
                          "GBPUSD": D("100000"),
                          "XAUUSD": D("100"), "NDX100": D("10")}
SYMBOLS = set(TICKS)


def _hash(x: object) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(x, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def analyze(rows: list[dict], *, static_nav: D = D("60"),
            ndx_fee_proxy_per_lot: D = D("20")) -> dict:
    if (len(rows) != 3368 or len({x["signal_fingerprint"] for x in rows}) != 3368
        or not isinstance(static_nav, D) or not static_nav.is_finite() or static_nav <= 0
        or not ndx_fee_proxy_per_lot.is_finite() or ndx_fee_proxy_per_lot < 0):
        raise ValueError("seal/identity/price sensitivity invalid")
    receipts = []
    by_symbol = defaultdict(Counter)
    reasons = Counter()
    for idx, row in enumerate(rows):
        t = row["trader_opportunity"]
        symbol = "NDX100" if row["qore_symbol"] == "NAS100" else row["qore_symbol"]
        if symbol not in SYMBOLS:
            raise ValueError(f"unknown symbol at row {idx}")
        side = {"long": "BUY", "short": "SELL"}[t["side"]]
        at = datetime.fromisoformat(row["market_decision_at"])
        entry, stop = D(str(t["intended_entry"])), D(str(t["stop_loss"]))
        if at.tzinfo is None or at.utcoffset() is None:
            raise ValueError("naive market decision time")
        signal = TraderSignalIntake(
            signal_fingerprint=row["signal_fingerprint"],
            trader_id=row["trader_id"], symbol=symbol, side=side,
            entry_price=entry, structural_stop_price=stop,
            take_profit_price=D(str(t["take_profit"])),
            decided_at=at, trader_evidence_sha256=_hash(row),
        )
        with localcontext() as ctx:
            ctx.prec = 100
            price_unit_usd_per_lot = (
                D(str(t["stop_loss_per_volume"])) / abs(entry-stop)
                if symbol in {"AUDJPY", "GBPJPY"} else USD_PRICE_LOSS_PER_LOT[symbol]
            )
            if symbol in {"AUDJPY", "EURUSD", "GBPJPY", "GBPUSD"}:
                total_fee = D("14")
            elif symbol == "XAUUSD":
                total_fee = entry * D("100") * D(".000016") * 2
            else:
                total_fee = ndx_fee_proxy_per_lot
            budget = EconomicStopBudget(
                qore_reconciled_nav_usd=static_nav,
                cibo_max_loss_usd=static_nav * D(".05"),
                source_unreserved_loss_capacity_usd=static_nav,
                broker_min_lot=D(".01"), broker_lot_step=D(".01"),
                tick_size_price=TICKS[symbol],
                # Broker historical stops_level is UNKNOWN. Optimistic sensitivity
                # only; NOT executable without real provider preflight.
                broker_min_stop_distance_price=D("0"),
                price_loss_usd_per_price_unit_per_lot=price_unit_usd_per_lot,
                opening_commission_usd_per_lot=total_fee / 2,
                closing_commission_usd_per_lot=total_fee / 2,
                execution_buffer_usd_per_lot=D("0"),
                broker_data_as_of=at,
                price_valuation_evidence_sha256=_hash({
                    "research_source": row["signal_fingerprint"],
                    "basis": "NON_HISTORICAL_USD_LOSS_PER_PRICE_UNIT_SCENARIO",
                    "roundtrip_fee_per_lot": str(total_fee),
                }),
            )
        receipt = propose_received_trader_management(signal=signal, budget=budget)
        primary_reason = receipt.reason_codes[0]
        by_symbol[symbol]["signals_received"] += 1
        by_symbol[symbol][receipt.status] += 1
        by_symbol[symbol][primary_reason] += 1
        reasons[primary_reason] += 1
        receipts.append({
            "signal_fingerprint": signal.signal_fingerprint,
            "trader_id": signal.trader_id,
            "symbol": symbol, "decision_at": at.isoformat(),
            "intake": "CIBO_MANAGEMENT_RECEIVED",
            "status": receipt.status,
            "reason_codes": list(receipt.reason_codes),
            "structural_stop_price": str(receipt.structural_stop_price),
            "proposed_protective_stop_price": (
                str(receipt.proposed_protective_stop_price)
                if receipt.proposed_protective_stop_price is not None else None
            ),
            "qore_static_budget_usd": str(receipt.budget_usd),
            "min_lot_risk_at_proposed_stop_proxy_usd": (
                str(receipt.min_lot_stop_plus_all_costs_usd)
                if receipt.min_lot_stop_plus_all_costs_usd is not None else None
            ),
            "physical_qdle_lots": None,
            "broker_fill": False,
            "research_only": True,
        })
    if len(receipts) != 3368 or any(
        r["intake"] != "CIBO_MANAGEMENT_RECEIVED" or r["broker_fill"]
        for r in receipts
    ):
        raise ValueError("CIBO management must receive every Trader signal")
    summary = {
        "schema": "qore.cibo.p0.3368.manager-intake-static-proxy.v1",
        "signals_received": len(receipts),
        "unique_trader_signal_ids": len({r["signal_fingerprint"] for r in receipts}),
        "cibo_administration_receipts": len(receipts),
        "old_cibo_cognitive_admission_gate_used": False,
        "model": "ONE_SIGNAL_AT_A_TIME_STATIC_NAV_60_BROKER_GRID_ONLY",
        "starting_nav_usd": str(static_nav),
        "static_max_entry_risk_usd": str(static_nav * D(".05")),
        "physical_qdle_financing_tested": False,
        "causal_managed_exits_simulated": False,
        "real_mt5_fills": 0,
        "profit_factor": None,
        "drawdown": None,
        "intratrade_price_path_tested": False,
        "proxies": ["USD/JPY price conversion derived from original stop valuation",
                    "static broker min lot 0.01, min stop distance UNKNOWN modeled 0",
                    "FX 14 USD/lot roundtrip; NDX 20 USD/lot; XAU notional proxy",
                    "spread, gap, slippage buffer 0 optimistic sensitivity",
                    "no margin, concurrency, Bank/Cushion available source validation"],
        "by_symbol": {k:dict(sorted(v.items())) for k,v in sorted(by_symbol.items())},
        "reasons": dict(sorted(reasons.items())),
    }
    return {"summary":summary,"receipts":receipts}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    raw = json.loads(args.manifest.read_text())
    output = analyze(raw["opportunities"])
    args.output.parent.mkdir(exist_ok=True, parents=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True)+"\n")
    print("CIBO_3368_MANAGER_INTAKE", json.dumps(output["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
