#!/usr/bin/env python3
"""Trader Lab QDLE causal financial replay; RESEARCH ONLY, NEVER execution.

Accepts ordered provider + QORE ledger events, routes every pre-entry intent
through the production QDLE reservation kernel, and refuses to report economic
success if even one mandatory minimum lot cannot be funded. Synthetic source
provenance is explicit. No future outcome is used for financial decisions.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.qore_dynamic_lot_engine import (
    BrokerValuation, Position, QDLE, QDLEAccount, QDLEError, QDLEIntent, QDLESymbol,
)


class SealedReplayBroker:
    def __init__(self) -> None:
        self.observations: dict[str, BrokerValuation] = {}
        self.preflight: dict[str, bool] = {}

    def observe(self, row: dict) -> None:
        symbol = row["symbol"]
        self.observations[symbol] = BrokerValuation(
            Decimal(row["stop_loss_usd_per_lot"]),
            Decimal(row["margin_usd_per_lot"]),
            datetime.fromisoformat(row["as_of"]),
            "SEALED_REPLAY:" + row["source_id"],
        )
        self.preflight[symbol] = bool(row.get("preflight_pass", False))

    def value(self, instrument: QDLESymbol, intent: QDLEIntent, now: datetime) -> BrokerValuation:
        quote = self.observations.get(instrument.broker_symbol)
        if quote is None or quote.as_of > now:
            raise QDLEError("no causal pretrade valuation event")
        return quote

    def check_volume(self, instrument: QDLESymbol, intent: QDLEIntent, lots: Decimal) -> None:
        if not self.preflight.get(instrument.broker_symbol):
            raise QDLEError("no recorded broker preflight PASS")


def _dec(row: dict, name: str) -> Decimal:
    return Decimal(str(row[name]))


def replay(events: list[dict], db_path: str | Path,
           *, expected_intents: int | None = None) -> dict:
    broker = SealedReplayBroker()
    engine = QDLE(db_path, broker, max_age_seconds=30)
    intent_rows = []
    failures = []
    seen_request_ids: set[str] = set()
    counted_intents = 0
    last_time = None
    for ix, event in enumerate(events):
        kind = event["type"]
        now = datetime.fromisoformat(event["at"])
        if now.tzinfo is None or (last_time is not None and now < last_time):
            raise QDLEError("noncausal/out-of-order replay event")
        last_time = now
        if kind == "ACCOUNT":
            engine.publish_account(QDLEAccount(
                account_id=event["account_id"], provider=event["provider"],
                currency=event["currency"], sequence=int(event["sequence"]),
                as_of=now, balance=_dec(event, "balance"),
                equity=_dec(event, "equity"), free_margin=_dec(event, "free_margin"),
                qore_unreserved_risk_usd=_dec(event, "qore_unreserved_risk_usd"),
                sovereign_free_source_usd=_dec(event, "sovereign_free_source_usd"),
                cushion_free_source_usd=_dec(event, "cushion_free_source_usd"),
                positions=tuple(Position(p["ticket"], p["symbol"], p["side"],
                                         _dec(p, "lots"))
                                for p in event.get("positions", [])),
                covered_fill_tickets=tuple(event.get("covered_fill_tickets", [])),
            ))
        elif kind == "SYMBOL":
            engine.publish_symbol(QDLESymbol(
                broker_symbol=event["symbol"],
                aliases=tuple(event["aliases"]),
                min_lot=_dec(event, "volume_min"), max_lot=_dec(event, "volume_max"),
                lot_step=_dec(event, "volume_step"),
                directional_volume_limit=_dec(event, "volume_limit"),
                tick_size=_dec(event, "tick_size"),
                tick_value_loss_usd=_dec(event, "tick_value_loss_usd"),
                contract_size=_dec(event, "contract_size"),
                currency_profit=event["currency_profit"],
                fee_usd_per_lot=_dec(event, "fee_usd_per_lot"),
                fee_provenance=event["fee_provenance"],
                as_of=now, tradable=bool(event["tradable"]),
            ))
        elif kind == "VALUATION":
            broker.observe(dict(event, as_of=event["at"]))
        elif kind == "INTENT":
            counted_intents += 1
            request_id = event["request_id"]
            if request_id in seen_request_ids:
                failures.append({"index": ix, "request_id": request_id,
                                 "reason": "DUPLICATE_TRADER_SIGNAL_NOT_DISTINCT_ENTRY"})
                continue
            seen_request_ids.add(request_id)
            trade = QDLEIntent(
                request_id=event["request_id"], trader_id=event["trader_id"],
                symbol=event["symbol"], side=event["side"],
                entry_price=_dec(event, "entry_price"),
                stop_price=_dec(event, "stop_price"),
                requested_risk_usd=_dec(event, "requested_risk_usd"),
                sizing_cap_usd=_dec(event, "sizing_cap_usd"),
                cibo_compound_cap_usd=_dec(event, "cibo_compound_cap_usd"),
                portfolio_cap_usd=_dec(event, "portfolio_cap_usd"),
                leverage_cap_lots=_dec(event, "leverage_cap_lots"),
                margin_cap_usd=_dec(event, "margin_cap_usd"),
                source_lane=event["source_lane"],
                slippage_usd_per_lot=_dec(event, "slippage_usd_per_lot"),
                expected_account_sequence=event["expected_account_sequence"],
            )
            try:
                result = engine.reserve_for_trader(trade, now=now)
                intent_rows.append({"request_id": trade.request_id,
                                    "state": result.state,
                                    "lotage": str(result.lots),
                                    "stop_usd": str(result.stop_usd),
                                    "all_in_stop_usd": str(result.total_risk_usd),
                                    "margin_usd": str(result.margin_usd),
                                    "binding_limits": result.binding_limits})
                if result.state != "RESERVED_FOR_TRADER":
                    failures.append({"index": ix, "request_id": trade.request_id,
                                     "reason": result.note or "UNFUNDABLE"})
            except QDLEError as exc:
                failures.append({"index": ix, "request_id": trade.request_id,
                                 "reason": str(exc)})
        elif kind == "FILL":
            engine.acknowledge_fill(event["request_id"], event["ticket"])
        elif kind == "RECONCILE":
            engine.reconcile_fill(event["request_id"])
        elif kind == "REJECTED":
            engine.confirm_rejection(event["request_id"], event["broker_rejection_ref"])
        else:
            raise QDLEError(f"unsupported event: {kind}")
    if expected_intents is not None and counted_intents != expected_intents:
        failures.append({"reason": "EXPECTED_ENTRY_COUNT_MISMATCH"})
    reserved = [r for r in intent_rows if r["state"] == "RESERVED_FOR_TRADER"]
    status = "RESEARCH_PHYSICAL_GATE_PASS" if not failures else "RESEARCH_FAIL_CLOSED"
    # Gate passing is not broker execution, 3-year certification or PnL proof.
    return {
        "schema": "qore.qdle.trader-lab-financing-report.v1",
        "status": status, "certified": False, "broker_execution_proven": False,
        "source_plane": "SEALED_REPLAY_NOT_LIVE_MT5",
        "total_intents_accounted": counted_intents,
        "unique_signal_ids": len(seen_request_ids),
        "reserved_proposals": len(reserved),
        "unfundable_or_invalid": len(failures),
        "proposed_stop_risk_usd": str(sum((Decimal(r["all_in_stop_usd"])
                                               for r in reserved), Decimal(0))),
        "failures": failures,
        "intents": intent_rows,
        "telemetry": engine.ledger(limit=1000),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-intents", type=int)
    args = parser.parse_args()
    dataset = json.loads(args.events.read_text(encoding="utf-8"))
    if dataset.get("schema") != "qore.qdle.replay-events.v1":
        parser.error("QDLE event schema required")
    if args.db.exists():
        parser.error("QDLE replay needs a clean unique database per trial")
    result = replay(dataset["events"], args.db,
                    expected_intents=args.expected_intents)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({key: result[key] for key in (
        "status", "reserved_proposals", "unfundable_or_invalid",
        "total_intents_accounted", "proposed_stop_risk_usd")}, sort_keys=True))
    return 0 if result["status"] == "RESEARCH_PHYSICAL_GATE_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
