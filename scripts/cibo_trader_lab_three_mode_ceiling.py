#!/usr/bin/env python3
"""Run the isolated GitHub Trader Lab BANK / MEDIUM / ATTACK experiment."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.cibo_three_mode_capital_lab import (
    run_three_mode_trader_lab,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baseline-replay", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    baseline = None
    cognitive_recommend_by_signal = None
    if args.baseline_replay is not None:
        payload = json.loads(
            args.baseline_replay.read_text(encoding="utf-8")
        )
        baseline = Decimal(str(payload["ending_capital_usd"]))
        decisions = payload.get("decision_receipts")
        if not isinstance(decisions, list):
            raise ValueError("baseline replay decision receipts missing")
        cognitive_recommend_by_signal = {
            str(item["signal_fingerprint"]): (
                str(item["capital_disposition"]) != "COGNITIVE_BLOCK"
            )
            for item in decisions
        }

    result = run_three_mode_trader_lab(
        manifest,
        baseline_ending_capital_usd=baseline,
        cognitive_recommend_by_signal=cognitive_recommend_by_signal,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "decision_count": result["decision_count"],
                "decision_epoch_count": result["decision_epoch_count"],
                "ending_total_capital_usd": result[
                    "ending_total_capital_usd"
                ],
                "ending_sovereign_bank_usd": result[
                    "ending_sovereign_bank_usd"
                ],
                "ending_portfolio_cushion_usd": result[
                    "ending_portfolio_cushion_usd"
                ],
                "max_drawdown_fraction": result[
                    "max_drawdown_fraction"
                ],
                "mode_epoch_counts": result["mode_epoch_counts"],
                "trade_mode_counts": result["trade_mode_counts"],
                "maximum_selected_multiplier": result[
                    "maximum_selected_multiplier"
                ],
                "attack_sovereign_breach_usd": result[
                    "attack_sovereign_breach_usd"
                ],
                "delta_vs_baseline_ending_capital_usd": result[
                    "delta_vs_baseline_ending_capital_usd"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
