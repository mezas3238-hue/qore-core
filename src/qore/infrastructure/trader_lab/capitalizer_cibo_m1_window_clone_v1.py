"""Materialize a bounded native-M1 window from the frozen Capitalizer CIBO clone path.

The underlying provider transport, symbol map, raw schema, and no-synthesis guarantees are
identical to capitalizer_cibo_10y_m1_clone_v1. Only the requested historical window changes.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from qore.infrastructure.trader_lab import capitalizer_cibo_10y_m1_clone_v1 as base

IDENTITY = "QORE_CAPITALIZER_CIBO_NATIVE_M1_WINDOW_V1"


def clone_window(
    symbol: str,
    output: Path,
    *,
    start: datetime,
    end_exclusive: datetime,
    role: str,
) -> dict[str, object]:
    if end_exclusive <= start:
        raise ValueError("M1 window end must be after start")
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("M1 window start must be timezone-aware")
    if end_exclusive.tzinfo is None or end_exclusive.utcoffset() is None:
        raise ValueError("M1 window end must be timezone-aware")
    if role not in {"DEVELOPMENT", "FRESH_HOLDOUT"}:
        raise ValueError("role must be DEVELOPMENT or FRESH_HOLDOUT")

    old_start = base.TARGET_START
    old_end = base.TARGET_END_EXCLUSIVE
    try:
        base.TARGET_START = start
        base.TARGET_END_EXCLUSIVE = end_exclusive
        raw_manifest = base.clone_symbol(symbol, output)
    finally:
        base.TARGET_START = old_start
        base.TARGET_END_EXCLUSIVE = old_end

    split_manifest: dict[str, object] = {
        "identity": IDENTITY,
        "role": role,
        "canonical_symbol": symbol,
        "target_start": start.isoformat(),
        "target_end_exclusive": end_exclusive.isoformat(),
        "raw_clone_identity": raw_manifest["identity"],
        "retained_m1": raw_manifest["retained_m1"],
        "provider_native_m1": raw_manifest["provider_native_m1"],
        "synthetic_m1": raw_manifest["synthetic_m1"],
        "interpolated_m1": raw_manifest["interpolated_m1"],
        "read_only": True,
        "methodology_changed": False,
        "entry_timeframe": "M1_NATIVE",
        "m1_mss_required": True,
        "m1_fvg_required": True,
        "m1_order_block_required": True,
        "outcome_used_for_selection": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    (output / "m1-window-manifest.json").write_text(
        json.dumps(split_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return split_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", choices=base.TARGET_SYMBOLS)
    parser.add_argument("output", type=Path)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end-exclusive", required=True)
    parser.add_argument(
        "--role",
        required=True,
        choices=("DEVELOPMENT", "FRESH_HOLDOUT"),
    )
    args = parser.parse_args()

    start = datetime.fromisoformat(args.start)
    end_exclusive = datetime.fromisoformat(args.end_exclusive)
    result = clone_window(
        args.symbol,
        args.output,
        start=start,
        end_exclusive=end_exclusive,
        role=args.role,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
