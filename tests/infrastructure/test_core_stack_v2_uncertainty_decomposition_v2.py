from __future__ import annotations

from dataclasses import replace

import pytest

from qore.infrastructure.core_stack_v2.uncertainty_decomposition_v2 import (
    SharedUncertaintyEvidenceV2,
    SharedUncertaintySource,
    decompose_uncertainty_v2,
)


def _evidence(**overrides: int) -> SharedUncertaintyEvidenceV2:
    values = {
        "observation_noise_bps": 2_000,
        "realized_path_variability_bps": 2_000,
        "scenario_overlap_bps": 2_000,
        "model_disagreement_bps": 2_000,
        "novelty_bps": 2_000,
        "calibration_error_bps": 2_000,
        "historical_distance_bps": 2_000,
        "data_missingness_bps": 1_000,
        "timestamp_ambiguity_bps": 1_000,
        "provider_anomaly_bps": 1_000,
        "regime_unfamiliarity_bps": 2_000,
        "regime_transition_bps": 2_000,
        "relationship_instability_bps": 2_000,
        "causal_identification_ambiguity_bps": 2_000,
        "confounding_risk_bps": 2_000,
        "transportability_uncertainty_bps": 2_000,
        "simulation_model_gap_bps": 2_000,
        "scenario_coverage_gap_bps": 2_000,
        "simulation_instability_bps": 2_000,
    }
    values.update(overrides)
    return SharedUncertaintyEvidenceV2(**values)


def test_data_uncertainty_is_first_class_and_limits_assertiveness() -> None:
    state = decompose_uncertainty_v2(
        _evidence(
            data_missingness_bps=9_000,
            timestamp_ambiguity_bps=8_500,
            provider_anomaly_bps=9_500,
        )
    )

    assert state.data_bps == 9_000
    assert SharedUncertaintySource.DATA in state.dominant_sources
    assert state.assertiveness_ceiling_bps == 1_000
    assert state.calibration_state == "UNCALIBRATED"


def test_regime_and_causal_uncertainty_remain_separate() -> None:
    state = decompose_uncertainty_v2(
        _evidence(
            regime_unfamiliarity_bps=8_000,
            regime_transition_bps=8_500,
            relationship_instability_bps=8_000,
            causal_identification_ambiguity_bps=4_000,
            confounding_risk_bps=4_000,
            transportability_uncertainty_bps=4_000,
        )
    )

    assert state.regime_bps > state.causal_bps
    assert state.regime_bps > state.epistemic_bps
    assert state.dominant_sources == (SharedUncertaintySource.REGIME,)


def test_simulation_uncertainty_is_not_epistemic_alias() -> None:
    state = decompose_uncertainty_v2(
        _evidence(
            simulation_model_gap_bps=9_000,
            scenario_coverage_gap_bps=9_000,
            simulation_instability_bps=8_500,
        )
    )

    assert state.simulation_bps > state.epistemic_bps
    assert SharedUncertaintySource.SIMULATION in state.dominant_sources


def test_multiple_near_max_sources_are_preserved() -> None:
    state = decompose_uncertainty_v2(
        _evidence(
            model_disagreement_bps=8_000,
            novelty_bps=8_000,
            calibration_error_bps=8_000,
            historical_distance_bps=8_000,
            regime_unfamiliarity_bps=7_700,
            regime_transition_bps=7_700,
            relationship_instability_bps=7_700,
        )
    )

    assert state.dominant_sources == (
        SharedUncertaintySource.EPISTEMIC,
        SharedUncertaintySource.REGIME,
    )


def test_future_or_outcome_evidence_is_rejected() -> None:
    with pytest.raises(ValueError, match="source-time only"):
        replace(_evidence(), future_market_used=True)

    with pytest.raises(ValueError, match="source-time only"):
        replace(_evidence(), outcome_used=True)


def test_decomposition_has_no_downstream_authority() -> None:
    state = decompose_uncertainty_v2(_evidence())

    assert state.execution_authority is False
    assert state.risk_authority is False
    assert state.sizing_authority is False
    assert state.capital_authority is False
