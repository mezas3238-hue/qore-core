#!/usr/bin/env python3
"""Run the non-certifying chronological USD60 CIBO ceiling replay."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ceiling_ablation import CiboCeilingAblationMode
from qore.infrastructure.cibo_function_economic_sensors import (
    summarize_function_sensors,
)
from qore.infrastructure.cibo_single_account_historical_ceiling_epoch import (
    CiboHistoricalProviderAssumption,
)
from qore.infrastructure.cibo_single_account_historical_ceiling_replay import (
    run_historical_ceiling_replay,
)


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _canonical(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _canonical(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--risk-headroom-multiple",
        default="1",
        help="Counterfactual provider risk headroom as multiple of equity.",
    )
    parser.add_argument(
        "--max-risk-multiple",
        default="1",
        help="Counterfactual provider max risk as multiple of equity.",
    )
    parser.add_argument(
        "--margin-capacity-multiple",
        default="100",
        help="Counterfactual provider margin capacity as multiple of equity.",
    )
    parser.add_argument(
        "--active-mll-usd",
        default="0",
        help="Counterfactual provider minimum-loss level.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=100,
    )
    parser.add_argument(
        "--ablation",
        choices=tuple(item.value for item in CiboCeilingAblationMode),
        default=CiboCeilingAblationMode.FULL.value,
        help="Research-only causal ablation mode.",
    )
    args = parser.parse_args()
    if args.progress_every < 0:
        parser.error("--progress-every must be non-negative")

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    assumption = CiboHistoricalProviderAssumption(
        risk_headroom_multiple_of_equity=Decimal(
            args.risk_headroom_multiple
        ),
        max_risk_multiple_of_equity=Decimal(args.max_risk_multiple),
        margin_capacity_multiple_of_equity=Decimal(
            args.margin_capacity_multiple
        ),
        active_mll_usd=Decimal(args.active_mll_usd),
    )

    def progress(payload: dict[str, object]) -> None:
        index = int(payload["epoch_index"])
        total = int(payload["decision_epoch_count"])
        if (
            args.progress_every
            and (index % args.progress_every == 0 or index == total)
        ):
            print(json.dumps(payload, sort_keys=True), file=sys.stderr, flush=True)

    result = run_historical_ceiling_replay(
        manifest,
        provider_assumption=assumption,
        progress_hook=progress,
        ablation_mode=CiboCeilingAblationMode(args.ablation),
    )
    function_sensors = tuple(
        sensor
        for decision in result.decision_receipts
        for sensor in decision.function_sensors
    )
    payload = {
        "schema": "qore.cibo.single-account-historical-ceiling-replay.v1",
        "source_manifest_sha256": result.source_manifest_sha256,
        "ablation_mode": result.ablation_mode.value,
        "decision_epoch_count": result.decision_epoch_count,
        "decision_count": len(result.decision_receipts),
        "settlement_count": len(result.settlement_receipts),
        "ending_capital_usd": format(result.ending_capital_usd, "f"),
        "peak_capital_usd": format(result.peak_capital_usd, "f"),
        "net_pnl_usd": format(result.net_pnl_usd, "f"),
        "external_ai_call_count": result.external_ai_call_count,
        "regime_reconstruction_count": result.regime_reconstruction_count,
        "provider_assumption": _canonical(result.provider_assumption),
        "final_capital": _canonical(result.final_capital),
        "decision_receipts": _canonical(result.decision_receipts),
        "settlement_receipts": _canonical(result.settlement_receipts),
        "function_economic_sensors": summarize_function_sensors(
            function_sensors
        ),
        "governance": {
            "single_account_usd60": True,
            "account_reset_count": result.account_reset_count,
            "economic_era_reset_count": result.economic_era_reset_count,
            "outcome_used_for_predecision": result.outcome_used_for_predecision,
            "external_ai": result.external_ai_call_count != 0,
            "broker_mutation": result.broker_mutation,
            "certification_claimed": result.certification_claimed,
            "provider_plane": "COUNTERFACTUAL_RESEARCH_ASSUMPTION",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "decision_epoch_count": payload["decision_epoch_count"],
                "decision_count": payload["decision_count"],
                "settlement_count": payload["settlement_count"],
                "ending_capital_usd": payload["ending_capital_usd"],
                "peak_capital_usd": payload["peak_capital_usd"],
                "net_pnl_usd": payload["net_pnl_usd"],
                "external_ai_call_count": payload[
                    "external_ai_call_count"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
