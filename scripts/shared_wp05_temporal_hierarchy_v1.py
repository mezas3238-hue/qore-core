"""WP-05 consumed-development temporal hierarchy falsification lab.

R8 is used to fit a compact hierarchy readout and freeze its declaration
threshold. R6 and R5 are later consumed partitions used only for development
falsification. No fresh holdout is opened here.

The task is deliberately narrow and aligned with WP-05:
when local scales oppose the higher-timeframe state, distinguish temporary
pullback from genuine terminal structural failure.

Baseline:
    every local-vs-higher opposition is declared structural failure.

Hierarchy:
    continuous M1/M3/M5/M15/H1/H4/D1 state plus cross-level propagation and
    higher-timeframe resilience/fragility are used by one frozen probabilistic
    readout.

Exit-development gate:
    on BOTH R6 and R5, reduce false structural-failure declarations by at
    least 20% while preserving at least 95% of baseline terminal detections.

Passing this lab does not close WP-05. It only permits a newly preregistered
fresh holdout with the exact frozen model.
"""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
from typing import Any

from shared_wp03_historical_causal_discovery import (
    MARKETS,
    SAMPLE_MINUTES,
    TARGET_HORIZON_MINUTES,
    _load_bars,
    _metric,
    _parse_key,
    _sign,
)

from qore.infrastructure.core_stack_v2.hierarchical_world_model import WorldScale
from qore.infrastructure.core_stack_v2.temporal_hierarchy_engine import (
    TemporalHierarchyEvaluation,
    TemporalHierarchySnapshot,
    TemporalHierarchyTrainingEpisode,
    TemporalScaleState,
    evaluate_temporal_hierarchy,
    fit_temporal_hierarchy_model,
)

SCHEMA = "qore.shared.wp05.temporal_hierarchy_consumed_v1"
IDENTITY = "QORE_SHARED_WP05_TEMPORAL_HIERARCHY_V1_001"
PARTITIONS = ("r8", "r6", "r5")

SCALE_HORIZONS: tuple[tuple[WorldScale, int], ...] = (
    (WorldScale.M1, 1),
    (WorldScale.M3, 3),
    (WorldScale.M5, 5),
    (WorldScale.M15, 15),
    (WorldScale.H1, 60),
    (WorldScale.H4, 240),
    (WorldScale.DAILY, 1_440),
)
MAX_LOOKBACK = max(horizon for _scale, horizon in SCALE_HORIZONS)

MINIMUM_EPISODES = 6_000
MINIMUM_BASELINE_TERMINALS = 50
MINIMUM_FALSE_REDUCTION_BPS = 2_000
MINIMUM_TERMINAL_PRESERVATION_BPS = 9_500


def _clamp_bps(value: float) -> int:
    return max(0, min(10_000, int(round(value))))


def _signed_efficiency(rows: tuple[Any, ...]) -> float:
    if not rows:
        raise ValueError("signed efficiency requires closed bars")
    if len(rows) == 1:
        bar = rows[0]
        width = max(0.0, float(bar.high) - float(bar.low))
        body = float(bar.close) - float(bar.opened)
        if width <= 0.0:
            return 0.0
        return max(-1.0, min(1.0, body / width))
    metric = _metric(rows)
    sign = _sign(metric.net_bps)
    return float(sign) * float(metric.efficiency)


