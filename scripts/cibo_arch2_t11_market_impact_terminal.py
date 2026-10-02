"""Build immutable Architect-2 T11 terminal receipt from one sealed report."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_arch2_t11_market_impact_terminal_receipt import (
    build_t11_market_impact_terminal_receipt,
)


def build_terminal_payload(report: dict[str, Any]) -> dict[str, object]:
    receipt = build_t11_market_impact_terminal_receipt(report)
    payload = asdict(receipt)
    payload["four_of_four_by_symbol"] = [
        [symbol, passed]
        for symbol, passed in receipt.four_of_four_by_symbol
    ]
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    raw = json.loads(args.report.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError("T11 market-impact report must be a JSON object")
    payload = build_terminal_payload(raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
