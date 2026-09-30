from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_continuation_positive_tail_intelligence import (
    SharedPositionCausalObservation,
)
from qore.infrastructure.core_stack_v2.shared_position_trajectory_memory import (
    SharedPositionJourneyState,
    build_position_trajectory_memory,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedTraderIntelligenceValidationError,
)

T0 = datetime(2026, 9, 30, 16, 30, tzinfo=UTC)


def _obs(
    minute: int,
    *,
    close: int,
    efficiency: int,
    fragility: int,
) -> SharedPositionCausalObservation:
    return SharedPositionCausalObservation(
        observation_id=f"obs-{minute}",
        position_id="position-001",
        asset="NAS100",
        as_of=T0 + timedelta(minutes=minute),
        evidence_cutoff_at=T0 + timedelta(minutes=minute),
        minutes_since_fill=minute,
        progress_bps=6_000,
        signed_close_r_bps=close,
        efficiency_bps=efficiency,
        overlap_bps=2_000,
        signed_body_r_bps=close,
        peer_confirmation_bps=7_000,
        breadth_bps=6_500,
        peer_transition_adverse_bps=2_000,
        world_support_bps=7_000,
        world_fragility_bps=fragility,
        data_integrity_bps=9_900,
        provenance_refs=("source:position-001",),
    )


def test_trajectory_memory_is_deterministic_and_authority_free() -> None:
    observations = (
        _obs(1, close=500, efficiency=500, fragility=2_000),
        _obs(2, close=1_500, efficiency=1_200, fragility=1_500),
        _obs(3, close=2_000, efficiency=1_800, fragility=1_000),
    )
    first = build_position_trajectory_memory(observations)
    second = build_position_trajectory_memory(observations)
    assert first.trajectory_fingerprint == second.trajectory_fingerprint
    assert first.future_market_used is False
    assert first.future_outcome_used is False
    assert first.pnl_used is False
    assert all(point.execution_authority is False for point in first.points)


def test_deterioration_is_a_state_not_exit_command() -> None:
    observations = (
        _obs(1, close=500, efficiency=500, fragility=2_000),
        _obs(2, close=-4_000, efficiency=-3_500, fragility=8_500),
    )
    memory = build_position_trajectory_memory(observations)
    assert memory.points[-1].journey_state in {
        SharedPositionJourneyState.DETERIORATING,
        SharedPositionJourneyState.CONFLICTED,
    }
    assert memory.points[-1].position_management_authority is False


def test_bad_data_becomes_insufficient() -> None:
    bad = replace(_obs(1, close=0, efficiency=0, fragility=2_000), data_integrity_bps=8_000)
    memory = build_position_trajectory_memory((bad,))
    assert memory.points[0].journey_state is SharedPositionJourneyState.INSUFFICIENT


def test_future_or_nonchronological_mix_is_rejected_by_source_contract() -> None:
    first = _obs(2, close=0, efficiency=0, fragility=2_000)
    second = _obs(1, close=0, efficiency=0, fragility=2_000)
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="strictly chronological",
    ):
        build_position_trajectory_memory((first, second))
