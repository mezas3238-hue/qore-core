# ruff: noqa: I001
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.market_digital_twin import (
    BehaviorHypothesis,
    ExpectedStateTransition,
    LiquidityTopology,
    RegimeStructure,
    TwinObservation,
    TwinPrediction,
    TwinStateValue,
    TwinUncertainty,
    VolatilityTopology,
    build_market_digital_twin,
)
from qore.infrastructure.core_stack_v2.multi_world_engine import (
    WorldModelFamily,
)
from qore.infrastructure.core_stack_v2.multi_world_federation import (
    WorldDiagnostic,
    WorldEvidence,
    build_world_evidence_from_twin,
    update_world_federation,
)


BASE = datetime(2026, 9, 26, 8, 30, tzinfo=UTC)


def _evidence(
    *,
    as_of: datetime,
    winner: WorldModelFamily,
    loser: WorldModelFamily | None = None,
) -> tuple[WorldEvidence, ...]:
    rows = []
    for family in WorldModelFamily:
        prediction_error = 1_000 if family is winner else 6_000
        causal = 9_000 if family is winner else 4_000
        calibration = 8_500 if family is winner else 4_500
        trajectory = 8_500 if family is winner else 4_500
        current = 9_000 if family is winner else 4_500
        if family is loser:
            prediction_error = 9_500
            causal = 1_000
            calibration = 1_000
            trajectory = 1_000
            current = 1_000
        rows.append(
            WorldEvidence(
                family=family,
                as_of=as_of,
                prediction_error_bps=prediction_error,
                prediction_observation_count=10,
                causal_consistency_bps=causal,
                calibration_bps=calibration,
                trajectory_accuracy_bps=trajectory,
                current_evidence_bps=current,
                integrity_bps=9_500,
            )
        )
    return tuple(rows)


def _probability(state, family: WorldModelFamily) -> int:
    return next(
        item.probability_bps
        for item in state.posteriors
        if item.family is family
    )


def test_best_explaining_world_dominates_without_erasing_other_worlds() -> None:
    state = update_world_federation(
        as_of=BASE,
        evidence=_evidence(
            as_of=BASE,
            winner=WorldModelFamily.MOMENTUM_DRIVEN,
        ),
        epistemic_uncertainty_bps=2_000,
        ood_risk_bps=1_000,
    )

    assert state.dominant_world is WorldModelFamily.MOMENTUM_DRIVEN
    assert len(state.posteriors) == len(WorldModelFamily)
    assert all(item.probability_bps > 0 for item in state.posteriors)
    assert sum(item.probability_bps for item in state.posteriors) == 10_000
    assert state.execution_authority is False
    assert state.risk_authority is False
    assert state.sizing_authority is False


def test_sequential_federation_can_replace_a_failing_world() -> None:
    first = update_world_federation(
        as_of=BASE,
        evidence=_evidence(
            as_of=BASE,
            winner=WorldModelFamily.MOMENTUM_DRIVEN,
        ),
        epistemic_uncertainty_bps=1_500,
        ood_risk_bps=500,
    )
    second_time = BASE + timedelta(minutes=1)
    second = update_world_federation(
        as_of=second_time,
        evidence=_evidence(
            as_of=second_time,
            winner=WorldModelFamily.LIQUIDITY_DRIVEN,
            loser=WorldModelFamily.MOMENTUM_DRIVEN,
        ),
        epistemic_uncertainty_bps=1_500,
        ood_risk_bps=500,
        previous=first,
    )

    assert first.dominant_world is WorldModelFamily.MOMENTUM_DRIVEN
    assert second.dominant_world is WorldModelFamily.LIQUIDITY_DRIVEN
    assert second.dominant_world_changed is True
    assert second.previous_dominant_world is WorldModelFamily.MOMENTUM_DRIVEN


def test_regime_transition_prior_prevents_absorbing_world_monopoly() -> None:
    state = None
    for minute in range(50):
        as_of = BASE + timedelta(minutes=minute)
        state = update_world_federation(
            as_of=as_of,
            evidence=_evidence(
                as_of=as_of,
                winner=WorldModelFamily.MOMENTUM_DRIVEN,
            ),
            epistemic_uncertainty_bps=1_000,
            ood_risk_bps=500,
            previous=state,
        )

    assert state is not None
    assert state.regime_transition_bps == 500
    assert _probability(state, WorldModelFamily.MOMENTUM_DRIVEN) < 10_000
    assert all(item.probability_bps > 0 for item in state.posteriors)

    first_shift_at = BASE + timedelta(minutes=50)
    first_shift = update_world_federation(
        as_of=first_shift_at,
        evidence=_evidence(
            as_of=first_shift_at,
            winner=WorldModelFamily.LIQUIDITY_DRIVEN,
            loser=WorldModelFamily.MOMENTUM_DRIVEN,
        ),
        epistemic_uncertainty_bps=1_000,
        ood_risk_bps=500,
        previous=state,
    )
    second_shift_at = BASE + timedelta(minutes=51)
    second_shift = update_world_federation(
        as_of=second_shift_at,
        evidence=_evidence(
            as_of=second_shift_at,
            winner=WorldModelFamily.LIQUIDITY_DRIVEN,
            loser=WorldModelFamily.MOMENTUM_DRIVEN,
        ),
        epistemic_uncertainty_bps=1_000,
        ood_risk_bps=500,
        previous=first_shift,
    )

    assert _probability(
        second_shift,
        WorldModelFamily.LIQUIDITY_DRIVEN,
    ) > _probability(
        second_shift,
        WorldModelFamily.MOMENTUM_DRIVEN,
    )
    assert second_shift.dominant_world is WorldModelFamily.LIQUIDITY_DRIVEN


