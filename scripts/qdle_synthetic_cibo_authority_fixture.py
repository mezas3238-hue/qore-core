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


def generate(manifest: dict) -> dict:
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
    return dict(
        schema="qore.cibo.qdle-authoritative-economic-input.v1",
        provenance="SYNTHETIC_NEGATIVE_CONTROL_ZERO_RISK_NOT_CIBO",
        initial_bank_usd="30", initial_cushion_usd="30",
        capital_transfers=[], instructions=instructions,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads(args.manifest.read_text())
    if len(raw.get("opportunities", [])) != 3368:
        parser.error("requires sealed 3368 signal manifest")
    args.output.write_text(json.dumps(generate(raw), indent=2, sort_keys=True))
    print("SYNTHETIC_CIBO_NEGATIVE_CONTROL_ONLY", len(raw["opportunities"]))


if __name__ == "__main__":
    main()
