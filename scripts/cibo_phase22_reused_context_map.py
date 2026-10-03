#!/usr/bin/env python3
"""Reconstruct predecision Trader context for reused-holdout Phase22 research.

This utility never changes the sealed Phase22 batch or its fresh/certification
lineage. It creates a separate research-only context map by deterministically
joining the already-consumed batch to the original native Trader artifacts.

Only the canonical allowlisted context extractor is used. Outcome/exit/PnL
fields are not copied into the context map.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_phase22_fresh_opportunity_batch import (
    predecision_context_from_native_row,
)

FILES = {
    "R34_XAUUSD": "phase18-xauusd-r34-geometry-trades.jsonl",
    "R38_EURUSD": "phase18-eurusd-r38-geometry-trades.jsonl",
    "R43_GBPUSD": "phase18-gbpusd-r39-geometry-trades.jsonl",
    "R38_GBPJPY": "phase18-gbpjpy-r37-geometry-trades.jsonl",
    "R42_AUDJPY": "phase18-audjpy-r40-geometry-trades.jsonl",
}
FORBIDDEN_KEY_PARTS = (
    "exit",
    "realized",
    "outcome",
    "pnl",
    "raw_net",
    "scaled_net",
)


def _canon_decimal(value: object) -> str:
    parsed = Decimal(str(value))
    if not parsed.is_finite():
        raise RuntimeError("context reconstruction decimal must be finite")
    return format(parsed, "f")


def _key_from_batch(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(row["signal_at"]),
        str(row["side"]),
        _canon_decimal(row["entry_price"]),
        _canon_decimal(row["structural_stop"]),
        _canon_decimal(row["technical_target"]),
    )


def _key_from_native(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(row["signal_at"]),
        str(row["side"]),
        _canon_decimal(row["entry_price"]),
        _canon_decimal(row["structural_stop"]),
        _canon_decimal(row["technical_target"]),
    )


def _load_native(root: Path) -> dict[str, dict[tuple[str, ...], dict[str, Any]]]:
    out: dict[str, dict[tuple[str, ...], dict[str, Any]]] = {}
    for trader_id, file_name in FILES.items():
        paths = tuple(root.rglob(file_name))
        if len(paths) != 1:
            raise RuntimeError(
                f"{trader_id} native context file must be unique: {len(paths)}"
            )
        rows = [
            json.loads(line)
            for line in paths[0].read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if any(not isinstance(row, dict) for row in rows):
            raise RuntimeError(f"{trader_id} native context row must be object")
        indexed = {_key_from_native(row): row for row in rows}
        if len(indexed) != len(rows):
            raise RuntimeError(f"{trader_id} native context key collision")
        out[trader_id] = indexed
    return out


def build_context_map(
    *,
    batch: dict[str, Any],
    native_root: Path,
) -> dict[str, Any]:
    if batch.get("validation_mode") != "NON_CERTIFYING_REUSED_HOLDOUT":
        raise RuntimeError("reused-holdout batch required")
    if batch.get("schema") != "qore.cibo.phase22.v4-fresh-batch-assembly.v1":
        raise RuntimeError("unexpected Phase22 V4 batch schema")
    opportunities = batch.get("opportunities")
    if not isinstance(opportunities, list) or not opportunities:
        raise RuntimeError("non-empty Phase22 opportunity population required")

    native = _load_native(native_root)
    rows: dict[str, dict[str, Any]] = {}
    matched_by_trader = {name: 0 for name in FILES}
    for raw in opportunities:
        if not isinstance(raw, dict):
            raise RuntimeError("Phase22 opportunity row must be object")
        trader_id = str(raw["trader_id"])
        if trader_id not in native:
            continue
        native_row = native[trader_id].get(_key_from_batch(raw))
        if native_row is None:
            raise RuntimeError(
                "native context join failed for "
                f"{trader_id}:{raw['signal_fingerprint']}"
            )
        context = predecision_context_from_native_row(native_row)
        if not context:
            raise RuntimeError(
                f"native context unexpectedly empty: {trader_id}"
            )
        if any(
            any(token in key.lower() for token in FORBIDDEN_KEY_PARTS)
            for key, _ in context
        ):
            raise RuntimeError("outcome field leaked into reconstructed context")
        signal = str(raw["signal_fingerprint"])
        if signal in rows:
            raise RuntimeError("duplicate Phase22 signal in context map")
        rows[signal] = {
            "trader_id": trader_id,
            "decision_context": [[key, value] for key, value in context],
        }
        matched_by_trader[trader_id] += 1

    matched = sum(matched_by_trader.values())
    if matched != 486:
        raise RuntimeError(
            f"expected exact 486 Turtle context joins, observed {matched}"
        )

    return {
        "schema": "qore.cibo.phase22.reused-context-map.v1",
        "mode": "NON_CERTIFYING_REUSED_HOLDOUT",
        "source_batch_sha256": str(batch["batch_sha256"]),
        "source_opportunity_count": len(opportunities),
        "matched_turtle_opportunity_count": matched,
        "matched_by_trader": matched_by_trader,
        "context_rows": rows,
        "governance": {
            "source_batch_mutated": False,
            "fresh_oos_claimed": False,
            "certification_claimed": False,
            "outcome_fields_used_for_context": False,
            "broker_mutation": False,
            "live": False,
            "production": False,
            "real_capital": False,
            "merge_authority": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--native-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    batch = json.loads(args.batch.read_text(encoding="utf-8"))
    if not isinstance(batch, dict):
        raise RuntimeError("Phase22 batch root must be object")
    report = build_context_map(batch=batch, native_root=args.native_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "source_batch_sha256": report["source_batch_sha256"],
                "matched_turtle_opportunity_count": (
                    report["matched_turtle_opportunity_count"]
                ),
                "matched_by_trader": report["matched_by_trader"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
