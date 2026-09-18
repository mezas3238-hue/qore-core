from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.certified_trader_telemetry import (
    LiveWeekObservation,
    compare_live_week,
    compute_weekly_telemetry,
    load_certified_baselines,
    load_jsonl_trades,
    nominal_equity_percent,
)

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_BASELINE = _ROOT / "docs" / "research" / "CERTIFIED-TRADER-WEEKLY-TELEMETRY-v1.json"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="QORE certified-trader weekly frequency/loss telemetry"
    )
    parser.add_argument("--baseline", type=Path, default=_DEFAULT_BASELINE)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("show")

    derive = sub.add_parser("derive")
    derive.add_argument("--ledger", type=Path, required=True)
    derive.add_argument("--window-start", required=True)
    derive.add_argument("--window-end", required=True)
    derive.add_argument("--r-field", default="scaled_net_010_r")

    compare = sub.add_parser("compare")
    compare.add_argument("--trader", required=True)
    compare.add_argument("--entries", required=True, type=int)
    compare.add_argument("--closed-r", required=True)
    compare.add_argument("--worst-day-r", required=True)
    return parser


def _comparison_json(value: Any) -> dict[str, Any]:
    return {
        "trader_id": value.trader_id,
        "entries": value.entries,
        "closed_r": str(value.closed_r),
        "worst_closed_day_r": str(value.worst_closed_day_r),
        "frequency_status": value.frequency_status.value,
        "weekly_loss_status": value.weekly_loss_status.value,
        "daily_loss_status": value.daily_loss_status.value,
        "advisory_only": value.advisory_only,
        "outside_historical_envelope": value.outside_historical_envelope,
    }


def main() -> int:
    args = _parser().parse_args()
    if args.command == "show":
        baselines = load_certified_baselines(args.baseline)
        payload = {
            key: {
                "identity": item.identity,
                "symbol": item.symbol,
                "metrics": item.metrics.as_json(),
            }
            for key, item in sorted(baselines.items())
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.command == "derive":
        trades = load_jsonl_trades(args.ledger, r_field=args.r_field)
        metrics = compute_weekly_telemetry(
            trades,
            window_start=datetime.fromisoformat(args.window_start),
            window_end=datetime.fromisoformat(args.window_end),
        )
        payload: dict[str, Any] = metrics.as_json()
        payload["nominal_worst_day_percent_at_0_20pct_per_1r"] = str(
            nominal_equity_percent(metrics.worst_closed_day_r)
        )
        payload["nominal_worst_week_percent_at_0_20pct_per_1r"] = str(
            nominal_equity_percent(metrics.worst_closed_week_r)
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.command == "compare":
        baselines = load_certified_baselines(args.baseline)
        if args.trader not in baselines:
            raise SystemExit(f"unknown certified trader: {args.trader}")
        result = compare_live_week(
            baselines[args.trader],
            LiveWeekObservation(
                entries=args.entries,
                closed_r=Decimal(args.closed_r),
                worst_closed_day_r=Decimal(args.worst_day_r),
            ),
        )
        print(json.dumps(_comparison_json(result), indent=2, sort_keys=True))
        return 0

    raise AssertionError("unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())
