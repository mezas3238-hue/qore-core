from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.core_stack_v2.shared_continuation_positive_tail_intelligence import (
    SharedPositionCausalObservation,
)
from qore.infrastructure.core_stack_v2.shared_continuation_positive_tail_v2 import (
    SharedContinuationTrajectoryV2Policy,
    assess_continuation_trajectory_v2,
    continuation_trajectory_v2_features,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedSupportState,
)

T0 = datetime(2026, 9, 30, 7, 30, tzinfo=UTC)


def _obs(
    minute: int,
    *,
    close: int,
    efficiency: int,
    progress: int,
    overlap: int,
    peer_confirmation: int = 8_000,
    breadth: int = 8_000,
    peer_adverse: int = 2_000,
    world_support: int = 8_000,
    world_fragility: int = 2_000,
    integrity: int = 10_000,
) -> SharedPositionCausalObservation:
    at = T0 + timedelta(minutes=minute)
    return SharedPositionCausalObservation(
        observation_id=f"obs-{minute}",
        position_id="position-1",
        asset="NAS100",
        as_of=at,
        evidence_cutoff_at=at,
        minutes_since_fill=minute,
        progress_bps=progress,
        signed_close_r_bps=close,
        efficiency_bps=efficiency,
        overlap_bps=overlap,
        signed_body_r_bps=close,
        peer_confirmation_bps=peer_confirmation,
        breadth_bps=breadth,
        peer_transition_adverse_bps=peer_adverse,
        world_support_bps=world_support,
        world_fragility_bps=world_fragility,
        data_integrity_bps=integrity,
        provenance_refs=("causal-source",),
    )


def _policy() -> SharedContinuationTrajectoryV2Policy:
    return SharedContinuationTrajectoryV2Policy(
        policy_id="sti6-v2-test",
        sequence_window=4,
        continuation_velocity_threshold_bps=400,
        tail_velocity_threshold_bps=500,
        local_expansion_threshold_bps=4_500,
        persistence_threshold_bps=5_000,
        max_failure_hazard_bps=4_500,
        minimum_integrity_bps=9_500,
        source_only_calibration=True,
        evidence_refs=("r8-source-only",),
    )


def test_v2_rewards_accelerating_persistent_local_expansion() -> None:
    observations = (
        _obs(1, close=500, efficiency=500, progress=1_000, overlap=4_000),
        _obs(2, close=1_500, efficiency=1_800, progress=2_500, overlap=3_500),
        _obs(3, close=3_000, efficiency=3_500, progress=5_000, overlap=2_500),
        _obs(4, close=5_000, efficiency=5_500, progress=7_000, overlap=1_500),
    )
    assessment = assess_continuation_trajectory_v2(
        observations,
        policy=_policy(),
    )

    assert assessment.continuation_velocity_bps > 0
    assert assessment.tail_velocity_bps > 0
    assert assessment.expansion_persistence_bps >= 5_000
    assert assessment.materially_supported is True
    assert assessment.positive_tail_candidate is True
    assert assessment.failure_veto is False
    assert assessment.position_management_authority is False
    assert assessment.execution_authority is False
    assert assessment.sizing_authority is False


def test_failure_hazard_veto_blocks_false_continuation() -> None:
    observations = (
        _obs(1, close=500, efficiency=500, progress=1_000, overlap=7_000),
        _obs(
            2,
            close=1_500,
            efficiency=1_500,
            progress=2_500,
            overlap=8_000,
            peer_confirmation=2_000,
            breadth=2_000,
            peer_adverse=8_000,
            world_support=2_000,
            world_fragility=8_000,
        ),
        _obs(
            3,
            close=3_000,
            efficiency=3_000,
            progress=5_000,
            overlap=8_500,
            peer_confirmation=1_500,
            breadth=1_500,
            peer_adverse=9_000,
            world_support=1_500,
            world_fragility=9_000,
        ),
    )
    assessment = assess_continuation_trajectory_v2(
        observations,
        policy=_policy(),
    )

    assert assessment.failure_veto is True
    assert assessment.materially_supported is False
    assert assessment.positive_tail_candidate is False
    assert "FAILURE_HAZARD_VETO" in assessment.reason_codes


def test_bad_integrity_fails_to_insufficient() -> None:
    observations = (
        _obs(
            1,
            close=1_000,
            efficiency=1_000,
            progress=2_000,
            overlap=3_000,
            integrity=7_000,
        ),
    )
    assessment = assess_continuation_trajectory_v2(
        observations,
        policy=_policy(),
    )

    assert assessment.continuation_support is SharedSupportState.INSUFFICIENT
    assert assessment.positive_tail_support is SharedSupportState.INSUFFICIENT
    assert assessment.failure_hazard is SharedSupportState.INSUFFICIENT
    assert assessment.materially_supported is False


def test_features_are_deterministic() -> None:
    observations = (
        _obs(1, close=1_000, efficiency=1_200, progress=2_000, overlap=3_500),
        _obs(2, close=2_000, efficiency=2_500, progress=4_000, overlap=3_000),
        _obs(3, close=4_000, efficiency=4_500, progress=6_000, overlap=2_000),
    )
    first = continuation_trajectory_v2_features(
        observations,
        sequence_window=3,
    )
    second = continuation_trajectory_v2_features(
        observations,
        sequence_window=3,
    )
    assert first == second
