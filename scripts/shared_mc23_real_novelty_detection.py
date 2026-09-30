#!/usr/bin/env python3
"""MC-23 real source-time novelty detection on consumed R6/R5 evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import shared_sti2_real_opportunity_discovery as source

from qore.infrastructure.core_stack_v2.meta_learning_regime_adaptation import (
    AdaptationDisposition,
    AdaptiveHypothesisProposal,
    NoveltyState,
    assess_regime_novelty,
)
from qore.infrastructure.core_stack_v2.uncertainty_decomposition_v2 import (
    SharedUncertaintyEvidenceV2,
)

IDENTITY = "QORE_SHARED_MC23_REAL_NOVELTY_DETECTION_001"


def _clamp(value: int) -> int:
    return max(0, min(10_000, int(value)))


def _uncertainty(observation: Any) -> SharedUncertaintyEvidenceV2:
    novelty = max(
        int(observation.anomaly_bps),
        int(observation.leader_divergence_bps),
    )
    return SharedUncertaintyEvidenceV2(
        observation_noise_bps=_clamp(observation.anomaly_bps),
        realized_path_variability_bps=_clamp(
            observation.regime_transition_bps
        ),
        scenario_overlap_bps=_clamp(observation.leader_divergence_bps),
        model_disagreement_bps=_clamp(observation.leader_divergence_bps),
        novelty_bps=_clamp(novelty),
        calibration_error_bps=0,
        historical_distance_bps=_clamp(observation.structural_fragility_bps),
        data_missingness_bps=_clamp(10_000 - observation.data_integrity_bps),
        timestamp_ambiguity_bps=0,
        provider_anomaly_bps=0,
        regime_unfamiliarity_bps=_clamp(
            max(observation.anomaly_bps, observation.regime_transition_bps)
        ),
        regime_transition_bps=_clamp(observation.regime_transition_bps),
        relationship_instability_bps=_clamp(
            observation.leader_divergence_bps
        ),
        causal_identification_ambiguity_bps=_clamp(
            observation.leader_divergence_bps
        ),
        confounding_risk_bps=_clamp(observation.structural_fragility_bps),
        transportability_uncertainty_bps=_clamp(
            observation.regime_transition_bps
        ),
        simulation_model_gap_bps=_clamp(observation.anomaly_bps),
        scenario_coverage_gap_bps=_clamp(observation.structural_fragility_bps),
        simulation_instability_bps=_clamp(observation.leader_divergence_bps),
    )


def _partition(
    paths: dict[str, Path],
    partition: str,
) -> dict[str, object]:
    rows = source._aligned_source_rows(
        paths,
        partition=f"mc23_{partition}",
        require_future=False,
    )
    counts: Counter[str] = Counter()
    deterministic = 0
    proposals = 0
    unknown_as_known = 0

    for index, (observation, _states, _pre, future) in enumerate(rows):
        if future is not None:
            raise AssertionError("MC23 novelty detection cannot attach future evidence")
        evidence = _uncertainty(observation)
        first = assess_regime_novelty(
            evidence,
            closest_known_structures=(
                "MC16_REGIME_MEMORY",
                "WP04_LATENT_REPRESENTATION",
            ),
        )
        second = assess_regime_novelty(
            evidence,
            closest_known_structures=(
                "MC16_REGIME_MEMORY",
                "WP04_LATENT_REPRESENTATION",
            ),
        )
        deterministic += int(first == second)
        counts[first.state.value] += 1
        unknown_as_known += int(first.unknown_treated_as_known)

        if first.state in {NoveltyState.NOVEL, NoveltyState.NEAR_KNOWN}:
            proposal = AdaptiveHypothesisProposal(
                proposal_id=f"{partition}:{index}:novelty-research",
                novelty=first,
                hypothesis_ref="research:ADAPTIVE_REPRESENTATION_REQUIRED",
                validation_refs=(),
                disposition=AdaptationDisposition.RESEARCH_ONLY,
            )
            proposals += int(
                proposal.disposition is AdaptationDisposition.RESEARCH_ONLY
                and not proposal.certified_knowledge_mutation
                and not proposal.productive_authority
            )

    passed = (
        bool(rows)
        and deterministic == len(rows)
        and unknown_as_known == 0
    )
    return {
        "partition": partition,
        "observation_count": len(rows),
        "deterministic_count": deterministic,
        "state_counts": dict(sorted(counts.items())),
        "novel_or_near_known_count": (
            counts[NoveltyState.NOVEL.value]
            + counts[NoveltyState.NEAR_KNOWN.value]
        ),
        "research_only_proposal_count": proposals,
        "unknown_treated_as_known_count": unknown_as_known,
        "pass": passed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r6", "r5"):
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    def paths(name: str) -> dict[str, Path]:
        return {
            "NAS100": getattr(args, f"{name}_nas"),
            "SP500": getattr(args, f"{name}_sp"),
            "US30": getattr(args, f"{name}_us"),
        }

    results = {
        name: _partition(paths(name), name)
        for name in ("r6", "r5")
    }
    passed = all(bool(item["pass"]) for item in results.values())
    novel_count = sum(
        int(item["novel_or_near_known_count"])
        for item in results.values()
    )
    payload = {
        "identity": IDENTITY,
        "status": (
            "MC23_REAL_NOVELTY_DETECTION_BOUND_PASS"
            if passed
            else "MC23_REAL_NOVELTY_DETECTION_BINDING_FAILED"
        ),
        "results": results,
        "real_source_observations": sum(
            int(item["observation_count"]) for item in results.values()
        ),
        "real_novel_or_near_known_episode_count": novel_count,
        "real_novelty_detection_bound": passed,
        "novel_unknown_treated_as_known": False,
        "adaptive_proposals_research_only": True,
        "research_indices_are_not_calibrated_probabilities": True,
        "future_market_used": False,
        "outcome_used": False,
        "pnl_used": False,
        "real_novel_regime_validated_adaptation": False,
        "certified_knowledge_mutation": False,
        "productive_authority": False,
        "mc23_completed_and_proven": False,
        "next_gate": (
            "VALIDATE_FROZEN_ADAPTATION_ON_INDEPENDENT_NOVEL_REGIME_EVIDENCE"
        ),
        "master_ledger_mutated": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
