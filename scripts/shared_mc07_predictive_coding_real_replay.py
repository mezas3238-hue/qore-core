#!/usr/bin/env python3
"""Real historical proof for Shared MC-07 predictive coding.

Expectations are formed strictly at source time T. The later observation at
T+30m is used only when the prediction-error record matures. R8 calibrates
channel tolerances and the surprise threshold; R6 and R5 replay them unchanged.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median

import shared_sti2_real_opportunity_discovery as source
from shared_wp03_historical_causal_discovery import (
    PRE_WINDOW_MINUTES,
    CausalConcept,
    _source_state,
)

from qore.infrastructure.core_stack_v2.predictive_coding_engine import (
    PredictiveChannel,
    PredictiveExpectation,
    PredictiveObservation,
    compute_predictive_coding_state,
)

IDENTITY = "QORE_SHARED_MC07_PREDICTIVE_CODING_REAL_REPLAY_001"
CHANNEL_CONCEPTS = {
    PredictiveChannel.VOLATILITY: CausalConcept.REGIME_TRANSITION,
    PredictiveChannel.DISPLACEMENT: CausalConcept.DISPLACEMENT,
    PredictiveChannel.RETRACEMENT_DEPTH: CausalConcept.STRUCTURAL_FRAGILITY,
    PredictiveChannel.INTERMARKET_REACTION: CausalConcept.LEADER_CONFIRMATION,
    PredictiveChannel.LIQUIDITY_RESPONSE: CausalConcept.LIQUIDITY_ACCUMULATION,
}


def _quantile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("predictive coding calibration has no values")
    index = int(round((len(ordered) - 1) * fraction))
    return ordered[max(0, min(len(ordered) - 1, index))]


def _target_states(
    pre: dict[str, tuple[object, ...]],
    future: dict[str, tuple[object, ...]],
) -> dict[CausalConcept, int]:
    shifted = {
        market: tuple((pre[market] + future[market])[-PRE_WINDOW_MINUTES:])
        for market in pre
    }
    states, _vol_ratio, _coherence = _source_state(shifted)
    return states


def _raw_rows(
    paths: dict[str, Path],
    *,
    partition: str,
) -> tuple[dict[str, object], ...]:
    rows = source._aligned_source_rows(
        paths,
        partition=partition,
        require_future=True,
    )
    out: list[dict[str, object]] = []
    for observation, current_states, pre, future in rows:
        if future is None:
            raise AssertionError("predictive replay requires later observation")
        target = _target_states(pre, future)
        expected = {
            channel: int(current_states[concept])
            for channel, concept in CHANNEL_CONCEPTS.items()
        }
        observed = {
            channel: int(target[concept])
            for channel, concept in CHANNEL_CONCEPTS.items()
        }
        out.append(
            {
                "source_at": observation.as_of.isoformat(),
                "expected": expected,
                "observed": observed,
            }
        )
    return tuple(out)


def _freeze_r8(
    rows: tuple[dict[str, object], ...],
) -> tuple[dict[PredictiveChannel, int], int]:
    errors: dict[PredictiveChannel, list[int]] = {
        channel: [] for channel in PredictiveChannel
    }
    for row in rows:
        expected = row["expected"]
        observed = row["observed"]
        assert isinstance(expected, dict) and isinstance(observed, dict)
        for channel in PredictiveChannel:
            errors[channel].append(
                abs(int(observed[channel]) - int(expected[channel]))
            )

    tolerances = {
        channel: max(250, _quantile(values, 0.75))
        for channel, values in errors.items()
    }

    surprises: list[int] = []
    for row in rows:
        expected = row["expected"]
        observed = row["observed"]
        assert isinstance(expected, dict) and isinstance(observed, dict)
        state = compute_predictive_coding_state(
            expectations=tuple(
                PredictiveExpectation(
                    channel=channel,
                    expected_bps=int(expected[channel]),
                    tolerance_bps=tolerances[channel],
                )
                for channel in PredictiveChannel
            ),
            observations=tuple(
                PredictiveObservation(
                    channel=channel,
                    observed_bps=int(observed[channel]),
                )
                for channel in PredictiveChannel
            ),
        )
        surprises.append(state.aggregate_surprise_bps)

    threshold = _quantile(surprises, 0.75)
    return tolerances, threshold


def _evaluate(
    rows: tuple[dict[str, object], ...],
    *,
    tolerances: dict[PredictiveChannel, int],
    surprise_threshold_bps: int,
) -> dict[str, object]:
    high_errors: list[int] = []
    low_errors: list[int] = []
    revision_pressures: list[int] = []

    for row in rows:
        expected = row["expected"]
        observed = row["observed"]
        assert isinstance(expected, dict) and isinstance(observed, dict)
        state = compute_predictive_coding_state(
            expectations=tuple(
                PredictiveExpectation(
                    channel=channel,
                    expected_bps=int(expected[channel]),
                    tolerance_bps=tolerances[channel],
                )
                for channel in PredictiveChannel
            ),
            observations=tuple(
                PredictiveObservation(
                    channel=channel,
                    observed_bps=int(observed[channel]),
                )
                for channel in PredictiveChannel
            ),
        )
        raw_error = sum(
            abs(int(observed[channel]) - int(expected[channel]))
            for channel in PredictiveChannel
        ) // len(PredictiveChannel)
        revision_pressures.append(state.model_revision_pressure_bps)
        if state.aggregate_surprise_bps >= surprise_threshold_bps:
            high_errors.append(raw_error)
        else:
            low_errors.append(raw_error)

    if not high_errors or not low_errors:
        raise ValueError("predictive coding replay degenerated to one surprise class")
    high_mean = sum(high_errors) // len(high_errors)
    low_mean = sum(low_errors) // len(low_errors)
    separation = high_mean - low_mean
    high_rate = len(high_errors) * 10_000 // len(rows)
    gate = (
        separation >= 1_000
        and 1_000 <= high_rate <= 5_000
        and median(revision_pressures) > 0
    )
    return {
        "sample_count": len(rows),
        "high_surprise_count": len(high_errors),
        "high_surprise_rate_bps": high_rate,
        "high_surprise_raw_error_mean_bps": high_mean,
        "low_surprise_raw_error_mean_bps": low_mean,
        "raw_error_separation_bps": separation,
        "median_revision_pressure_bps": int(median(revision_pressures)),
        "gate_pass": gate,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r8", "r6", "r5"):
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    evidence = {
        partition: {
            "NAS100": getattr(args, f"{partition}_nas"),
            "SP500": getattr(args, f"{partition}_sp"),
            "US30": getattr(args, f"{partition}_us"),
        }
        for partition in ("r8", "r6", "r5")
    }
    rows = {
        partition: _raw_rows(evidence[partition], partition=partition)
        for partition in ("r8", "r6", "r5")
    }
    tolerances, threshold = _freeze_r8(rows["r8"])
    evaluations = {
        partition: _evaluate(
            rows[partition],
            tolerances=tolerances,
            surprise_threshold_bps=threshold,
        )
        for partition in ("r8", "r6", "r5")
    }
    pass_all = evaluations["r6"]["gate_pass"] and evaluations["r5"]["gate_pass"]

    payload = {
        "identity": IDENTITY,
        "status": (
            "MC07_PREDICTIVE_CODING_REPLICATED_PASS"
            if pass_all
            else "MC07_PREDICTIVE_CODING_FALSIFIED"
        ),
        "r8_frozen_policy": {
            "channel_tolerance_bps": {
                channel.value: tolerances[channel]
                for channel in PredictiveChannel
            },
            "high_surprise_threshold_bps": threshold,
            "threshold_fit_partition": "R8_CONSUMED",
        },
        "evaluations": evaluations,
        "engine_implemented": True,
        "real_data_bound": True,
        "causal_replay_executed": True,
        "research_oos_r6_pass": bool(evaluations["r6"]["gate_pass"]),
        "temporal_replication_r5_pass": bool(evaluations["r5"]["gate_pass"]),
        "expectation_uses_future_market": False,
        "later_observation_used_only_when_error_matures": True,
        "outcome_or_pnl_used": False,
        "protected_certification_holdout_opened": False,
        "productive_authority": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": payload["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
