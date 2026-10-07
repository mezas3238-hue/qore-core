#!/usr/bin/env python3
"""Run the isolated GitHub Trader Lab BANK / MEDIUM / ATTACK experiment."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.cibo_capital_management_authority import (
    minimum_seed_volume,
)
from qore.infrastructure.cibo_single_account_manifest_economics import (
    manifest_row_provider_cost_per_volume_usd,
    manifest_row_to_ceiling_opportunity_evidence,
)
from qore.infrastructure.trader_lab.cibo_three_mode_capital_lab import (
    run_three_mode_trader_lab,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baseline-replay", type=Path)
    parser.add_argument("--historical-manifest", type=Path)
    parser.add_argument(
        "--enforce-context-abstain",
        action="store_true",
        help=(
            "Trader-Lab-only post-burn hypothesis: treat the pre-existing "
            "research context-quality ABSTAIN as no-deployment. This lane "
            "requires genuinely fresh validation before any promotion."
        ),
    )
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    baseline = None
    cognitive_recommend_by_signal = None
    historical_prior_by_signal = None
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

    if args.historical_manifest is not None:
        historical = json.loads(
            args.historical_manifest.read_text(encoding="utf-8")
        )
        historical_rows = historical.get("opportunities")
        if not isinstance(historical_rows, list) or not historical_rows:
            raise ValueError("historical prior manifest opportunities missing")
        historical_prior_by_signal = {}
        for row in historical_rows:
            evidence = manifest_row_to_ceiling_opportunity_evidence(row)
            opportunity = evidence.opportunity
            minimum = minimum_seed_volume(opportunity)
            provider_cost = (
                minimum * manifest_row_provider_cost_per_volume_usd(row)
            )
            context_quality = row.get("context_quality")
            if not isinstance(context_quality, dict):
                raise ValueError("historical context quality missing")
            historical_prior_by_signal[opportunity.signal_fingerprint] = {
                "expected_edge_after_cost_usd": format(
                    evidence.expected_net_value_usd - provider_cost,
                    "f",
                ),
                "expected_capital_minutes": format(
                    evidence.expected_capital_minutes,
                    "f",
                ),
                "context_allowed": bool(
                    evidence.context_allowed
                    and evidence.provider_viable
                    and evidence.capital_source_eligible
                    and context_quality.get("disposition") == "ALLOW"
                ),
            }

    result = run_three_mode_trader_lab(
        manifest,
        baseline_ending_capital_usd=baseline,
        cognitive_recommend_by_signal=cognitive_recommend_by_signal,
        historical_prior_by_signal=historical_prior_by_signal,
        enforce_research_context_abstain=args.enforce_context_abstain,
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
                "research_lane": result["research_lane"],
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
                "engineering_trace_event_count": result[
                    "engineering_sensor_report"
                ]["trace_event_count"],
                "execution_funnel": result[
                    "engineering_sensor_report"
                ]["execution_funnel"],
                "upstream_economic_intake": result[
                    "engineering_sensor_report"
                ]["upstream_economic_intake"],
                "economic_bottleneck_ranking": result[
                    "engineering_sensor_report"
                ]["bottleneck_ranking"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
