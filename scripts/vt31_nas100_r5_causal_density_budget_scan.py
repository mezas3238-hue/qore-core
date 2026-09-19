"""Focused R5 budget scan around the best causal density policy.

Research-only wrapper. It keeps:
- CORE risk = 1R
- SECONDARY risk = 0.05R
- SCOUT risk = 0.02R
- WAIT release = 10:20 NY
- same causal authorization/fill semantics

Only the monthly alternate-capital budget varies.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

import vt31_nas100_causal_hybrid_density_v2 as density

SCAN_VARIANTS = {
    "WAIT_1020_B075": (10 * 60 + 20, Decimal("0.75")),
    "WAIT_1020_B090": (10 * 60 + 20, Decimal("0.90")),
    "WAIT_1020_B105": (10 * 60 + 20, Decimal("1.05")),
    "WAIT_1020_B120": (10 * 60 + 20, Decimal("1.20")),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    density.VARIANTS = SCAN_VARIANTS
    payload = density.replay(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                name: {
                    "trade_count": item["trade_count"],
                    "tier_counts": item["tier_counts"],
                    "metrics": item["capital_weighted_metrics"],
                    "mc": item["monte_carlo"],
                }
                for name, item in payload["variants"].items()
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
