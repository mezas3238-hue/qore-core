from __future__ import annotations

from qore.infrastructure.core_stack_v2.uncertainty_decomposition import (
    UncertaintyEvidence,
    decompose_uncertainty,
)


def test_epistemic_dominance_is_distinguished_from_market_noise() -> None:
    state = decompose_uncertainty(
        UncertaintyEvidence(
            observation_noise_bps=2_000,
            realized_path_variability_bps=2_500,
            scenario_overlap_bps=2_000,
            model_disagreement_bps=8_000,
            novelty_bps=8_500,
            calibration_error_bps=7_500,
            historical_distance_bps=8_000,
            regime_unfamiliarity_bps=8_000,
        )
    )

    assert state.dominant_source == "EPISTEMIC"
    assert state.epistemic_bps > state.aleatoric_bps
    assert state.confidence_ceiling_bps < 3_000
    assert state.execution_authority is False


def test_chaotic_but_familiar_market_is_aleatoric() -> None:
    state = decompose_uncertainty(
        UncertaintyEvidence(
            observation_noise_bps=8_500,
            realized_path_variability_bps=9_000,
            scenario_overlap_bps=8_000,
            model_disagreement_bps=2_000,
            novelty_bps=1_500,
            calibration_error_bps=2_000,
            historical_distance_bps=1_500,
            regime_unfamiliarity_bps=2_000,
        )
    )

    assert state.dominant_source == "ALEATORIC"
    assert state.aleatoric_bps > state.epistemic_bps
