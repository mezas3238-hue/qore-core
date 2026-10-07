#!/usr/bin/env python3
"""Run the isolated GitHub Trader Lab BANK / MEDIUM / ATTACK experiment."""

from __future__ import annotations

import argparse
import json
from bisect import bisect_left, bisect_right
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.cibo_position_lifecycle import (
    FULL_CIBO_LIFECYCLE_FEATURES,
    CiboLifecycleFeature,
    CiboPositionLifecycleInput,
    run_cibo_position_lifecycle,
)
from qore.infrastructure.cibo_single_account_manifest_economics import (
    manifest_row_provider_cost_per_volume_usd,
)
from qore.infrastructure.cibo_single_account_manifest_settlement import (
    manifest_row_to_shadow_outcome_observation,
)
from qore.infrastructure.trader_lab.cibo_market_atlas_journey_extractor_v1 import (
    load_raw_m5,
)
from qore.infrastructure.trader_lab.cibo_three_mode_capital_lab import (
    run_three_mode_trader_lab,
)

_LIFECYCLE_SYMBOLS = frozenset(
    {"AUDJPY", "EURUSD", "GBPJPY", "GBPUSD", "NAS100", "XAUUSD"}
)


def _lifecycle_roots(values: list[str]) -> dict[str, Path]:
    if not values:
        return {}
    roots: dict[str, Path] = {}
    for value in values:
        symbol, sep, raw = value.partition("=")
        if not sep or symbol not in _LIFECYCLE_SYMBOLS or not raw:
            raise ValueError("lifecycle source root must be supported SYMBOL=PATH")
        if symbol in roots:
            raise ValueError(f"duplicate lifecycle source root: {symbol}")
        roots[symbol] = Path(raw)
    if set(roots) != set(_LIFECYCLE_SYMBOLS):
        raise ValueError("lifecycle custody requires exact six symbol roots")
    return roots


