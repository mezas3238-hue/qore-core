from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from qore.infrastructure.core_stack_v2.shared_continuation_positive_tail_intelligence import (
    SharedContinuationPositiveTailPolicy,
    SharedPositionCausalObservation,
    assess_continuation_positive_tail,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedSupportState,
    SharedTraderIntelligenceValidationError,
)

T0 = datetime(2026, 9, 29, 23, 0, tzinfo=UTC)


def _observation(**overrides: object) -> SharedPositionCausalObservation:
    values: dict[str, object] = {
        "observation_id": "position-observation-001",
        "position_id": "vt31-position-001",
        "asset": "NAS100",
        "as_of": T0,
        "evidence_cutoff_at": T0,
        "minutes_since_fill": 8,
        "progress_bps": 7_500,
        "signed_close_r_bps": 7_000,
        "efficiency_bps": 7_500,
        "overlap_bps": 2_000,
        "signed_body_r_bps": 3_000,
        "peer_confirmation_bps": 8_000,
        "breadth_bps": 8_000,
        "peer_transition_adverse_bps": 1_500,
        "world_support_bps": 8_000,
        "world_fragility_bps": 1_500,
        "data_integrity_bps": 10_000,
        "provenance_refs": ("immutable-source-bars",),
    }
    values.update(overrides)
    return SharedPositionCausalObservation(**values)  # type: ignore[arg-type]


def _policy() -> SharedContinuationPositiveTailPolicy:
    return SharedContinuationPositiveTailPolicy(
        policy_id="sti6-source-only-v1",
        continuation_threshold_bps=6_000,
        positive_tail_threshold_bps=7_000,
        minimum_integrity_bps=9_500,
        source_only_calibration=True,
        evidence_refs=("r8-source-only-distribution",),
    )


def test_continuation_engine_derives_positive_tail_without_hold_authority() -> None:
    assessment = assess_continuation_positive_tail(
        _observation(),
        policy=_policy(),
    )

    assert assessment.materially_supported is True
    assert assessment.positive_tail_candidate is True
    assert assessment.continuation_support in {
        SharedSupportState.ELEVATED,
        SharedSupportState.STRONG,
    }
    assert assessment.mandatory_hold is False
    assert assessment.position_management_authority is False
    assert assessment.execution_authority is False
    assert assessment.sizing_authority is False


def test_adverse_position_does_not_masquerade_as_continuation() -> None:
    assessment = assess_continuation_positive_tail(
        _observation(
            progress_bps=1_000,
            signed_close_r_bps=-7_000,
            efficiency_bps=-7_500,
            overlap_bps=8_500,
            signed_body_r_bps=-5_000,
            peer_confirmation_bps=2_000,
            breadth_bps=2_500,
            peer_transition_adverse_bps=8_000,
            world_support_bps=2_000,
            world_fragility_bps=8_000,
        ),
        policy=_policy(),
    )

    assert assessment.materially_supported is False
    assert assessment.positive_tail_candidate is False
    assert assessment.failure_hazard_bps > assessment.continuation_score_bps


def test_bad_data_fails_to_insufficient() -> None:
    assessment = assess_continuation_positive_tail(
        _observation(data_integrity_bps=8_000),
        policy=_policy(),
    )

    assert assessment.continuation_support is SharedSupportState.INSUFFICIENT
    assert assessment.positive_tail_support is SharedSupportState.INSUFFICIENT
    assert assessment.failure_hazard is SharedSupportState.INSUFFICIENT


def test_source_observation_rejects_outcome_and_pnl_inputs() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="source-time evidence only",
    ):
        replace(_observation(), future_outcome_used=True)

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="source-time evidence only",
    ):
        replace(_observation(), pnl_used=True)


def test_continuation_policy_must_be_source_only() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="calibration must be source-only",
    ):
        replace(_policy(), source_only_calibration=False)
