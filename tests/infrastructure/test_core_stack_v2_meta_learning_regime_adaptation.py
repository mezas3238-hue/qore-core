import pytest

from qore.infrastructure.core_stack_v2.meta_learning_regime_adaptation import (
    AdaptationDisposition,
    AdaptiveHypothesisProposal,
    NoveltyState,
    assess_regime_novelty,
)
from qore.infrastructure.core_stack_v2.uncertainty_decomposition_v2 import (
    SharedUncertaintyEvidenceV2,
)


def _evidence(*, novelty: int, distance: int, unfamiliarity: int, missing: int = 0):
    return SharedUncertaintyEvidenceV2(
        observation_noise_bps=1000,
        realized_path_variability_bps=1000,
        scenario_overlap_bps=1000,
        model_disagreement_bps=3000,
        novelty_bps=novelty,
        calibration_error_bps=1000,
        historical_distance_bps=distance,
        data_missingness_bps=missing,
        timestamp_ambiguity_bps=0,
        provider_anomaly_bps=0,
        regime_unfamiliarity_bps=unfamiliarity,
        regime_transition_bps=2000,
        relationship_instability_bps=2000,
        causal_identification_ambiguity_bps=2000,
        confounding_risk_bps=2000,
        transportability_uncertainty_bps=2000,
        simulation_model_gap_bps=2000,
        scenario_coverage_gap_bps=2000,
        simulation_instability_bps=2000,
    )


def test_high_novelty_never_masquerades_as_known() -> None:
    result = assess_regime_novelty(
        _evidence(novelty=8000, distance=7500, unfamiliarity=7200),
        closest_known_structures=("REGIME_A",),
    )
    assert result.state is NoveltyState.NOVEL
    assert result.unknown_treated_as_known is False


def test_missing_data_yields_unresolved_not_novel_certainty() -> None:
    result = assess_regime_novelty(
        _evidence(novelty=8000, distance=7500, unfamiliarity=7200, missing=8000),
        closest_known_structures=(),
    )
    assert result.state is NoveltyState.UNRESOLVED


def test_validated_adaptation_requires_validation() -> None:
    novelty = assess_regime_novelty(
        _evidence(novelty=8000, distance=7500, unfamiliarity=7200),
        closest_known_structures=("REGIME_A",),
    )
    with pytest.raises(ValueError, match="validation evidence"):
        AdaptiveHypothesisProposal(
            proposal_id="adapt-1",
            novelty=novelty,
            hypothesis_ref="hypothesis:new-regime",
            validation_refs=(),
            disposition=AdaptationDisposition.VALIDATED_ADAPTATION,
        )