def _scale_state(
    *,
    scale: WorldScale,
    horizon: int,
    windows: dict[str, tuple[Any, ...]],
) -> TemporalScaleState:
    primary_rows = windows["NAS100"][-horizon:]
    signed_eff = _signed_efficiency(primary_rows)
    primary_metric = None if horizon == 1 else _metric(primary_rows)
    primary_efficiency = (
        abs(signed_eff)
        if primary_metric is None
        else float(primary_metric.efficiency)
    )
    direction_milli = int(
        round(max(-1.0, min(1.0, signed_eff)) * 1_000)
    )

    if horizon <= 1:
        persistence = abs(signed_eff)
    else:
        if primary_metric is None:
            raise AssertionError("multi-bar scale requires metric")
        short = max(1, horizon // 3)
        medium = max(short, (2 * horizon) // 3)
        full_sign = _sign(primary_metric.net_bps)
        tail_metrics = (
            _metric(primary_rows[-short:]),
            _metric(primary_rows[-medium:]),
            primary_metric,
        )
        persistence = sum(
            metric.efficiency
            * float(
                full_sign != 0
                and _sign(metric.net_bps) == full_sign
            )
            for metric in tail_metrics
        ) / len(tail_metrics)

    peer_signed = [
        _signed_efficiency(windows[market][-horizon:])
        for market in MARKETS
    ]
    primary_signal = peer_signed[0]
    coherence = sum(
        (1.0 + primary_signal * signal) / 2.0
        for signal in peer_signed[1:]
    ) / max(1, len(peer_signed) - 1)

    recent_horizon = max(1, horizon // 4)
    recent_signed = _signed_efficiency(primary_rows[-recent_horizon:])
    alignment = max(-1.0, min(1.0, signed_eff * recent_signed))
    fragility = (1.0 - alignment) / 2.0
    transition = min(1.0, abs(recent_signed - signed_eff) / 2.0)

    return TemporalScaleState(
        scale=scale,
        direction_milli=direction_milli,
        persistence_bps=_clamp_bps(persistence * 10_000.0),
        coherence_bps=_clamp_bps(coherence * 10_000.0),
        efficiency_bps=_clamp_bps(primary_efficiency * 10_000.0),
        fragility_bps=_clamp_bps(fragility * 10_000.0),
        transition_bps=_clamp_bps(transition * 10_000.0),
    )


def _terminal_failure(
    *,
    pre: dict[str, tuple[Any, ...]],
    future: dict[str, tuple[Any, ...]],
) -> bool:
    pre15 = _metric(pre["NAS100"][-15:])
    source_direction = _sign(pre15.net_bps)
    if source_direction == 0:
        return False

    prior = pre["NAS100"][-20:]
    prior_peak = max(bar.high for bar in prior)
    prior_floor = min(bar.low for bar in prior)
    final_close = future["NAS100"][29].close

    if source_direction > 0:
        return bool(
            min(bar.low for bar in future["NAS100"][:30]) < prior_floor
            and final_close < prior_floor
        )
    return bool(
        max(bar.high for bar in future["NAS100"][:30]) > prior_peak
        and final_close > prior_peak
    )


def _prepare_partition(
    *,
    partition: str,
    evidence_paths: dict[str, Path],
) -> tuple[
    tuple[TemporalHierarchyTrainingEpisode, ...],
    dict[str, str | int | None],
]:
    bars = {
        market: _load_bars(evidence_paths[market])
        for market in MARKETS
    }
    peer_indexes = {
        market: {
            bar.closed_key: index
            for index, bar in enumerate(bars[market])
        }
        for market in ("SP500", "US30")
    }

    episodes: list[TemporalHierarchyTrainingEpisode] = []
    nas = bars["NAS100"]
    for nas_index in range(
        MAX_LOOKBACK,
        len(nas) - TARGET_HORIZON_MINUTES - 1,
    ):
        key = nas[nas_index].closed_key
        if int(key[14:16]) not in SAMPLE_MINUTES:
            continue

        indexes = {"NAS100": nas_index}
        missing = False
        for market in ("SP500", "US30"):
            peer_index = peer_indexes[market].get(key)
            if peer_index is None:
                missing = True
                break
            indexes[market] = peer_index
        if missing:
            continue

        pre: dict[str, tuple[Any, ...]] = {}
        future: dict[str, tuple[Any, ...]] = {}
        valid = True
        for market in MARKETS:
            index = indexes[market]
            if (
                index < MAX_LOOKBACK
                or index + TARGET_HORIZON_MINUTES >= len(bars[market])
            ):
                valid = False
                break
            pre_rows = tuple(
                bars[market][index - MAX_LOOKBACK + 1 : index + 1]
            )
            future_rows = tuple(
                bars[market][
                    index + 1 : index + 1 + TARGET_HORIZON_MINUTES
                ]
            )
            if len(pre_rows) != MAX_LOOKBACK:
                valid = False
                break
            if len(future_rows) != TARGET_HORIZON_MINUTES:
                valid = False
                break
            pre[market] = pre_rows
            future[market] = future_rows
        if not valid:
            continue

        source_at = _parse_key(pre["NAS100"][-1].closed_key)
        observed_at = _parse_key(future["NAS100"][-1].closed_key)
        if observed_at <= source_at:
            continue
        if (observed_at - source_at).total_seconds() > 35 * 60:
            continue

        levels = tuple(
            _scale_state(
                scale=scale,
                horizon=horizon,
                windows=pre,
            )
            for scale, horizon in SCALE_HORIZONS
        )
        snapshot = TemporalHierarchySnapshot(
            episode_id=f"{partition}:{source_at.isoformat()}",
            as_of=source_at,
            levels=levels,
        )
        episodes.append(
            TemporalHierarchyTrainingEpisode(
                snapshot=snapshot,
                observed_at=observed_at,
                terminal_failure=_terminal_failure(
                    pre=pre,
                    future=future,
                ),
            )
        )

    del bars
    del peer_indexes
    gc.collect()

    return tuple(episodes), {
        "episode_count": len(episodes),
        "source_min": (
            min(item.snapshot.as_of for item in episodes).isoformat()
            if episodes
            else None
        ),
        "source_max": (
            max(item.snapshot.as_of for item in episodes).isoformat()
            if episodes
            else None
        ),
        "target_max": (
            max(item.observed_at for item in episodes).isoformat()
            if episodes
            else None
        ),
    }


def _evaluation_payload(
    evaluation: TemporalHierarchyEvaluation,
) -> dict[str, int | str]:
    return {
        "partition": evaluation.partition,
        "sample_count": evaluation.sample_count,
        "baseline_declaration_count": evaluation.baseline_declaration_count,
        "baseline_terminal_count": evaluation.baseline_terminal_count,
        "baseline_false_declaration_count": (
            evaluation.baseline_false_declaration_count
        ),
        "hierarchy_declaration_count": evaluation.hierarchy_declaration_count,
        "hierarchy_terminal_count": evaluation.hierarchy_terminal_count,
        "hierarchy_false_declaration_count": (
            evaluation.hierarchy_false_declaration_count
        ),
        "hierarchy_missed_terminal_count": (
            evaluation.hierarchy_missed_terminal_count
        ),
        "false_declaration_reduction_bps": (
            evaluation.false_declaration_reduction_bps
        ),
        "terminal_detection_preservation_bps": (
            evaluation.terminal_detection_preservation_bps
        ),
    }


def run(
    *,
    evidence: dict[str, dict[str, Path]],
) -> dict[str, Any]:
    partitions: dict[
        str,
        tuple[TemporalHierarchyTrainingEpisode, ...],
    ] = {}
    ranges: dict[str, dict[str, str | int | None]] = {}

    for partition in PARTITIONS:
        rows, partition_range = _prepare_partition(
            partition=partition,
            evidence_paths=evidence[partition],
        )
        partitions[partition] = rows
        ranges[partition] = partition_range

    sample_gate = all(
        len(partitions[partition]) >= MINIMUM_EPISODES
        for partition in PARTITIONS
    )
    if not sample_gate:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "status": "WP05_V1_SAMPLE_GATE_FAILED",
            "protocol_pass": False,
            "development_gate_pass": False,
            "fresh_holdout_opened": False,
            "partition_ranges": ranges,
        }

    fitted_at = max(item.observed_at for item in partitions["r8"])
    model = fit_temporal_hierarchy_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=partitions["r8"],
        minimum_training_recall_bps=MINIMUM_TERMINAL_PRESERVATION_BPS,
        ridge=1.0,
    )
    evaluations = {
        partition: evaluate_temporal_hierarchy(
            model=model,
            partition=partition,
            episodes=partitions[partition],
        )
        for partition in PARTITIONS
    }

    development_gate_pass = all(
        evaluations[partition].baseline_terminal_count
        >= MINIMUM_BASELINE_TERMINALS
        and evaluations[partition].false_declaration_reduction_bps
        >= MINIMUM_FALSE_REDUCTION_BPS
        and evaluations[partition].terminal_detection_preservation_bps
        >= MINIMUM_TERMINAL_PRESERVATION_BPS
        for partition in ("r6", "r5")
    )
    protocol_pass = (
        sample_gate
        and model.target_used_for_training_only is True
        and model.runtime_future_market_used is False
        and model.outcome_used_at_runtime is False
        and model.trader_identity_used is False
        and model.symbol_identity_used is False
        and model.knowledge_promotion_authority is False
        and model.methodology_authority is False
        and model.sizing_authority is False
        and model.risk_authority is False
        and model.order_authority is False
        and model.execution_authority is False
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "status": (
            "WP05_V1_HIERARCHY_FROZEN_FOR_FRESH_HOLDOUT"
            if protocol_pass and development_gate_pass
            else "WP05_V1_HIERARCHY_FALSIFIED"
        ),
        "protocol_pass": protocol_pass,
        "development_gate_pass": development_gate_pass,
        "fresh_holdout_opened": False,
        "wp05_exit_gate_pass": False,
        "partition_ranges": ranges,
        "scale_horizons_m1_bars": {
            scale.value: horizon
            for scale, horizon in SCALE_HORIZONS
        },
        "model": {
            "fit_partition": model.fit_partition,
            "fitted_at": model.fitted_at.isoformat(),
            "feature_names": list(model.feature_names),
            "feature_centers_micros": list(model.feature_centers_micros),
            "feature_scales_micros": list(model.feature_scales_micros),
            "coefficients_micros": list(model.coefficients_micros),
            "intercept_micros": model.intercept_micros,
            "declaration_threshold_micros": (
                model.declaration_threshold_micros
            ),
            "minimum_training_recall_bps": (
                model.minimum_training_recall_bps
            ),
            "baseline_training_count": model.baseline_training_count,
            "baseline_terminal_count": model.baseline_terminal_count,
        },
        "evaluations": {
            partition: _evaluation_payload(evaluation)
            for partition, evaluation in evaluations.items()
        },
        "frozen_development_gate": {
            "minimum_false_declaration_reduction_bps": (
                MINIMUM_FALSE_REDUCTION_BPS
            ),
            "minimum_terminal_detection_preservation_bps": (
                MINIMUM_TERMINAL_PRESERVATION_BPS
            ),
            "minimum_baseline_terminal_count": (
                MINIMUM_BASELINE_TERMINALS
            ),
            "must_pass_partitions": ["r6", "r5"],
        },
        "governance": {
            "r8_fit_only": True,
            "r6_refit": False,
            "r5_refit": False,
            "threshold_fit_partition": "r8_only",
            "r6_threshold_retuning": False,
            "r5_threshold_retuning": False,
            "future_target_used_for_training_or_evaluation_only": True,
            "runtime_future_market_used": False,
            "trade_direction_used": False,
            "trade_entry_used": False,
            "trade_stop_used": False,
            "trade_target_used": False,
            "trade_pnl_used": False,
            "trader_identity_feature_used": False,
            "symbol_identity_feature_used": False,
            "fresh_holdout_opened": False,
            "fresh_holdout_required_before_wp05_exit": True,
            "global_qore_validation_still_required": True,
            "knowledge_auto_promotion": False,
            "shared_methodology_authority": False,
            "shared_sizing_authority": False,
            "shared_risk_authority": False,
            "shared_order_authority": False,
            "shared_execution_authority": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


def _paths(
    args: argparse.Namespace,
    partition: str,
) -> dict[str, Path]:
    return {
        "NAS100": getattr(args, f"{partition}_nas"),
        "SP500": getattr(args, f"{partition}_sp"),
        "US30": getattr(args, f"{partition}_us"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in PARTITIONS:
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        evidence={
            partition: _paths(args, partition)
            for partition in PARTITIONS
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "protocol_pass": payload["protocol_pass"],
                "development_gate_pass": payload.get(
                    "development_gate_pass",
                    False,
                ),
                "evaluations": payload.get("evaluations", {}),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