def test_regime_transition_prior_is_bounded() -> None:
    with pytest.raises(ValueError, match="regime_transition_bps"):
        update_world_federation(
            as_of=BASE,
            evidence=_evidence(
                as_of=BASE,
                winner=WorldModelFamily.MOMENTUM_DRIVEN,
            ),
            epistemic_uncertainty_bps=1_000,
            ood_risk_bps=500,
            regime_transition_bps=10_001,
        )


def test_epistemic_uncertainty_increases_unresolved_world_probability() -> None:
    evidence = _evidence(
        as_of=BASE,
        winner=WorldModelFamily.MEAN_REVERSION,
    )
    low = update_world_federation(
        as_of=BASE,
        evidence=evidence,
        epistemic_uncertainty_bps=1_000,
        ood_risk_bps=500,
    )
    high = update_world_federation(
        as_of=BASE,
        evidence=evidence,
        epistemic_uncertainty_bps=9_000,
        ood_risk_bps=8_000,
    )

    assert _probability(
        high,
        WorldModelFamily.UNRESOLVED,
    ) > _probability(
        low,
        WorldModelFamily.UNRESOLVED,
    )


def test_world_federation_requires_complete_world_coverage() -> None:
    incomplete = _evidence(
        as_of=BASE,
        winner=WorldModelFamily.EVENT_DISLOCATION,
    )[:-1]

    with pytest.raises(ValueError, match="every family"):
        update_world_federation(
            as_of=BASE,
            evidence=incomplete,
            epistemic_uncertainty_bps=2_000,
            ood_risk_bps=2_000,
        )


def test_future_world_evidence_fails_closed() -> None:
    future = BASE + timedelta(seconds=1)
    evidence = _evidence(
        as_of=future,
        winner=WorldModelFamily.MACRO_DRIVEN,
    )

    with pytest.raises(ValueError, match="future world evidence"):
        update_world_federation(
            as_of=BASE,
            evidence=evidence,
            epistemic_uncertainty_bps=2_000,
            ood_risk_bps=2_000,
        )


def test_world_diagnostic_supports_all_required_dimensions() -> None:
    diagnostic = WorldDiagnostic(
        family=WorldModelFamily.AGENCY_INVENTORY,
        as_of=BASE,
        causal_consistency_bps=7_000,
        calibration_bps=6_500,
        trajectory_accuracy_bps=6_000,
        current_evidence_bps=7_500,
        integrity_bps=9_000,
    )

    assert diagnostic.family is WorldModelFamily.AGENCY_INVENTORY
    assert diagnostic.integrity_bps == 9_000



def test_federation_consumes_prediction_error_from_market_digital_twin() -> None:
    prediction = TwinPrediction(
        prediction_id="momentum-p1",
        channel="EXPECTED_DISPLACEMENT",
        made_at=BASE - timedelta(minutes=2),
        target_at=BASE - timedelta(minutes=1),
        expected_bps=8_000,
        tolerance_bps=1_000,
        model_family="MOMENTUM_WORLD",
    )
    observation = TwinObservation(
        prediction_id="momentum-p1",
        channel="EXPECTED_DISPLACEMENT",
        observed_at=BASE - timedelta(seconds=30),
        observed_bps=3_000,
    )
    twin = build_market_digital_twin(
        as_of=BASE,
        evidence_cutoff_at=BASE - timedelta(seconds=1),
        observable_state=(
            TwinStateValue(
                "OBSERVED_STRUCTURE",
                6_000,
                7_000,
                BASE - timedelta(seconds=2),
            ),
        ),
        latent_state=(
            TwinStateValue(
                "LATENT_PRESSURE",
                5_500,
                5_000,
                BASE - timedelta(seconds=2),
            ),
        ),
        behavior_hypotheses=(
            BehaviorHypothesis(
                "UNKNOWN_AGENCY",
                5_000,
                2_000,
                ("OBSERVED_STRUCTURE",),
            ),
        ),
        liquidity_topology=LiquidityTopology(
            5_000,
            5_000,
            5_000,
            5_000,
            5_000,
            9_000,
        ),
        volatility_topology=VolatilityTopology(
            5_000,
            5_000,
            5_000,
            5_000,
            5_000,
            9_000,
        ),
        cross_market_dependencies=(),
        regime_structure=RegimeStructure(
            "UNKNOWN",
            5_000,
            5_000,
            5_000,
            5_000,
        ),
        uncertainty=TwinUncertainty(
            3_000,
            3_000,
            3_000,
            2_000,
        ),
        expected_transitions=(
            ExpectedStateTransition(
                3,
                "UNKNOWN",
                5_000,
                2_000,
            ),
        ),
        predictions=(prediction,),
        observations=(observation,),
    )
    diagnostics = tuple(
        WorldDiagnostic(
            family=family,
            as_of=BASE,
            causal_consistency_bps=5_000,
            calibration_bps=5_000,
            trajectory_accuracy_bps=5_000,
            current_evidence_bps=5_000,
        )
        for family in WorldModelFamily
    )

    evidence = build_world_evidence_from_twin(
        twin=twin,
        diagnostics=diagnostics,
    )
    by_family = {item.family: item for item in evidence}

    assert (
        by_family[WorldModelFamily.MOMENTUM_DRIVEN].prediction_error_bps
        == 10_000
    )
    assert (
        by_family[WorldModelFamily.MOMENTUM_DRIVEN].prediction_observation_count
        == 1
    )
    assert (
        by_family[WorldModelFamily.LIQUIDITY_DRIVEN].prediction_error_bps
        == 5_000
    )
