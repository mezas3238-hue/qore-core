from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.market_digital_twin import (
    BehaviorHypothesis,
    CrossMarketDependency,
    ExpectedStateTransition,
    LiquidityTopology,
    RegimeStructure,
    TwinDiagnosis,
    TwinObservation,
    TwinPrediction,
    TwinStateValue,
    TwinUncertainty,
    VolatilityTopology,
    build_market_digital_twin,
)


NOW = datetime(2026, 9, 26, 3, 0, tzinfo=UTC)


def _build(
    *,
    predictions: tuple[TwinPrediction, ...] = (),
    observations: tuple[TwinObservation, ...] = (),
    uncertainty: TwinUncertainty | None = None,
):
    return build_market_digital_twin(
        as_of=NOW,
        evidence_cutoff_at=NOW - timedelta(seconds=1),
        observable_state=(
            TwinStateValue(
                concept="STRUCTURE_ACCEPTANCE",
                probability_bps=7_000,
                confidence_bps=8_000,
                evidence_cutoff_at=NOW - timedelta(seconds=2),
            ),
        ),
        latent_state=(
            TwinStateValue(
                concept="HIDDEN_LIQUIDITY_PRESSURE",
                probability_bps=6_500,
                confidence_bps=6_000,
                evidence_cutoff_at=NOW - timedelta(seconds=2),
            ),
        ),
        behavior_hypotheses=(
            BehaviorHypothesis(
                behavior="PASSIVE_ABSORPTION",
                probability_bps=6_200,
                confidence_bps=5_800,
                supporting_evidence=("FAILED_AUCTION", "PRICE_RESPONSE"),
            ),
        ),
        liquidity_topology=LiquidityTopology(
            available_liquidity_bps=6_500,
            absorption_bps=6_200,
            vulnerability_bps=3_000,
            vacuum_risk_bps=2_500,
            imbalance_bps=5_500,
            integrity_bps=9_000,
        ),
        volatility_topology=VolatilityTopology(
            realized_state_bps=5_500,
            expansion_pressure_bps=6_000,
            compression_pressure_bps=2_500,
            shock_risk_bps=2_000,
            persistence_bps=6_500,
            integrity_bps=9_000,
        ),
        cross_market_dependencies=(
            CrossMarketDependency(
                source_node="LEADER",
                target_node="TARGET",
                dependence_bps=7_000,
                lead_lag_bps=6_000,
                stability_bps=8_000,
                break_risk_bps=2_000,
            ),
        ),
        regime_structure=RegimeStructure(
            regime="EXPANSION",
            transition_probability_bps=2_500,
            familiarity_bps=8_000,
            anomaly_bps=1_500,
            stability_bps=8_000,
        ),
        uncertainty=uncertainty
        or TwinUncertainty(
            aleatoric_bps=3_000,
            epistemic_bps=2_000,
            model_disagreement_bps=2_500,
            ood_risk_bps=1_000,
        ),
        expected_transitions=(
            ExpectedStateTransition(
                horizon_bars=3,
                target_state="CONTINUATION",
                probability_bps=6_500,
                confidence_bps=6_000,
            ),
        ),
        predictions=predictions,
        observations=observations,
    )


def test_digital_twin_snapshot_is_deterministic_and_authority_free() -> None:
    left = _build()
    right = _build()

    assert left.fingerprint == right.fingerprint
    assert left.diagnosis is TwinDiagnosis.INSUFFICIENT
    assert left.outcome_used is False
    assert left.pnl_used is False
    assert left.future_market_used is False
    assert left.execution_authority is False
    assert left.risk_authority is False
    assert left.sizing_authority is False


def test_matured_prediction_error_creates_model_revision_pressure() -> None:
    prediction = TwinPrediction(
        prediction_id="p1",
        channel="EXPECTED_DISPLACEMENT",
        made_at=NOW - timedelta(minutes=2),
        target_at=NOW - timedelta(minutes=1),
        expected_bps=8_000,
        tolerance_bps=1_000,
        model_family="MOMENTUM_WORLD",
    )
    observation = TwinObservation(
        prediction_id="p1",
        channel="EXPECTED_DISPLACEMENT",
        observed_at=NOW - timedelta(seconds=30),
        observed_bps=3_000,
    )

    twin = _build(
        predictions=(prediction,),
        observations=(observation,),
    )

    assert len(twin.prediction_error_ledger) == 1
    record = twin.prediction_error_ledger[0]
    assert record.signed_error_bps == -5_000
    assert record.absolute_error_bps == 5_000
    assert record.surprise_bps == 10_000
    assert twin.diagnosis is TwinDiagnosis.MODEL_DRIFT
    assert twin.model_revision_pressure_bps >= 7_000


def test_unmatured_prediction_stays_unresolved_without_future_information() -> None:
    prediction = TwinPrediction(
        prediction_id="p-future",
        channel="EXPECTED_VOLATILITY",
        made_at=NOW - timedelta(seconds=10),
        target_at=NOW + timedelta(minutes=1),
        expected_bps=5_000,
        tolerance_bps=1_000,
        model_family="LIQUIDITY_WORLD",
    )

    twin = _build(predictions=(prediction,))

    assert twin.prediction_error_ledger == ()
    assert twin.unresolved_prediction_ids == ("p-future",)


def test_future_observation_fails_closed() -> None:
    prediction = TwinPrediction(
        prediction_id="p1",
        channel="EXPECTED_VOLATILITY",
        made_at=NOW - timedelta(minutes=2),
        target_at=NOW - timedelta(minutes=1),
        expected_bps=5_000,
        tolerance_bps=1_000,
        model_family="LIQUIDITY_WORLD",
    )
    observation = TwinObservation(
        prediction_id="p1",
        channel="EXPECTED_VOLATILITY",
        observed_at=NOW + timedelta(seconds=1),
        observed_bps=5_200,
    )

    with pytest.raises(ValueError, match="future observation"):
        _build(predictions=(prediction,), observations=(observation,))


def test_high_epistemic_uncertainty_raises_revision_pressure() -> None:
    prediction = TwinPrediction(
        prediction_id="p1",
        channel="EXPECTED_LIQUIDITY_RESPONSE",
        made_at=NOW - timedelta(minutes=2),
        target_at=NOW - timedelta(minutes=1),
        expected_bps=5_000,
        tolerance_bps=2_000,
        model_family="LIQUIDITY_WORLD",
    )
    observation = TwinObservation(
        prediction_id="p1",
        channel="EXPECTED_LIQUIDITY_RESPONSE",
        observed_at=NOW - timedelta(seconds=30),
        observed_bps=5_100,
    )
    low = _build(
        predictions=(prediction,),
        observations=(observation,),
        uncertainty=TwinUncertainty(
            aleatoric_bps=2_000,
            epistemic_bps=1_000,
            model_disagreement_bps=1_000,
            ood_risk_bps=500,
        ),
    )
    high = _build(
        predictions=(prediction,),
        observations=(observation,),
        uncertainty=TwinUncertainty(
            aleatoric_bps=2_000,
            epistemic_bps=8_000,
            model_disagreement_bps=7_000,
            ood_risk_bps=6_000,
        ),
    )

    assert high.model_revision_pressure_bps > low.model_revision_pressure_bps
