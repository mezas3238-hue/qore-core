from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.hierarchical_world_model import WorldScale
from qore.infrastructure.core_stack_v2.temporal_hierarchy_engine import (
    TemporalHierarchySnapshot,
    TemporalScaleState,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_recovery_veto_v4 import (
    assess_temporal_hierarchy_recovery_veto,
    evaluate_temporal_hierarchy_recovery_veto,
    fit_temporal_hierarchy_recovery_veto_model,
    recovery_motif_signature,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_transition_v2 import (
    TemporalHierarchyTrajectory,
    TemporalHierarchyTrajectoryTrainingEpisode,
)

BASE = datetime(2020, 1, 1, tzinfo=UTC)


def _level(
    scale: WorldScale,
    direction: int,
    *,
    persistence: int = 8_000,
    coherence: int = 7_500,
    fragility: int = 2_000,
    transition: int = 2_000,
) -> TemporalScaleState:
    return TemporalScaleState(
        scale=scale,
        direction_milli=direction,
        persistence_bps=persistence,
        coherence_bps=coherence,
        efficiency_bps=7_000,
        fragility_bps=fragility,
        transition_bps=transition,
    )


def _snapshot(
    *,
    at: datetime,
    episode: str,
    phase: int,
    terminal: bool,
    jitter: int,
) -> TemporalHierarchySnapshot:
    if terminal:
        # Adversity penetrates and remains at H1/H4.
        m5 = -750 + jitter
        m15 = -250 - phase * 120 + jitter
        h1 = 700 - phase * 320 + jitter
        h4 = 850 - phase * 220 + jitter
        fragility = 2_500 + phase * 900
        transition = 2_500 + phase * 900
        persistence = 8_500 - phase * 800
    else:
        # Same local opposition initially, then front recedes below M15 while
        # broad structure retains resilience.
        m5 = (-750 if phase < 2 else 350) + jitter
        m15 = (-300 if phase < 2 else 450) + jitter
        h1 = 760 + jitter
        h4 = 860 + jitter
        fragility = 2_100
        transition = 2_200
        persistence = 8_600

    return TemporalHierarchySnapshot(
        episode_id=f"{episode}:{phase}",
        as_of=at,
        levels=(
            _level(WorldScale.M1, -900 + jitter),
            _level(WorldScale.M3, -840 + jitter),
            _level(WorldScale.M5, m5),
            _level(
                WorldScale.M15,
                m15,
                persistence=persistence,
                fragility=fragility,
                transition=transition,
            ),
            _level(
                WorldScale.H1,
                h1,
                persistence=persistence,
                fragility=fragility,
                transition=transition,
            ),
            _level(
                WorldScale.H4,
                h4,
                persistence=persistence + 200,
                fragility=max(0, fragility - 200),
                transition=max(0, transition - 200),
            ),
            _level(
                WorldScale.DAILY,
                900 + jitter,
                persistence=9_000,
                coherence=8_400,
                fragility=1_500,
                transition=1_700,
            ),
        ),
    )


def _trajectory(
    index: int,
    *,
    terminal: bool,
    partition: str,
    day_offset: int = 0,
) -> TemporalHierarchyTrajectory:
    end = BASE + timedelta(days=day_offset + index)
    offsets = (90, 60, 30, 15, 0)
    jitter = (index % 9 - 4) * 5
    return TemporalHierarchyTrajectory(
        episode_id=f"{partition}-{index}",
        snapshots=tuple(
            _snapshot(
                at=end - timedelta(minutes=offset),
                episode=f"{partition}-{index}",
                phase=phase,
                terminal=terminal,
                jitter=jitter,
            )
            for phase, offset in enumerate(offsets)
        ),
    )


def _episodes(
    *,
    partition: str,
    count: int,
    terminal_every: int,
    day_offset: int = 0,
) -> tuple[TemporalHierarchyTrajectoryTrainingEpisode, ...]:
    rows = []
    for index in range(count):
        terminal = index % terminal_every == 0
        trajectory = _trajectory(
            index,
            terminal=terminal,
            partition=partition,
            day_offset=day_offset,
        )
        rows.append(
            TemporalHierarchyTrajectoryTrainingEpisode(
                trajectory=trajectory,
                observed_at=trajectory.snapshots[-1].as_of
                + timedelta(minutes=30),
                terminal_failure=terminal,
            )
        )
    return tuple(rows)


def test_v4_signature_preserves_path_shape() -> None:
    recovery = recovery_motif_signature(
        _trajectory(1, terminal=False, partition="x")
    )
    terminal = recovery_motif_signature(
        _trajectory(2, terminal=True, partition="x")
    )
    assert recovery.current_below_max == 1
    assert recovery.recession_count > 0
    assert terminal.current_high_breach == 1
    assert terminal.high_breach_count > recovery.high_breach_count


def test_v4_recovery_veto_is_terminal_safe_on_shifted_partition() -> None:
    training = _episodes(
        partition="r8",
        count=500,
        terminal_every=4,
    )
    model = fit_temporal_hierarchy_recovery_veto_model(
        fitted_at=max(item.observed_at for item in training),
        fit_partition="r8",
        episodes=training,
    )
    evaluation = evaluate_temporal_hierarchy_recovery_veto(
        model=model,
        partition="r6",
        episodes=_episodes(
            partition="r6",
            count=360,
            terminal_every=4,
            day_offset=800,
        ),
    )
    assert model.calibration_terminal_preservation_bps >= 9_700
    assert evaluation.false_declaration_reduction_bps >= 8_000
    assert evaluation.terminal_detection_preservation_bps >= 9_500


def test_v4_runtime_defaults_to_failure_unless_recovery_is_proven() -> None:
    training = _episodes(partition="r8", count=420, terminal_every=4)
    model = fit_temporal_hierarchy_recovery_veto_model(
        fitted_at=max(item.observed_at for item in training),
        fit_partition="r8",
        episodes=training,
    )
    recovered = assess_temporal_hierarchy_recovery_veto(
        model=model,
        trajectory=_trajectory(900, terminal=False, partition="runtime"),
    )
    terminal = assess_temporal_hierarchy_recovery_veto(
        model=model,
        trajectory=_trajectory(901, terminal=True, partition="runtime"),
    )
    assert recovered.recovery_veto is True
    assert recovered.structural_failure_declared is False
    assert terminal.recovery_veto is False
    assert terminal.structural_failure_declared is True
    assert model.runtime_future_market_used is False
    assert model.outcome_used_at_runtime is False
    assert model.methodology_authority is False
    assert model.sizing_authority is False
    assert model.risk_authority is False
    assert model.order_authority is False
    assert model.execution_authority is False


def test_v4_rejects_future_fit_evidence() -> None:
    training = _episodes(partition="r8", count=260, terminal_every=4)
    cutoff = max(item.observed_at for item in training) - timedelta(days=20)
    with pytest.raises(ValueError, match="future training evidence"):
        fit_temporal_hierarchy_recovery_veto_model(
            fitted_at=cutoff,
            fit_partition="r8",
            episodes=training,
        )
