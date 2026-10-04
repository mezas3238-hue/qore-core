from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.core_stack_v2.counterfactual_world_calibration import (
    CounterfactualFailureCalibration,
    calibrated_failure_probability_bps,
    raw_failure_probability_bps,
)
from qore.infrastructure.core_stack_v2.counterfactual_world_engine import (
    build_counterfactual_world_distribution,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)


def _observation() -> SharedOpportunitySourceObservation:
    now = datetime(2026, 10, 4, 18, 0, tzinfo=UTC)
    return SharedOpportunitySourceObservation(
        observation_id="mc18-calibration-test",
        asset="NAS100",
        as_of=now,
        evidence_cutoff_at=now,
        direction_sign=1,
        data_integrity_bps=10_000,
        compression_bps=4_000,
        liquidity_accumulation_bps=5_000,
        failed_auction_bps=5_000,
        displacement_bps=6_000,
        acceptance_bps=5_500,
        absorption_bps=4_000,
        leader_confirmation_bps=5_000,
        leader_divergence_bps=5_000,
        momentum_persistence_bps=5_500,
        momentum_decay_bps=4_500,
        structural_fragility_bps=5_000,
        liquidity_vacuum_bps=5_000,
        regime_transition_bps=5_000,
        anomaly_bps=3_000,
        provenance_refs=("mc18:calibration-test",),
    )


def _calibration() -> CounterfactualFailureCalibration:
    return CounterfactualFailureCalibration(
        calibration_id="test-calibration",
        intercept=-1.0,
        coefficient=2.0,
        fitted_on="CONSUMED_DEVELOPMENT",
        target_definition="TEST_BINARY_FAILURE",
    )


def test_failure_mass_is_bounded_and_deterministic() -> None:
    distribution = build_counterfactual_world_distribution(_observation())
    first = raw_failure_probability_bps(distribution)
    second = raw_failure_probability_bps(distribution)

    assert 0 <= first <= 10_000
    assert first == second


@pytest.mark.parametrize("raw", (0, 2_500, 5_000, 7_500, 10_000))
def test_calibrated_probability_is_bounded(raw: int) -> None:
    value = calibrated_failure_probability_bps(raw, _calibration())
    assert 0 <= value <= 10_000


def test_positive_calibration_is_monotone() -> None:
    calibration = _calibration()
    values = [
        calibrated_failure_probability_bps(raw, calibration)
        for raw in (0, 2_500, 5_000, 7_500, 10_000)
    ]
    assert values == sorted(values)


def test_calibration_rejects_nonpositive_slope() -> None:
    with pytest.raises(ValueError, match="positive monotonicity"):
        CounterfactualFailureCalibration(
            calibration_id="invalid",
            intercept=0.0,
            coefficient=0.0,
            fitted_on="CONSUMED_DEVELOPMENT",
            target_definition="TEST",
        )


def test_calibration_has_no_productive_authority() -> None:
    calibration = _calibration()
    assert calibration.productive_authority is False
    assert len(calibration.fingerprint()) == 64
