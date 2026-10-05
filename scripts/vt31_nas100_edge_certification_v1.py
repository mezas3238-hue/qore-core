"""CLI for VT31 NAS100 edge-only certification development reports.

The input is an already-consumed replay JSON containing terminal trade rows.
This command does not acquire market data, open holdouts, scan policies, size
positions, or authorize execution.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.traders.vt31_nas100_edge_certification import (
    build_edge_only_report,
)


def _load_trades(path: Path, *, market: str) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("trades")
    if not isinstance(raw, list):
        raise ValueError("replay JSON must contain a trades list")

    trades: list[dict[str, object]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("every replay trade must be an object")
        if item.get("market", market) != market:
            continue
        if "r_multiple" not in item:
            continue
        trades.append(dict(item))
    return trades


def build(
    replay_path: Path,
    *,
    market: str = "NAS100",
    friction_r: Decimal = Decimal("0"),
    baseline_path: Path | None = None,
    monte_carlo_paths: int = 10_000,
) -> dict[str, object]:
    trades = _load_trades(replay_path, market=market)
    baseline = (
        None
        if baseline_path is None
        else _load_trades(baseline_path, market=market)
    )
    report = build_edge_only_report(
        trades,
        baseline_rows=baseline,
        friction_r=friction_r,
        monte_carlo_paths=monte_carlo_paths,
    )
    report["source_replay"] = replay_path.name
    report["source_trade_count"] = len(trades)
    report["source_market_filter"] = market
    report["source_replay_used_for_policy_selection"] = False
    report["research_only"] = True
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("replay", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--market", default="NAS100")
    parser.add_argument("--friction-r", type=Decimal, default=Decimal("0"))
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--monte-carlo-paths", type=int, default=10_000)
    args = parser.parse_args()

    payload = build(
        args.replay,
        market=args.market,
        friction_r=args.friction_r,
        baseline_path=args.baseline,
        monte_carlo_paths=args.monte_carlo_paths,
    )
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "source_trade_count": payload["source_trade_count"],
                "metrics": payload["metrics"],
                "gates": payload["gates"],
                "candidate_certified": payload["candidate_certified"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
