#!/usr/bin/env python3
"""Mechanically isolate fresh STI-8 V3 trade rows after frozen reconstruction."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

START = datetime(2026, 7, 22, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 29, 0, 0, tzinfo=UTC)
IDENTITY = "QORE_SHARED_STI8_V3_FRESH_TRADE_FILTER_001"


def _dt(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("signal_at must be timezone-aware")
    return parsed.astimezone(UTC)


def run(source: Path) -> dict[str, object]:
    payload = cast(dict[str, object], json.loads(source.read_text()))
    rows = cast(list[dict[str, object]], payload["trades"])
    selected = [
        row
        for row in rows
        if START <= _dt(row["signal_at"]) < END
    ]
    if not selected:
        raise ValueError("V3 recovery produced no fresh-window trades")
    if any(not (START <= _dt(row["signal_at"]) < END) for row in selected):
        raise AssertionError("fresh trade filter leaked pre-OOS row")
    return {
        "identity": IDENTITY,
        "partition": "sti8_economic_response_v3_oos",
        "trade_count": len(selected),
        "trades": selected,
        "source_reconstruction_trade_count": len(rows),
        "evaluation_window": {
            "opened_at_inclusive": START.isoformat(),
            "checked_at_exclusive": END.isoformat(),
        },
        "filter_is_mechanical": True,
        "policy_selection_used": False,
        "pre_oos_rows_present": False,
        "protected_certification_holdout_opened": False,
        "productive_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "identity": payload["identity"],
        "trade_count": payload["trade_count"],
        "source_reconstruction_trade_count": payload["source_reconstruction_trade_count"],
        "pre_oos_rows_present": payload["pre_oos_rows_present"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
