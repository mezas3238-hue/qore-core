#!/usr/bin/env python3
"""Bind WP-04 V3B scientific evidence into the bounded MC-12 foundation audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.core_stack_v2.market_foundation_model_evidence import (
    FoundationLearningObjective,
    FoundationModality,
    MarketFoundationEvidence,
)

IDENTITY = "QORE_SHARED_MC12_MARKET_FOUNDATION_MODEL_AUDIT_001"
EXPECTED_REPRESENTATION = (
    "e2fc2ca059d5852b4e9107c467392e5e64aeabbd6aca2d8013951b93402bc987"
)


def _one(root: Path, filename: str) -> dict[str, object]:
    rows = list(root.rglob(filename))
    if len(rows) != 1:
        raise ValueError(f"expected one {filename}, found {len(rows)}")
    return json.loads(rows[0].read_text())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--holdout-e", type=Path, required=True)
    parser.add_argument("--replication-d", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    freeze = _one(args.freeze, "wp04-predictive-nonlinear-probe-v3b.json")
    holdout = _one(args.holdout_e, "wp04-v3b-holdout-e.json")
    replication = _one(args.replication_d, "wp04-v3b-replication-d.json")

    representation = freeze["representation"]
    if not isinstance(representation, dict):
        raise ValueError("WP04 freeze representation payload missing")
    if representation["fingerprint"] != EXPECTED_REPRESENTATION:
        raise ValueError("WP04 representation fingerprint drift")
    if freeze["status"] != "WP04_V3B_PROBE_FROZEN_FOR_ONE_SHOT_HOLDOUT":
        raise ValueError("WP04 V3B freeze is not scientific freeze")
    if holdout["status"] != "WP04_V3B_HOLDOUT_E_PASS_REPLICATION_REQUIRED":
        raise ValueError("WP04 HOLDOUT_E PASS missing")
    if replication["status"] != "WP04_V3B_REPLICATION_D_PASS":
        raise ValueError("WP04 temporal replication PASS missing")

    h_eval = holdout["evaluation"]
    r_eval = replication["evaluation"]
    evidence = MarketFoundationEvidence(
        representation_fingerprint=EXPECTED_REPRESENTATION,
        concept_count=int(representation["selected_concept_count"]),
        probe_count=len(freeze["final_frozen_probes"]),
        horizon_minutes=int(representation["horizon_minutes"]),
        markets=("NAS100", "SP500", "US30"),
        market_families=("US_EQUITY_INDEX",),
        objectives_proven=tuple(
            sorted(
                (
                    FoundationLearningObjective.NEXT_STATE_PREDICTION,
                    FoundationLearningObjective.CROSS_MARKET_REPRESENTATION,
                ),
                key=lambda item: item.value,
            )
        ),
        modalities_proven=(FoundationModality.M1_OHLC_DERIVED_SEQUENCE,),
        fresh_holdout_incremental_bps=int(
            h_eval["pooled_incremental_information_bps"]
        ),
        fresh_holdout_positive_targets=int(h_eval["positive_target_count"]),
        temporal_replication_incremental_bps=int(
            r_eval["pooled_incremental_information_bps"]
        ),
        temporal_replication_positive_targets=int(
            r_eval["positive_target_count"]
        ),
        global_multi_family_world_bound=False,
    )

    missing_objectives = tuple(
        item.value
        for item in (
            FoundationLearningObjective.MASKED_RECONSTRUCTION,
            FoundationLearningObjective.CONTRASTIVE_STATE_LEARNING,
            FoundationLearningObjective.ANOMALY_DISCOVERY,
        )
    )
    missing_modalities = tuple(
        item.value
        for item in FoundationModality
        if item not in evidence.modalities_proven
    )
    payload = {
        "identity": IDENTITY,
        "status": "MC12_PARTIAL_FOUNDATION_REPRESENTATION_SCIENTIFICALLY_PROVEN",
        "evidence_fingerprint": evidence.fingerprint(),
        "representation_fingerprint": evidence.representation_fingerprint,
        "concept_count": evidence.concept_count,
        "probe_count": evidence.probe_count,
        "horizon_minutes": evidence.horizon_minutes,
        "markets": evidence.markets,
        "market_families": evidence.market_families,
        "objectives_proven": tuple(item.value for item in evidence.objectives_proven),
        "modalities_proven": tuple(item.value for item in evidence.modalities_proven),
        "holdout_incremental_bps": evidence.fresh_holdout_incremental_bps,
        "holdout_positive_targets": evidence.fresh_holdout_positive_targets,
        "replication_incremental_bps": evidence.temporal_replication_incremental_bps,
        "replication_positive_targets": evidence.temporal_replication_positive_targets,
        "sequence_representation_scientifically_proven": (
            evidence.sequence_representation_scientifically_proven
        ),
        "missing_optional_learning_objectives": missing_objectives,
        "missing_modalities": missing_modalities,
        "global_multi_family_world_bound": False,
        "dependency": "B_GLOBAL_WORLD_MULTI_FAMILY_AND_MODALITY_BINDING",
        "mc12_completed_and_proven": False,
        "runtime_future_market_used": False,
        "identity_shortcut_used": False,
        "productive_authority": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
