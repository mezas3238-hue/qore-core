from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.core_stack_v2.shared_continuation_latent_trajectory_v3 import (
    FEATURE_NAMES,
    assign_latent_trajectory_state,
    fit_latent_trajectory_model,
    trajectory_feature_vector,
)
from qore.infrastructure.core_stack_v2.shared_continuation_positive_tail_intelligence import (
    SharedPositionCausalObservation,
)

T0 = datetime(2026, 9, 30, 7, 40, tzinfo=UTC)


def _obs(
    minute: int,
    *,
    close: int,
    efficiency: int,
    progress: int,
    overlap: int,
    failure_bias: int = 0,
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
        peer_confirmation_bps=max(0, 8_000 - failure_bias),
        breadth_bps=max(0, 8_000 - failure_bias),
        peer_transition_adverse_bps=min(10_000, 2_000 + failure_bias),
        world_support_bps=max(0, 8_000 - failure_bias),
        world_fragility_bps=min(10_000, 2_000 + failure_bias),
        data_integrity_bps=10_000,
        provenance_refs=("source-only",),
    )


def _sequence(seed: int) -> tuple[SharedPositionCausalObservation, ...]:
    return tuple(
        _obs(
            minute=i,
            close=seed * 200 + i * 300,
            efficiency=seed * 150 + i * 250,
            progress=min(10_000, seed * 250 + i * 500),
            overlap=max(0, 7_000 - seed * 300 - i * 350),
            failure_bias=(seed % 3) * 500,
        )
        for i in range(1, 6)
    )


def test_latent_model_fit_is_source_only_and_deterministic() -> None:
    rows = [
        trajectory_feature_vector(_sequence(seed))
        for seed in range(1, 20)
    ]
    first = fit_latent_trajectory_model(rows)
    second = fit_latent_trajectory_model(rows)

    assert first.feature_names == FEATURE_NAMES
    assert first.cluster_count == 6
    assert first.iterations == 25
    assert first.source_only_fit is True
    assert first.productive_authority is False
    assert first.fingerprint() == second.fingerprint()


def test_assignment_has_no_outcome_semantics_or_authority() -> None:
    rows = [
        trajectory_feature_vector(_sequence(seed))
        for seed in range(1, 20)
    ]
    model = fit_latent_trajectory_model(rows)
    state = assign_latent_trajectory_state(_sequence(7), model=model)

    assert state.state_id.startswith("LATENT_TRAJECTORY_STATE_")
    assert state.outcome_semantics_assigned is False
    assert state.mandatory_hold is False
    assert state.position_management_authority is False
    assert state.execution_authority is False
    assert state.sizing_authority is False
    assert len(state.model_fingerprint) == 64
