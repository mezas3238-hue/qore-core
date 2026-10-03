#!/usr/bin/env python3
"""Stop/continue sensor for the CIBO Trader Lab 3x1Y adaptive research harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.trader_lab.cibo_three_holdout_1y_contract import (
    evaluate_three_groups,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--group1", type=Path, required=True)
    parser.add_argument("--group2", type=Path, required=True)
    parser.add_argument("--group3", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payloads = tuple(
        json.loads(path.read_text(encoding="utf-8"))
        for path in (args.group1, args.group2, args.group3)
    )
    result = evaluate_three_groups(payloads)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
