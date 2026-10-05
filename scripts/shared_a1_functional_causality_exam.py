#!/usr/bin/env python3
"""Executable A1 functional/causality exam for QORE Shared Lab TARGET origin.

This exam proves engineering consumption and observable causal propagation across
MC17 -> MC18 -> MC19 without making calibration, economic-value, certification,
trade, risk, sizing, or execution claims.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)
from qore.infrastructure.core_stack_v2.shared_trajectory_intelligence import (
    SharedTrajectoryState,
    assess_trajectory_intelligence,
)

IDENTITY = "QORE_SHARED_A1_FUNCTIONAL_CAUSALITY_EXAM_001"
AS_OF = datetime(2026, 10, 4, 18, 0, tzinfo=UTC)


def _healthy() -> SharedOpportunitySourceObservation:
    return SharedOpportunitySourceObservation(
        observation_id="a1-exam-healthy",
        asset="NAS100",
        as_of=AS_OF,
        evidence_cutoff_at=AS_OF,
        direction_sign=1,
        data_integrity_bps=10_000,
        compression_bps=4_000,
        liquidity_accumulation_bps=5_000,
        failed_auction_bps=2_000,
        displacement_bps=6_000,
        acceptance_bps=8_000,
        absorption_bps=6_000,
        leader_confirmation_bps=8_500,
        leader_divergence_bps=1_500,
        momentum_persistence_bps=8_000,
        momentum_decay_bps=1_500,
        structural_fragility_bps=1_500,
        liquidity_vacuum_bps=1_500,
        regime_transition_bps=1_500,
        anomaly_bps=1_000,
        provenance_refs=("a1:exam:source-only",),
    )


def _distressed() -> SharedOpportunitySourceObservation:
    return replace(
        _healthy(),
        observation_id="a1-exam-distressed",
        acceptance_bps=1_500,
        absorption_bps=1_000,
        leader_confirmation_bps=1_000,
        leader_divergence_bps=9_000,
        momentum_persistence_bps=1_000,
        momentum_decay_bps=9_000,
        structural_fragility_bps=9_000,
        liquidity_vacuum_bps=9_000,
        regime_transition_bps=9_000,
        anomaly_bps=9_000,
        provenance_refs=("a1:exam:distressed-source-only",),
    )


def _perturbed() -> SharedOpportunitySourceObservation:
    return replace(
        _healthy(),
        observation_id="a1-exam-causal-perturbation",
        leader_divergence_bps=8_500,
        structural_fragility_bps=7_500,
        liquidity_vacuum_bps=7_000,
        regime_transition_bps=7_500,
        anomaly_bps=6_500,
        provenance_refs=("a1:exam:causal-perturbation",),
    )


def run_exam() -> dict[str, Any]:
    healthy = assess_trajectory_intelligence(_healthy())
    repeated = assess_trajectory_intelligence(_healthy())
    distressed = assess_trajectory_intelligence(_distressed())
    perturbed = assess_trajectory_intelligence(_perturbed())
    insufficient = assess_trajectory_intelligence(
        replace(
            _healthy(),
            observation_id="a1-exam-insufficient",
            data_integrity_bps=9_000,
        )
    )

    authority_zero = all(
        not value
        for value in (
            healthy.creates_trader_setup,
            healthy.position_management_authority,
            healthy.execution_authority,
            healthy.risk_authority,
            healthy.sizing_authority,
            healthy.capital_authority,
        )
    )
    source_only = all(
        (
            item.source_only
            and not item.future_market_used
            and not item.future_outcome_used
        )
        for item in (healthy, distressed, perturbed, insufficient)
    )
    gates = {
        "mc17_output_consumed": healthy.mc17_output_consumed is True,
        "mc18_output_consumed": healthy.mc18_output_consumed is True,
        "normal_adversity_distinguished": (
            healthy.state is SharedTrajectoryState.NORMAL_ADVERSITY
        ),
        "structural_failure_distinguished": (
            distressed.state is SharedTrajectoryState.STRUCTURAL_FAILURE
        ),
        "low_integrity_fails_closed": (
            insufficient.state is SharedTrajectoryState.INSUFFICIENT
            and insufficient.dominant_agency_mechanism is None
        ),
        "mc17_upstream_perturbation_propagates": (
            healthy.mc17_fingerprint != perturbed.mc17_fingerprint
        ),
        "mc18_upstream_perturbation_propagates": (
            healthy.mc18_fingerprint != perturbed.mc18_fingerprint
        ),
        "mc19_downstream_output_changes": (
            healthy.fingerprint() != perturbed.fingerprint()
        ),
        "observable_hazard_changes": (
            healthy.structural_hazard_bps != perturbed.structural_hazard_bps
        ),
        "deterministic_replay": healthy.fingerprint() == repeated.fingerprint(),
        "source_only_temporal_firewall": source_only,
        "zero_productive_authority": authority_zero,
        "scientific_calibration_not_overclaimed": (
            healthy.scientifically_calibrated is False
        ),
    }
    passed = all(gates.values())

    return {
        "identity": IDENTITY,
        "status": (
            "A1_FUNCTIONAL_CAUSALITY_ENGINEERING_PASS"
            if passed
            else "A1_FUNCTIONAL_CAUSALITY_ENGINEERING_FAIL"
        ),
        "gates": gates,
        "functional_chain": [
            "SOURCE_OBSERVATION",
            "MC17_MARKET_AGENCY",
            "MC18_COUNTERFACTUAL_WORLD",
            "MC19_TRAJECTORY_INTELLIGENCE",
        ],
        "healthy": {
            "state": healthy.state.value,
            "mc17_fingerprint": healthy.mc17_fingerprint,
            "mc18_fingerprint": healthy.mc18_fingerprint,
            "mc19_fingerprint": healthy.fingerprint(),
            "structural_hazard_bps": healthy.structural_hazard_bps,
            "recovery_capacity_bps": healthy.recovery_capacity_bps,
        },
        "perturbed": {
            "state": perturbed.state.value,
            "mc17_fingerprint": perturbed.mc17_fingerprint,
            "mc18_fingerprint": perturbed.mc18_fingerprint,
            "mc19_fingerprint": perturbed.fingerprint(),
            "structural_hazard_bps": perturbed.structural_hazard_bps,
            "recovery_capacity_bps": perturbed.recovery_capacity_bps,
        },
        "distressed_state": distressed.state.value,
        "insufficient_state": insufficient.state.value,
        "shared_lab_provenance": {
            "run_id": os.environ.get("QORE_SHARED_LAB_RUN_ID"),
            "target_sha": os.environ.get("QORE_SHARED_LAB_TARGET_SHA"),
            "harness_sha": os.environ.get("QORE_SHARED_LAB_HARNESS_SHA"),
            "execution_origin": os.environ.get("QORE_SHARED_LAB_EXECUTION_ORIGIN"),
            "dataset_hash": os.environ.get("QORE_SHARED_LAB_DATASET_HASH"),
        },
        "scientific_calibration_proven": False,
        "economic_value_proven": False,
        "shared_certification_claimed": False,
        "protected_final_holdout_opened": False,
        "productive_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = run_exam()
    rendered = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")
    raise SystemExit(
        0 if payload["status"] == "A1_FUNCTIONAL_CAUSALITY_ENGINEERING_PASS" else 1
    )


if __name__ == "__main__":
    main()
