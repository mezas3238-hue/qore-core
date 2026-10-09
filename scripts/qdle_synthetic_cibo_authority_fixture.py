#!/usr/bin/env python3
"""Synthetic zero-budget CIBO proof: QDLE must NOT invent funds or fills.

This generator is STRICTLY a negative control; it is NOT CIBO strategy,
trade-management evidence, historical bank allocation or actual authority.
Do not use these fixtures to report CIBO PnL or achieved drawdown.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime
from decimal import Decimal as D


def generate(manifest: dict, *, one_funded: bool = False) -> dict:
    rows = manifest["opportunities"]
    ordered = sorted(enumerate(rows), key=lambda x: (
        x[1]["settlement_outcome_research_only"]["entry_at"], x[0]))
    instructions = []
    for index, (_, row) in enumerate(ordered, start=1):
        trader = row["trader_opportunity"]
        symbol = "NDX100" if row["qore_symbol"] == "NAS100" else row["qore_symbol"]
        evidence = "sha256:" + hashlib.sha256(
            ("SYNTHETIC_ZERO_RISK_NOT_CIBO:" + row["signal_fingerprint"]).encode()
        ).hexdigest()
        instructions.append(dict(
            signal_id=row["signal_fingerprint"], trader_id=row["trader_id"],
            symbol=symbol, side="BUY" if trader["side"] == "long" else "SELL",
            entry_price=trader["intended_entry"], stop_price=trader["stop_loss"],
            source_lane="PORTFOLIO_CUSHION" if index % 2 else "SOVEREIGN_BANK",
            allocated_source_funds_usd="0", authorized_all_in_risk_usd="0",
            maximum_requested_lots=None, account_sequence=index,
            issued_at=row["settlement_outcome_research_only"]["entry_at"],
            evidence_sha256=evidence,
        ))
    managed = []
    if one_funded:
        # Pick a late EURUSD signal where 0.01 lots safely fits $3 at a 10pip+
        # structural stop and full $14/lot round-trip *research* fee.
        candidates = [
            i for i, (_, row) in enumerate(ordered)
            if row["qore_symbol"] == "EURUSD"
            and D("0") < abs(
                D(row["trader_opportunity"]["intended_entry"])
                - D(row["trader_opportunity"]["stop_loss"])
            ) * D("100000") <= D("286")
        ]
        if not candidates:
            raise ValueError("no physically affordable EURUSD synthetic fixture")
        chosen_index = candidates[-1]
        chosen_row = ordered[chosen_index][1]
        chosen = instructions[chosen_index]
        chosen["source_lane"] = "PORTFOLIO_CUSHION"
        chosen["authorized_all_in_risk_usd"] = "3"
        chosen["allocated_source_funds_usd"] = "30"
        chosen["maximum_requested_lots"] = "0.01"
        exit_iso = chosen_row["settlement_outcome_research_only"]["exit_at"]
        chosen_at = datetime.fromisoformat(chosen["issued_at"])
        exit_at = datetime.fromisoformat(exit_iso)
        if exit_at < chosen_at:
            raise ValueError("fixture historical exit before entry")
        managed = [{
            "signal_id": chosen["signal_id"],
            "exit_at": exit_iso, "gross_outcome_r": "1",
            "evidence_sha256": "sha256:" + hashlib.sha256(
                ("SYNTHETIC_MANAGED_1R_NOT_CIBO:" + chosen["signal_id"]).encode()
            ).hexdigest()
        }]
        # Each funded position produces one additional snapshot on opening
        # and one on settlement, in addition to each signal's snapshot.
        for i in range(chosen_index + 1, len(instructions)):
            at = datetime.fromisoformat(instructions[i]["issued_at"])
            instructions[i]["account_sequence"] += 1 + (1 if exit_at <= at else 0)
    return dict(
        schema="qore.cibo.qdle-authoritative-economic-input.v1",
        provenance="SYNTHETIC_NEGATIVE_CONTROL_ZERO_RISK_NOT_CIBO",
        initial_bank_usd="30", initial_cushion_usd="30",
        capital_transfers=[], instructions=instructions,
        managed_settlement_receipts=managed,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--one-authorized-test-trade", action="store_true",
                        help="Synthetic positive control: one EURUSD trade, fabricated 1R exit strictly for interface validation")
    args = parser.parse_args()
    raw = json.loads(args.manifest.read_text())
    if len(raw.get("opportunities", [])) != 3368:
        parser.error("requires sealed 3368 signal manifest")
    args.output.write_text(json.dumps(generate(raw, one_funded=args.one_authorized_test_trade), indent=2, sort_keys=True))
    print("SYNTHETIC_CIBO_CONTRACT_ONLY_NOT_REAL", len(raw["opportunities"]), "one_authorized", args.one_authorized_test_trade)


if __name__ == "__main__":
    main()
