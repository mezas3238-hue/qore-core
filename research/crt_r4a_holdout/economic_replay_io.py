"""SHA-pinned offline signal+bid/ask+cost input contract and economic QA output.

Command-line input consists solely of local files. Manifest hashes make replay
reproducible but do NOT prove IC Markets origin, Pine parity or unseen holdout.
No broker/API/network operation and no financial certification is possible here.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from research.crt_r4a_holdout.economic_replay import (
    SOURCE_PINE,
    FrozenResearchSignal,
    QuoteEvidence,
    replay_symbol,
)
from research.crt_r4a_holdout.paper_quote_execution import (
    BidAskM5,
    CostAssumptions,
    SwapDebit,
)
from research.crt_r4a_holdout.seven_family_contract import Family
from research.crt_r4a_holdout.seven_family_paper_plan import MarketGeometry

QUOTE_COLS = (
    "opened_at", "bid_open", "bid_high", "bid_low", "bid_close",
    "ask_open", "ask_high", "ask_low", "ask_close"
)
SWAP_COLS = ("charged_at", "quote_amount_per_unit")


def instant(text: str) -> datetime:
    at = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if at.tzinfo is None:
        raise ValueError("source timestamps MUST include UTC offset")
    return at


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _csv_rows(path: Path, required: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None or not set(required) <= set(reader.fieldnames):
            raise ValueError(f"missing required CSV columns: {path.name}")
        rows = list(reader)
    if any(any(not row.get(column) for column in required) for row in rows):
        raise ValueError(f"missing source field in {path.name}")
    return rows


def _geometry(raw: dict[str, Any]) -> MarketGeometry:
    required = (
        "c1_high", "c1_low", "setup_open", "setup_close",
        "sweep_high", "sweep_low"
    )
    kw: dict[str, Any] = {k: Decimal(raw[k]) for k in required}
    for name in ("retest_high", "retest_low", "retest_close"):
        if raw.get(name) is not None:
            kw[name] = Decimal(raw[name])
    if raw.get("retest_closed_at") is not None:
        kw["retest_closed_at"] = instant(raw["retest_closed_at"])
    return MarketGeometry(**kw)


def load_and_replay(
    *, manifest: Path, signals: Path, quotes: Path,
    costs: Path, swaps: Path, quantity: Decimal,
) -> dict[str, Any]:
    data = json.loads(manifest.read_text(encoding="utf-8"))
    hashes = data["sha256"]
    for key, file in (
        ("signals", signals), ("quotes", quotes),
        ("costs", costs), ("swaps", swaps)
    ):
        if hashes.get(key) != digest(file):
            raise ValueError(f"{key}: declared SHA256 differs from file bytes")
    if data["source_pine_blob"] != SOURCE_PINE:
        raise ValueError("Pine R4-A source hash mismatch")
    symbol = data["symbol"]
    provider = data["provider_cohort"]
    raw_signals = json.loads(signals.read_text(encoding="utf-8"))
    if not isinstance(raw_signals, list):
        raise ValueError("signals require JSON array")
    frozen = []
    for item in raw_signals:
        frozen.append(FrozenResearchSignal(
            symbol=item["symbol"],
            provider_cohort=item["provider_cohort"],
            family=Family(item["family"]),
            source_event_id=item["source_event_id"],
            direction=item["direction"],
            mss_at=instant(item["mss_at"]),
            ratified_at=instant(item["ratified_at"]),
            available_at=instant(item["available_at"]),
            geometry=_geometry(item["geometry"]),
            atr_h4=Decimal(item["atr_h4"]),
            price_tick=Decimal(item["price_tick"]),
            source_pine_blob=item["source_pine_blob"],
        ))
    bars = tuple(
        BidAskM5(
            instant(row["opened_at"]),
            *(Decimal(row[k]) for k in QUOTE_COLS[1:]),
        )
        for row in _csv_rows(quotes, QUOTE_COLS)
    )
    raw_costs = json.loads(costs.read_text(encoding="utf-8"))
    contract = CostAssumptions(
        Decimal(raw_costs["commission_per_unit_per_side_quote"]),
        Decimal(raw_costs["adverse_slippage_price"]),
    )
    swap_items = tuple(
        SwapDebit(instant(row["charged_at"]), Decimal(row["quote_amount_per_unit"]))
        for row in _csv_rows(swaps, SWAP_COLS)
    )
    evidence = QuoteEvidence(
        symbol=symbol, provider_cohort=provider,
        bars=bars, cost_assumptions=contract,
        swaps=swap_items, quote_source_sha256=digest(quotes),
    )
    result = replay_symbol(tuple(frozen), evidence, quantity=quantity)
    return {
        "status": result.status,
        "symbol": symbol,
        "provider_cohort": provider,
        "quote_source_sha256": digest(quotes),
        "signal_source_sha256": digest(signals),
        "pine_source_blob": SOURCE_PINE,
        "manifest_integrity_checked": True,
        "provider_identity_independently_certified": False,
        "verified_account_currency_pnl": False,
        "original_pine_event_parity": False,
        "unseen_24m_holdout": False,
        "broker_orders_executed": 0,
        "unit": "QUOTE_PRICE_TIMES_SUPPLIED_QUANTITY_NOT_ACCOUNT_USD",
        "by_family": {
            family: asdict(metrics)
            for family, metrics in result.by_family.items()
        },
        "all_families": asdict(result.all_families),
        "ledger": [
            {
                "family": row.family.value,
                "event_id": row.source_event_id,
                "available_at": row.signal_at.isoformat(),
                "status": row.status,
                "reason": row.reason,
                "entry_at": (
                    row.result.entry_at.isoformat()
                    if row.result and row.result.entry_at else None
                ),
                "exit_at": (
                    row.result.exit_at.isoformat()
                    if row.result and row.result.exit_at else None
                ),
                "net_quote": row.result.net_quote if row.result else None,
                "net_r": row.result.net_r if row.result else None,
            }
            for row in result.observations
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for key in ("manifest", "signals", "quotes", "costs", "swaps", "out"):
        parser.add_argument("--" + key, required=True, type=Path)
    parser.add_argument("--quantity", required=True, type=Decimal)
    args = parser.parse_args()
    result = load_and_replay(
        manifest=args.manifest, signals=args.signals, quotes=args.quotes,
        costs=args.costs, swaps=args.swaps, quantity=args.quantity,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, indent=2, default=str, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": result["status"],
        "symbol": result["symbol"],
        "observations": len(result["ledger"]),
        "net_is_account_currency": False,
        "certified": False,
    }))


if __name__ == "__main__":
    main()