def _build_lifecycle_map(
    manifest: dict[str, object],
    roots: dict[str, Path],
    *,
    features: frozenset[CiboLifecycleFeature],
    adverse_loss_cut_r: Decimal,
) -> dict[str, dict[str, object]]:
    if not roots:
        return {}
    rows = manifest.get("opportunities")
    if not isinstance(rows, list):
        raise ValueError("lifecycle custody requires manifest opportunities")
    bars_by_symbol = {}
    bounds_by_symbol = {}
    for symbol in sorted(_LIFECYCLE_SYMBOLS):
        evidence, _provenance = load_raw_m5(roots[symbol])
        if evidence.symbol != symbol:
            raise ValueError(f"lifecycle Market Atlas identity drift: {symbol}")
        bars_by_symbol[symbol] = evidence.bars
        bounds_by_symbol[symbol] = (
            tuple(item.opened_at for item in evidence.bars),
            tuple(item.closed_at for item in evidence.bars),
        )
    result: dict[str, dict[str, object]] = {}
    for raw in rows:
        if not isinstance(raw, dict):
            raise ValueError("lifecycle manifest row must be mapping")
        signal = str(raw["signal_fingerprint"])
        symbol = str(raw["qore_symbol"])
        opportunity = raw.get("trader_opportunity")
        if not isinstance(opportunity, dict):
            raise ValueError("lifecycle trader opportunity missing")
        outcome = manifest_row_to_shadow_outcome_observation(raw)
        opened, closed = bounds_by_symbol[symbol]
        series = bars_by_symbol[symbol]
        start = bisect_left(opened, outcome.entry_at)
        end = bisect_right(closed, outcome.exit_at)
        managed = run_cibo_position_lifecycle(
            CiboPositionLifecycleInput(
                signal_fingerprint=signal,
                side=str(opportunity["side"]),
                entry_at=outcome.entry_at,
                horizon_at=outcome.exit_at,
                entry_price=Decimal(str(opportunity["intended_entry"])),
                structural_stop=Decimal(str(opportunity["stop_loss"])),
                technical_target=Decimal(str(opportunity["take_profit"])),
                provider_cost_per_volume_usd=(
                    manifest_row_provider_cost_per_volume_usd(raw)
                ),
                stop_risk_per_volume_usd=Decimal(
                    str(opportunity["stop_loss_per_volume"])
                ),
                original_settlement_gross_r=outcome.gross_structural_outcome_r,
            ),
            series[start:end] if start < end else (),
            features=features,
            adverse_loss_cut_r=adverse_loss_cut_r,
        )
        result[signal] = {
            "original_gross_r": format(outcome.gross_structural_outcome_r, "f"),
            "managed_gross_r": format(managed.gross_r, "f"),
            "managed_exit_at": managed.exit_at.isoformat(),
            "data_available": managed.data_available,
            "actions": list(managed.actions),
            "events": managed.events,
            "enabled_features": sorted(item.value for item in features),
            "adverse_loss_cut_r": format(adverse_loss_cut_r, "f"),
            "risk_released_before_exit_fraction": format(
                managed.risk_released_before_exit_fraction, "f"
            ),
            "margin_released_before_exit_fraction": format(
                managed.margin_released_before_exit_fraction, "f"
            ),
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baseline-replay", type=Path)
    parser.add_argument("--historical-manifest", type=Path)
    parser.add_argument("--historical-replay", type=Path)
    parser.add_argument(
        "--lifecycle-source-root",
        action="append",
        default=[],
        help="Post-entry causal Market Atlas source as SYMBOL=PATH.",
    )
    parser.add_argument(
        "--lifecycle-feature",
        action="append",
        choices=[item.value for item in CiboLifecycleFeature],
        default=[],
        help=(
            "Repeat to run a lifecycle ablation. When omitted, the complete "
            "causal lifecycle feature set is enabled."
        ),
    )
    parser.add_argument(
        "--lifecycle-adverse-loss-cut-r",
        type=Decimal,
        default=Decimal("-0.50"),
        help=(
            "Closed-bar deterioration trigger for ADVERSE_LOSS_CUT; the exit "
            "is executed causally at the next M5 open."
        ),
    )
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
        "--distributed-attack-frontier",
        action="store_true",
        help=(
            "Trader-Lab-only ATTACK density experiment: relax ATTACK from "
            "perfect-regime binary gating to a bounded causal escalation "
            "grade while preserving every Trader-executed base entry."
        ),
    )
    parser.add_argument(
        "--attack-multiplier-cap",
        type=int,
        default=8,
        help=(
            "Explicit ATTACK multiplier ceiling for the distributed frontier."
        ),
    )
    parser.add_argument(
        "--medium-multiplier-cap",
        type=int,
        default=4,
        help=(
            "Explicit ordinary MEDIUM intensity ceiling. This does not "
            "reject Trader entries; it limits only CIBO's added intensity."
        ),
    )
    parser.add_argument(
        "--coordinated-economic-group",
        action="store_true",
        help=(
            "Trader-Lab-only joint economics lane: coordinate Sizing, "
            "CIBO Compound, Compound Portfolio and Adaptive Leverage as one "
            "closed-loop capital engine without rejecting Trader entries."
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
    lifecycle_features = (
        frozenset(CiboLifecycleFeature(value) for value in args.lifecycle_feature)
        if args.lifecycle_feature
        else FULL_CIBO_LIFECYCLE_FEATURES
    )
    lifecycle_by_signal = _build_lifecycle_map(
        manifest,
        _lifecycle_roots(args.lifecycle_source_root),
        features=lifecycle_features,
        adverse_loss_cut_r=args.lifecycle_adverse_loss_cut_r,
    )
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
        lifecycle_by_signal=lifecycle_by_signal or None,
        enforce_research_context_abstain=args.enforce_context_abstain,
        soft_medium_drawdown_allocator=(
            args.soft_medium_drawdown_allocator
        ),
        medium_pretrade_drawdown_ceiling=(
            args.medium_pretrade_drawdown_ceiling
        ),
        distributed_attack_frontier=args.distributed_attack_frontier,
        attack_multiplier_cap=args.attack_multiplier_cap,
        medium_multiplier_cap=args.medium_multiplier_cap,
        coordinated_economic_group=args.coordinated_economic_group,
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
                "attack_trade_count": result["attack_trade_count"],
                "attack_density_fraction": result[
                    "attack_density_fraction"
                ],
                "mode_reason_counts": result["mode_reason_counts"],
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
                "trader_results": result["trader_results"],
                "medium_compound_positive_net_usd": result[
                    "medium_compound_positive_net_usd"
                ],
                "medium_compound_negative_net_usd": result[
                    "medium_compound_negative_net_usd"
                ],
                "attack_net_pnl_usd": result["attack_net_pnl_usd"],
                "economic_group_report": result["economic_group_report"],
                "max_drawdown_attribution": result[
                    "max_drawdown_attribution"
                ],
                "position_lifecycle_report": result["position_lifecycle_report"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
