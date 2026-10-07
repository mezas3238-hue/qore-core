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
    parser.add_argument("--historical-manifest", type=Path)
    parser.add_argument("--historical-replay", type=Path)
    parser.add_argument(
        "--soft-medium-drawdown-allocator",
        action="store_true",
        help=(
            "Trader-Lab-only frontier hypothesis: replace MEDIUM's hard "
            "worst-case 25% headroom wall with the existing causal "
            "drawdown-scaled risk allocator; realized DD is still measured."
        ),
    )
    parser.add_argument(
        "--medium-pretrade-drawdown-ceiling",
        type=Decimal,
        default=Decimal("0.25"),
        help=(
            "Trader-Lab-only MEDIUM reserve frontier: pre-trade worst-case "
            "drawdown ceiling. Realized DD must still remain <=0.25."
        ),
    )
    parser.add_argument(
        "--medium-open-risk-stress-weight",
        type=Decimal,
        default=Decimal("1"),
        help=(
            "Trader-Lab-only MEDIUM concurrency stress factor applied to "
            "currently open stop risk inside the 25% pre-trade drawdown wall."
        ),
    )
    parser.add_argument(
        "--selective-recovery-headroom-ceiling",
        type=Decimal,
        help=(
            "Trader-Lab-only recovery frontier: grant extra MEDIUM pre-trade "
            "headroom only to context ALLOW plus 5/5 positive causal "
            "walk-forward blocks. Realized DD must still remain <=0.25."
        ),
    )
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
    native_profile_by_signal = None
    historical_prior_by_signal = None
    if args.baseline_replay is not None:
        payload = json.loads(
            args.baseline_replay.read_text(encoding="utf-8")
        )
        baseline = Decimal(str(payload["ending_capital_usd"]))
        decisions = payload.get("decision_receipts")
        if not isinstance(decisions, list):
            raise ValueError("baseline replay decision receipts missing")
        cognitive_recommend_by_signal = {}
        native_profile_by_signal = {}
        for item in decisions:
            signal = str(item["signal_fingerprint"])
            sensors = item.get("cognitive_sensors")
            if not isinstance(sensors, list):
                raise ValueError("baseline cognitive sensors missing")
            by_code = {
                str(sensor.get("component_code")): sensor
                for sensor in sensors
                if isinstance(sensor, dict)
            }
            required = {
                "EXECUTIVE_SYNTHESIS",
                "REASONING_ROUTING",
                "CALIBRATION",
                "SCENARIO_ENGINE",
                "METACOGNITION",
                "ATTENTION_CONTEXT",
            }
            if not required.issubset(by_code):
                raise ValueError(
                    "baseline cognitive sensor surface incomplete"
                )

            def metrics(code: str) -> dict[str, str]:
                raw = by_code[code].get("output_metrics")
                if not isinstance(raw, list):
                    raise ValueError(
                        f"cognitive output metrics malformed for {code}"
                    )
                return {
                    str(pair[0]): str(pair[1])
                    for pair in raw
                    if isinstance(pair, list) and len(pair) == 2
                }

            executive = str(by_code["EXECUTIVE_SYNTHESIS"].get("status"))
            calibration = metrics("CALIBRATION")
            scenario = metrics("SCENARIO_ENGINE")
            attention = metrics("ATTENTION_CONTEXT")
            recommended = executive == "recommend"
            cognitive_recommend_by_signal[signal] = recommended
            native_profile_by_signal[signal] = {
                "executive_synthesis": executive,
                "reasoning_routing": str(
                    by_code["REASONING_ROUTING"].get("status")
                ),
                "calibration": str(
                    by_code["CALIBRATION"].get("status")
                ),
                "confidence_band": int(
                    calibration.get("confidence_band", "0")
                ),
                "scenario_abstained_count": int(
                    scenario.get("abstained_count", "0")
                ),
                "metacognition": str(
                    by_code["METACOGNITION"].get("status")
                ),
                "attention_ranked_signal_count": int(
                    attention.get("ranked_signal_count", "0")
                ),
                "native_maximum_intelligence": bool(
                    item.get("native_maximum_intelligence", False)
                ),
                "full_semantics_consumed": bool(
                    item.get("full_semantics_consumed", False)
                ),
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
            if not isinstance(row, dict):
                raise ValueError("historical prior row must be mapping")
            signal = str(row.get("signal_fingerprint", ""))
            if not signal:
                raise ValueError("historical signal fingerprint missing")
            expectation = row.get("expectation")
            context_quality = row.get("context_quality")
            if not isinstance(expectation, dict):
                raise ValueError("historical expectation missing")
            if not isinstance(context_quality, dict):
                raise ValueError("historical context quality missing")
            if expectation.get("basis") != "FROZEN_HISTORICAL_PRIOR":
                raise ValueError("historical prior basis drift")
            for flag in (
                "future_market_used",
                "outcome_used",
                "pnl_used",
                "post_entry_path_used",
            ):
                if expectation.get(flag) is not False:
                    raise ValueError(
                        f"historical prior violates causal flag {flag}"
                    )
            if context_quality.get("causal_predecision") is not True:
                raise ValueError(
                    "historical context is not causal predecision"
                )
            if context_quality.get("outcome_used") is not False:
                raise ValueError(
                    "historical context cannot consume outcome"
                )
            if row.get("outcome_available_to_predecision") is not False:
                raise ValueError(
                    "historical row exposes outcome to predecision"
                )
            expected_net = Decimal(
                str(expectation["expected_net_value_usd"])
            )
            expected_minutes = Decimal(
                str(expectation["expected_capital_minutes"])
            )
            if (
                not expected_net.is_finite()
                or not expected_minutes.is_finite()
                or expected_minutes <= 0
            ):
                raise ValueError("historical prior numeric evidence malformed")
            disposition = str(context_quality.get("disposition", ""))
            if disposition not in {"ALLOW", "ABSTAIN"}:
                raise ValueError(
                    "historical context disposition is invalid"
                )
            historical_prior_by_signal[signal] = {
                # The frozen prior already stores the causal expected net
                # economic value used by the historical Portfolio engine.
                # Do not reinterpret it through the newer walk-forward parser:
                # that parser requires metadata introduced after this artifact.
                "expected_edge_after_cost_usd": format(expected_net, "f"),
                "expected_capital_minutes": format(
                    expected_minutes, "f"
                ),
                "context_allowed": disposition == "ALLOW",
            }

    if args.historical_replay is not None:
        if historical_prior_by_signal is None:
            raise ValueError(
                "historical replay requires historical manifest"
            )
        control = json.loads(
            args.historical_replay.read_text(encoding="utf-8")
        )
        if control.get("governance", {}).get(
            "outcome_used_for_predecision"
        ) is not False:
            raise ValueError(
                "historical control violates predecision causality"
            )
        control_decisions = control.get("decision_receipts")
        control_settlements = control.get("settlement_receipts")
        if not isinstance(control_decisions, list) or not isinstance(
            control_settlements, list
        ):
            raise ValueError("historical control receipts missing")

        settlements = sorted(
            control_settlements,
            key=lambda item: (
                str(item["settled_at"]),
                str(item["signal_fingerprint"]),
            ),
        )
        running_capital = Decimal("60")
        settlement_index = 0
        for decision in sorted(
            control_decisions,
            key=lambda item: (
                str(item["decided_at"]),
                str(item["signal_fingerprint"]),
            ),
        ):
            decided_at = str(decision["decided_at"])
            while (
                settlement_index < len(settlements)
                and str(settlements[settlement_index]["settled_at"])
                <= decided_at
            ):
                running_capital += Decimal(
                    str(
                        settlements[settlement_index][
                            "realized_net_pnl_usd"
                        ]
                    )
                )
                settlement_index += 1

            signal = str(decision["signal_fingerprint"])
            if signal not in historical_prior_by_signal:
                raise ValueError(
                    "historical control signal absent from manifest prior"
                )
            if decision.get("outcome_used_for_predecision") is not False:
                raise ValueError(
                    "historical decision exposes outcome to predecision"
                )
            authorized_risk = Decimal(
                str(decision["authorized_stop_risk_usd"])
            )
            if authorized_risk < 0 or running_capital <= 0:
                raise ValueError(
                    "historical control capital/risk malformed"
                )
            control_ready = (
                str(decision["capital_disposition"])
                == "RISK_REVIEW_READY"
                and str(decision["risk_decision"]) == "ALLOW"
                and authorized_risk > 0
            )
            historical_prior_by_signal[signal].update(
                {
                    "historical_control_ready": control_ready,
                    "historical_authorized_stop_risk_usd": format(
                        authorized_risk, "f"
                    ),
                    "historical_realized_capital_predecision_usd": format(
                        running_capital, "f"
                    ),
                    "historical_stop_risk_fraction": format(
                        (
                            authorized_risk / running_capital
                            if authorized_risk > 0
                            else Decimal(0)
                        ),
                        "f",
                    ),
                    "historical_adaptive_leverage_multiplier": int(
                        decision["adaptive_leverage_multiplier"]
                    ),
                }
            )

        if set(historical_prior_by_signal) != {
            str(item["signal_fingerprint"])
            for item in control_decisions
        }:
            raise ValueError(
                "historical control/prior signal surface drift"
            )

    result = run_three_mode_trader_lab(
        manifest,
        baseline_ending_capital_usd=baseline,
        cognitive_recommend_by_signal=cognitive_recommend_by_signal,
        native_profile_by_signal=native_profile_by_signal,
        historical_prior_by_signal=historical_prior_by_signal,
        enforce_research_context_abstain=args.enforce_context_abstain,
        soft_medium_drawdown_allocator=(
            args.soft_medium_drawdown_allocator
        ),
        medium_pretrade_drawdown_ceiling=(
            args.medium_pretrade_drawdown_ceiling
        ),
        selective_recovery_headroom_ceiling=(
            args.selective_recovery_headroom_ceiling
        ),
        medium_open_risk_stress_weight=(
            args.medium_open_risk_stress_weight
        ),
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
