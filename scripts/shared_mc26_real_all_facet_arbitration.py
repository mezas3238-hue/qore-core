#!/usr/bin/env python3
"""MC-26 real all-facet Cognitive Arbitration proof.

This is a mechanism proof over already-consumed R6 source evidence plus sealed
capability artifacts. It does not claim fresh scientific value. Missing or
non-co-temporal evidence is preserved as uncertainty rather than fabricated.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import shared_sti2_real_opportunity_discovery as source

from qore.infrastructure.core_stack_v2.cognitive_arbitration import (
    CognitiveFacet,
    CognitiveFacetEvidence,
    SharedSituationState,
    arbitrate_shared_situation,
)
from qore.infrastructure.core_stack_v2.counterfactual_world_engine import (
    CounterfactualWorldKind,
    build_counterfactual_world_distribution,
)
from qore.infrastructure.core_stack_v2.hypothesis_ensemble import (
    evaluate_reversal_hypotheses,
)
from qore.infrastructure.core_stack_v2.meta_learning_regime_adaptation import (
    assess_regime_novelty,
)
from qore.infrastructure.core_stack_v2.perception import perceive
from qore.infrastructure.core_stack_v2.uncertainty_decomposition_v2 import (
    SharedUncertaintyEvidenceV2,
    decompose_uncertainty_v2,
)

IDENTITY = "QORE_SHARED_MC26_REAL_ALL_FACET_ARBITRATION_001"

R6_SOURCE_ARTIFACT_ID = 10389112524


@dataclass(frozen=True, slots=True)
class _PerceptionBar:
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


def _perception_bars(bars: tuple[Any, ...]) -> tuple[_PerceptionBar, ...]:
    return tuple(
        _PerceptionBar(
            opened_at=source._parse_key(bar.opened_key),
            closed_at=source._parse_key(bar.closed_key),
            open=Decimal(str(bar.opened)),
            high=Decimal(str(bar.high)),
            low=Decimal(str(bar.low)),
            close=Decimal(str(bar.close)),
        )
        for bar in bars
    )
MC15_RUN_ID = 36726927463
MC15_ARTIFACT_ID = 11102652639
MC18_RUN_ID = 36764204066
MC18_ARTIFACT_ID = 11119876541
MC19_RUN_ID = 36764215198
MC19_ARTIFACT_ID = 11120695398
MC14_RUN_ID = 36763713858
MC14_ARTIFACT_ID = 11120281435
MC20_RUN_ID = 36775872235
MC20_ARTIFACT_ID = 11125287784
MC28_RUN_ID = 36777388801
MC28_ARTIFACT_ID = 11126275619
STI5_RUN_ID = 36640098773
STI5_ARTIFACT_ID = 11066541040


def _load(root: Path, filename: str) -> dict[str, Any]:
    matches = list(root.rglob(filename))
    if len(matches) != 1:
        raise ValueError(f"expected one {filename}, found {len(matches)}")
    payload = json.loads(matches[0].read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{filename} must contain an object")
    return payload


def _clip(value: int) -> int:
    return max(0, min(10_000, int(value)))


def _uncertainty(
    observation: Any,
    *,
    specialist_disagreement_bps: int,
) -> tuple[SharedUncertaintyEvidenceV2, int]:
    evidence = SharedUncertaintyEvidenceV2(
        observation_noise_bps=observation.anomaly_bps,
        realized_path_variability_bps=observation.regime_transition_bps,
        scenario_overlap_bps=observation.leader_divergence_bps,
        model_disagreement_bps=specialist_disagreement_bps,
        novelty_bps=observation.anomaly_bps,
        calibration_error_bps=10_000 - observation.data_integrity_bps,
        historical_distance_bps=observation.structural_fragility_bps,
        data_missingness_bps=10_000 - observation.data_integrity_bps,
        timestamp_ambiguity_bps=0,
        provider_anomaly_bps=0,
        regime_unfamiliarity_bps=observation.anomaly_bps,
        regime_transition_bps=observation.regime_transition_bps,
        relationship_instability_bps=observation.leader_divergence_bps,
        causal_identification_ambiguity_bps=observation.leader_divergence_bps,
        confounding_risk_bps=observation.structural_fragility_bps,
        transportability_uncertainty_bps=observation.regime_transition_bps,
        simulation_model_gap_bps=observation.anomaly_bps,
        scenario_coverage_gap_bps=observation.structural_fragility_bps,
        simulation_instability_bps=observation.leader_divergence_bps,
    )
    result = decompose_uncertainty_v2(evidence)
    return evidence, _clip(10_000 - result.assertiveness_ceiling_bps)


def _specialist_disagreement(pre: dict[str, tuple[Any, ...]], observation: Any) -> tuple[int, int]:
    nas = pre["NAS100"]
    sp = pre["SP500"]
    us = pre["US30"]
    if len(nas) < 30 or len(sp) < 10 or len(us) < 10:
        return 0, 10_000
    recent = _perception_bars(nas[-10:])
    prior = _perception_bars(nas[-30:-10])
    sp_recent = _perception_bars(sp[-10:])
    us_recent = _perception_bars(us[-10:])
    low = min(Decimal(str(item.low)) for item in recent)
    high = max(Decimal(str(item.high)) for item in recent)
    width = high - low
    if width <= 0:
        return 0, 10_000
    side = "long" if recent[-1].close >= recent[0].close else "short"
    vector = perceive(
        as_of=observation.as_of,
        side=side,
        reference_width=width,
        nas_recent=recent,
        nas_prior=prior,
        sweep_to_signal=recent,
        sp500_recent=sp_recent,
        us30_recent=us_recent,
    )
    ensemble = evaluate_reversal_hypotheses(vector)
    scores = sorted(
        (
            ensemble.reversal_score,
            ensemble.continuation_against_score,
            ensemble.range_noise_score,
            ensemble.anomaly_score,
        ),
        reverse=True,
    )
    total = sum(scores)
    if total <= 0:
        return 0, 10_000
    top = scores[0] * 10_000 // total
    second = scores[1] * 10_000 // total
    return top, second


def _refs(*values: str) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r6-nas", type=Path, required=True)
    parser.add_argument("--r6-sp", type=Path, required=True)
    parser.add_argument("--r6-us", type=Path, required=True)
    parser.add_argument("--mc15", type=Path, required=True)
    parser.add_argument("--mc18", type=Path, required=True)
    parser.add_argument("--mc19", type=Path, required=True)
    parser.add_argument("--mc14", type=Path, required=True)
    parser.add_argument("--mc20", type=Path, required=True)
    parser.add_argument("--mc28", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    mc15 = _load(args.mc15, "mc15-six-source-uncertainty-v2.json")
    mc18 = _load(args.mc18, "mc18-counterfactual-world-real-replay.json")
    mc19 = _load(args.mc19, "mc19-trajectory-intelligence-audit.json")
    mc14 = _load(args.mc14, "mc14-latent-temporal-causal.json")
    mc20 = _load(args.mc20, "mc20-operational-stability-binding.json")
    mc28 = _load(args.mc28, "mc28-standard-006-diagnostic-taxonomy.json")

    if mc15.get("status") != "MC15_SIX_SOURCE_UNCERTAINTY_REPLICATED_PASS":
        raise AssertionError("MC15 real uncertainty evidence missing")
    if mc18.get("status") != "MC18_COUNTERFACTUAL_WORLD_ENGINE_REAL_DATA_BOUND_PASS":
        raise AssertionError("MC18 real world-model evidence missing")
    if mc19.get("status") != "MC19_TRAJECTORY_INTELLIGENCE_REAL_FOUNDATION_PASS":
        raise AssertionError("MC19 real trajectory evidence missing")
    if mc14.get("status") != "MC14_LATENT_TEMPORAL_CAUSAL_CONSUMED_DIAGNOSTIC_COMPLETE":
        raise AssertionError("MC14 real causal diagnostic missing")
    if mc14.get("r8_research_candidate_count") != 0:
        raise AssertionError("MC14 causal disposition changed")
    if mc20.get("status") != "MC20_STABILITY_ENGINE_COMPLETED_AND_PROVEN":
        raise AssertionError("MC20 stability evidence missing")
    if mc28.get("status") != "MC28_STANDARD_006_DIAGNOSTIC_CONTRACT_PASS_OPEN_5":
        raise AssertionError("MC28 gap inventory missing")
    if mc28.get("open_diagnostic_count") != 5:
        raise AssertionError("MC28 open-gap count changed")

    rows = source._aligned_source_rows(
        {
            "NAS100": args.r6_nas,
            "SP500": args.r6_sp,
            "US30": args.r6_us,
        },
        partition="mc26_real_all_facet_binding",
        require_future=False,
    )
    if not rows:
        raise ValueError("MC26 requires real source rows")
    observation, _states, pre, future = rows[0]
    if future is not None:
        raise AssertionError("MC26 mechanism proof cannot attach future evidence")

    world = build_counterfactual_world_distribution(observation)
    strongest = max(
        world.paths,
        key=lambda item: (item.probability_bps, item.kind.value),
    )
    unknown = next(
        item
        for item in world.paths
        if item.kind is CounterfactualWorldKind.UNKNOWN_SHOCK
    )
    specialist_support, specialist_disagreement = _specialist_disagreement(
        pre,
        observation,
    )
    uncertainty_evidence, uncertainty_bps = _uncertainty(
        observation,
        specialist_disagreement_bps=specialist_disagreement,
    )
    novelty = assess_regime_novelty(
        uncertainty_evidence,
        closest_known_structures=("R6_CONSUMED_SOURCE_STRUCTURE",),
    )
    novelty_uncertainty = max(
        novelty.novelty_bps,
        novelty.historical_distance_bps,
        novelty.regime_unfamiliarity_bps,
        novelty.model_disagreement_bps,
    )
    negative = max(
        observation.structural_fragility_bps,
        observation.anomaly_bps,
        observation.leader_divergence_bps,
    )

    source_ref = f"artifact:{R6_SOURCE_ARTIFACT_ID}"
    facets = (
        CognitiveFacetEvidence(
            facet=CognitiveFacet.WORLD_MODELS,
            support_bps=strongest.probability_bps,
            contradiction_bps=unknown.probability_bps,
            uncertainty_bps=max(
                unknown.probability_bps,
                10_000 - strongest.probability_bps,
            ),
            critical_negative=False,
            evidence_refs=_refs(
                source_ref,
                f"artifact:{MC18_ARTIFACT_ID}",
                f"run:{MC18_RUN_ID}",
            ),
        ),
        CognitiveFacetEvidence(
            facet=CognitiveFacet.SPECIALIST_DISAGREEMENT,
            support_bps=specialist_support,
            contradiction_bps=specialist_disagreement,
            uncertainty_bps=specialist_disagreement,
            critical_negative=False,
            evidence_refs=_refs(source_ref, "engine:hypothesis_ensemble"),
        ),
        CognitiveFacetEvidence(
            facet=CognitiveFacet.NEGATIVE_EVIDENCE,
            support_bps=10_000 - negative,
            contradiction_bps=negative,
            uncertainty_bps=0,
            critical_negative=False,
            evidence_refs=_refs(source_ref, "engine:source_negative_evidence"),
        ),
        CognitiveFacetEvidence(
            facet=CognitiveFacet.UNCERTAINTY,
            support_bps=10_000 - uncertainty_bps,
            contradiction_bps=0,
            uncertainty_bps=uncertainty_bps,
            critical_negative=False,
            evidence_refs=_refs(
                source_ref,
                f"artifact:{MC15_ARTIFACT_ID}",
                f"run:{MC15_RUN_ID}",
            ),
        ),
        CognitiveFacetEvidence(
            facet=CognitiveFacet.OOD_NOVELTY,
            support_bps=10_000 - novelty_uncertainty,
            contradiction_bps=0,
            uncertainty_bps=novelty_uncertainty,
            critical_negative=False,
            evidence_refs=_refs(
                source_ref,
                "engine:meta_learning_regime_adaptation",
            ),
        ),
        CognitiveFacetEvidence(
            facet=CognitiveFacet.TRAJECTORY_STATE,
            support_bps=10_000 - observation.regime_transition_bps,
            contradiction_bps=observation.regime_transition_bps,
            uncertainty_bps=observation.structural_fragility_bps,
            critical_negative=False,
            evidence_refs=_refs(
                source_ref,
                f"artifact:{MC19_ARTIFACT_ID}",
                f"run:{MC19_RUN_ID}",
            ),
        ),
        CognitiveFacetEvidence(
            facet=CognitiveFacet.STABILITY,
            support_bps=0,
            contradiction_bps=0,
            uncertainty_bps=10_000,
            critical_negative=False,
            evidence_refs=_refs(
                f"artifact:{MC20_ARTIFACT_ID}",
                f"run:{MC20_RUN_ID}",
                "gap:NON_COTEMPORAL_R6_VS_OPERATIONAL_STABILITY",
            ),
        ),
        CognitiveFacetEvidence(
            facet=CognitiveFacet.CAUSAL_CONSISTENCY,
            support_bps=0,
            contradiction_bps=0,
            uncertainty_bps=10_000,
            critical_negative=False,
            evidence_refs=_refs(
                f"artifact:{MC14_ARTIFACT_ID}",
                f"run:{MC14_RUN_ID}",
                "finding:ZERO_STRICT_LATENT_CAUSAL_CANDIDATES",
            ),
        ),
        CognitiveFacetEvidence(
            facet=CognitiveFacet.INFORMATION_GAPS,
            support_bps=0,
            contradiction_bps=0,
            uncertainty_bps=10_000,
            critical_negative=False,
            evidence_refs=_refs(
                f"artifact:{MC28_ARTIFACT_ID}",
                f"run:{MC28_RUN_ID}",
                "finding:FIVE_MANDATORY_STANDARD_006_DIAGNOSTICS_OPEN",
            ),
        ),
    )

    real = arbitrate_shared_situation(
        "MC26:R6_REAL_SOURCE_WITH_CURRENT_EVIDENCE_BOUNDARIES",
        facets,
    )
    real_repeat = arbitrate_shared_situation(
        "MC26:R6_REAL_SOURCE_WITH_CURRENT_EVIDENCE_BOUNDARIES",
        facets,
    )

    critical_facets = tuple(
        CognitiveFacetEvidence(
            facet=item.facet,
            support_bps=(0 if item.facet is CognitiveFacet.NEGATIVE_EVIDENCE else item.support_bps),
            contradiction_bps=(
                9_500
                if item.facet is CognitiveFacet.NEGATIVE_EVIDENCE
                else item.contradiction_bps
            ),
            uncertainty_bps=item.uncertainty_bps,
            critical_negative=(
                item.facet is CognitiveFacet.NEGATIVE_EVIDENCE
            ),
            evidence_refs=(
                _refs(
                    f"artifact:{STI5_ARTIFACT_ID}",
                    f"run:{STI5_RUN_ID}",
                    "finding:STI5_V1_FALSIFIED_ON_CONSUMED_EVIDENCE",
                )
                if item.facet is CognitiveFacet.NEGATIVE_EVIDENCE
                else item.evidence_refs
            ),
        )
        for item in facets
    )
    critical = arbitrate_shared_situation(
        "MC26:REAL_MATERIAL_FALSIFICATION_CONFLICT_CASE",
        critical_facets,
    )

    all_real_bound = all(item.evidence_refs for item in real.facets)
    deterministic = real.fingerprint() == real_repeat.fingerprint()
    no_authority = all(
        not value
        for value in (
            real.trading_command,
            real.sizing_authority,
            real.capital_authority,
            real.risk_authority,
            real.broker_authority,
            critical.trading_command,
            critical.sizing_authority,
            critical.capital_authority,
            critical.risk_authority,
            critical.broker_authority,
        )
    )
    completed = (
        len(real.facets) == 9
        and all_real_bound
        and deterministic
        and real.state is SharedSituationState.INSUFFICIENT
        and real.information_gap_preserved
        and critical.state is SharedSituationState.CONTESTED
        and critical.assertiveness_bps <= 2_500
        and critical.critical_negative_preserved
        and no_authority
    )
    payload = {
        "identity": IDENTITY,
        "status": (
            "MC26_COGNITIVE_ARBITRATION_COMPLETED_AND_PROVEN"
            if completed
            else "MC26_REAL_ALL_FACET_ARBITRATION_FAILED"
        ),
        "real_facet_count": len(real.facets),
        "all_nine_facets_real_evidence_bound": all_real_bound,
        "real_situation_state": real.state.value,
        "real_assertiveness_bps": real.assertiveness_bps,
        "real_reason_codes": real.reason_codes,
        "real_information_gap_preserved": real.information_gap_preserved,
        "non_cotemporal_operational_state_not_fused": True,
        "causal_absence_preserved_as_uncertainty": True,
        "mandatory_mc28_gaps_preserved": True,
        "critical_conflict_state": critical.state.value,
        "critical_conflict_assertiveness_bps": critical.assertiveness_bps,
        "critical_negative_preserved": critical.critical_negative_preserved,
        "deterministic_replay": deterministic,
        "numeric_facets_are_research_indices_not_calibrated_probabilities": True,
        "trading_command": False,
        "sizing_authority": False,
        "capital_authority": False,
        "risk_authority": False,
        "broker_authority": False,
        "productive_authority": False,
        "mc26_completed_and_proven": completed,
        "master_ledger_mutated": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
