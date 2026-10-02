#!/usr/bin/env python3
"""Real-data replicated stress proof for six-source uncertainty decomposition."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import shared_sti2_real_opportunity_discovery as source

from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)
from qore.infrastructure.core_stack_v2.uncertainty_decomposition_v2 import (
    SharedUncertaintyEvidenceV2,
    decompose_uncertainty_v2,
)

IDENTITY = "QORE_SHARED_MC15_UNCERTAINTY_DECOMPOSITION_V2_REAL_DATA_001"


def _clip(value: int) -> int:
    return max(0, min(10_000, value))


def _evidence(
    observation: SharedOpportunitySourceObservation,
    *,
    stress: str,
) -> SharedUncertaintyEvidenceV2:
    data_missingness = 10_000 - observation.data_integrity_bps
    timestamp_ambiguity = 0
    provider_anomaly = 0

    regime_unfamiliarity = observation.anomaly_bps
    regime_transition = observation.regime_transition_bps
    relationship_instability = observation.leader_divergence_bps

    causal_ambiguity = observation.leader_divergence_bps
    confounding = observation.structural_fragility_bps
    transportability = observation.regime_transition_bps

    simulation_gap = observation.anomaly_bps
    scenario_gap = observation.structural_fragility_bps
    simulation_instability = observation.leader_divergence_bps

    if stress == "DATA":
        data_missingness = max(data_missingness, 6_000)
        timestamp_ambiguity = 6_000
        provider_anomaly = 6_000
    elif stress == "REGIME":
        regime_unfamiliarity = _clip(regime_unfamiliarity + 3_000)
        regime_transition = _clip(regime_transition + 3_000)
        relationship_instability = _clip(relationship_instability + 3_000)
    elif stress == "CAUSAL":
        causal_ambiguity = _clip(causal_ambiguity + 3_000)
        confounding = _clip(confounding + 3_000)
        transportability = _clip(transportability + 3_000)
    elif stress == "SIMULATION":
        simulation_gap = _clip(simulation_gap + 3_000)
        scenario_gap = _clip(scenario_gap + 3_000)
        simulation_instability = _clip(simulation_instability + 3_000)
    elif stress != "BASELINE":
        raise ValueError(f"unknown stress: {stress}")

    return SharedUncertaintyEvidenceV2(
        observation_noise_bps=observation.anomaly_bps,
        realized_path_variability_bps=observation.regime_transition_bps,
        scenario_overlap_bps=observation.leader_divergence_bps,
        model_disagreement_bps=observation.leader_divergence_bps,
        novelty_bps=observation.anomaly_bps,
        calibration_error_bps=data_missingness,
        historical_distance_bps=observation.structural_fragility_bps,
        data_missingness_bps=data_missingness,
        timestamp_ambiguity_bps=timestamp_ambiguity,
        provider_anomaly_bps=provider_anomaly,
        regime_unfamiliarity_bps=regime_unfamiliarity,
        regime_transition_bps=regime_transition,
        relationship_instability_bps=relationship_instability,
        causal_identification_ambiguity_bps=causal_ambiguity,
        confounding_risk_bps=confounding,
        transportability_uncertainty_bps=transportability,
        simulation_model_gap_bps=simulation_gap,
        scenario_coverage_gap_bps=scenario_gap,
        simulation_instability_bps=simulation_instability,
    )


def _mean(values: list[int]) -> int:
    return sum(values) // len(values) if values else 0


def _partition(paths: dict[str, Path], partition: str) -> dict[str, object]:
    rows = source._aligned_source_rows(
        paths,
        partition=partition,
        require_future=False,
    )
    if not rows:
        raise ValueError("uncertainty replay has no source observations")

    stresses = ("BASELINE", "DATA", "REGIME", "CAUSAL", "SIMULATION")
    out: dict[str, dict[str, int]] = {}
    for stress in stresses:
        decompositions = [
            decompose_uncertainty_v2(_evidence(row[0], stress=stress))
            for row in rows
        ]
        out[stress] = {
            "aleatoric_bps": _mean([x.aleatoric_bps for x in decompositions]),
            "epistemic_bps": _mean([x.epistemic_bps for x in decompositions]),
            "data_bps": _mean([x.data_bps for x in decompositions]),
            "regime_bps": _mean([x.regime_bps for x in decompositions]),
            "causal_bps": _mean([x.causal_bps for x in decompositions]),
            "simulation_bps": _mean([x.simulation_bps for x in decompositions]),
            "assertiveness_ceiling_bps": _mean(
                [x.assertiveness_ceiling_bps for x in decompositions]
            ),
        }

    baseline = out["BASELINE"]
    gates = {
        "data_stress_detected": (
            out["DATA"]["data_bps"] - baseline["data_bps"] >= 1_500
        ),
        "regime_stress_detected": (
            out["REGIME"]["regime_bps"] - baseline["regime_bps"] >= 1_500
        ),
        "causal_stress_detected": (
            out["CAUSAL"]["causal_bps"] - baseline["causal_bps"] >= 1_500
        ),
        "simulation_stress_detected": (
            out["SIMULATION"]["simulation_bps"]
            - baseline["simulation_bps"]
            >= 1_500
        ),
        "data_stress_reduces_assertiveness": (
            baseline["assertiveness_ceiling_bps"]
            - out["DATA"]["assertiveness_ceiling_bps"]
            >= 500
        ),
        "regime_stress_reduces_assertiveness": (
            baseline["assertiveness_ceiling_bps"]
            - out["REGIME"]["assertiveness_ceiling_bps"]
            >= 500
        ),
        "causal_stress_reduces_assertiveness": (
            baseline["assertiveness_ceiling_bps"]
            - out["CAUSAL"]["assertiveness_ceiling_bps"]
            >= 500
        ),
        "simulation_stress_reduces_assertiveness": (
            baseline["assertiveness_ceiling_bps"]
            - out["SIMULATION"]["assertiveness_ceiling_bps"]
            >= 500
        ),
    }
    return {
        "partition": partition,
        "source_observation_count": len(rows),
        "components": out,
        "gates": gates,
        "gate_pass": all(gates.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r6", "r5"):
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    results = {}
    for partition in ("r6", "r5"):
        results[partition] = _partition(
            {
                "NAS100": getattr(args, f"{partition}_nas"),
                "SP500": getattr(args, f"{partition}_sp"),
                "US30": getattr(args, f"{partition}_us"),
            },
            partition,
        )
    passed = all(row["gate_pass"] for row in results.values())
    payload = {
        "identity": IDENTITY,
        "status": (
            "MC15_SIX_SOURCE_UNCERTAINTY_REPLICATED_PASS"
            if passed
            else "MC15_SIX_SOURCE_UNCERTAINTY_STRESS_FALSIFIED"
        ),
        "engine_implemented": True,
        "real_data_bound": True,
        "causal_source_replay_executed": True,
        "stress_pass": passed,
        "temporal_replication_across_consumed_r6_r5": passed,
        "calibration_state": "UNCALIBRATED",
        "results": results,
        "future_market_used": False,
        "outcome_used": False,
        "pnl_used": False,
        "protected_certification_holdout_opened": False,
        "productive_authority": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": payload["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
