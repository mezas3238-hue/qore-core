from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.hierarchical_world_model import WorldScale
from qore.infrastructure.core_stack_v2.temporal_hierarchy_absorption_v3 import (
    assess_temporal_hierarchy_absorption,
    evaluate_temporal_hierarchy_absorption,
    fit_temporal_hierarchy_absorption_model,
    hierarchy_absorption_signature,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_engine import (
    TemporalHierarchySnapshot,
    TemporalScaleState,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_transition_v2 import (
    TemporalHierarchyTrajectory,
    TemporalHierarchyTrajectoryTrainingEpisode,
)

BASE = datetime(2020, 1, 1, tzinfo=UTC)


def _level(
    scale: WorldScale,
    *,
    direction: int,
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
    episode: str,
    as_of: datetime,
    phase: int,
    terminal: bool,
    jitter: int,
) -> TemporalHierarchySnapshot:
    # Both classes preserve local bearish opposition against a bullish broad
    # anchor. Recoverable paths are absorbed back toward lower scales; terminal
    # paths propagate M5 -> M15 -> H1 while higher resilience deteriorates.
    m1 = -900 + jitter
    m3 = -820 + jitter

    if terminal:
        m5 = -760 + jitter
        m15 = (-300 if phase < 2 else -700) + jitter
        h1 = (650 if phase < 3 else -720) + jitter
        h4 = 420 + jitter
        persistence = 8_400 - phase * 700
        fragility = 2_200 + phase * 1_100
        transition = 2_100 + phase * 1_100
    else:
        m5 = (-700 if phase < 2 else 420) + jitter
        m15 = 380 + jitter
        h1 = 720 + jitter
        h4 = 820 + jitter
        persistence = 8_500 + phase * 100
        fragility = 2_100 - min(phase * 100, 400)
        transition = 2_200 - min(phase * 100, 400)

    return TemporalHierarchySnapshot(
        episode_id=f"{episode}:{phase}",
        as_of=as_of,
        levels=(
            _level(WorldScale.M1, direction=m1),
            _level(WorldScale.M3, direction=m3),
            _level(WorldScale.M5, direction=m5),
            _level(
                WorldScale.M15,
                direction=m15,
                persistence=persistence,
                fragility=fragility,
                transition=transition,
            ),
            _level(
                WorldScale.H1,
                direction=h1,
                persistence=persistence,
                fragility=fragility,
                transition=transition,
            ),
            _level(
                WorldScale.H4,
                direction=h4,
                persistence=persistence + 200,
                fragility=max(0, fragility - 250),
                transition=max(0, transition - 200),
            ),
            _level(
                WorldScale.DAILY,
                direction=900 + jitter,
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
    jitter = (index % 7 - 3) * 5
    offsets = (90, 60, 30, 15, 0)
    snapshots = tuple(
        _snapshot(
            episode=f"{partition}-{index}",
            as_of=end - timedelta(minutes=offset),
            phase=phase,
            terminal=terminal,
            jitter=jitter,
        )
        for phase, offset in enumerate(offsets)
    )
    return TemporalHierarchyTrajectory(
        episode_id=f"{partition}-{index}",
        snapshots=snapshots,
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


def test_v3_signature_distinguishes_absorption_from_upward_propagation() -> None:
    recovered = hierarchy_absorption_signature(
        _trajectory(1, terminal=False, partition="x")
    )
    terminal = hierarchy_absorption_signature(
        _trajectory(2, terminal=True, partition="x")
    )

    assert recovered.current_depth < recovered.maximum_depth
    assert recovered.absorption_count > 0
    assert terminal.current_depth == terminal.maximum_depth
    assert terminal.current_high_breach == 1
    assert terminal.frontier_trend > 0


def test_v3_absorption_model_reduces_false_failures_and_preserves_terminals() -> None:
    training = _episodes(
        partition="r8",
        count=360,
        terminal_every=4,
    )
    model = fit_temporal_hierarchy_absorption_model(
        fitted_at=max(item.observed_at for item in training),
        fit_partition="r8",
        episodes=training,
        minimum_training_recall_bps=9_500,
    )
    evaluation = evaluate_temporal_hierarchy_absorption(
        model=model,
        partition="r6",
        episodes=_episodes(
            partition="r6",
            count=280,
            terminal_every=4,
            day_offset=700,
        ),
    )

    assert evaluation.baseline_false_declaration_count > 0
    assert evaluation.false_declaration_reduction_bps >= 8_000
    assert evaluation.terminal_detection_preservation_bps >= 9_500


def test_v3_runtime_projection_is_source_only_and_authority_free() -> None:
    training = _episodes(partition="r8", count=320, terminal_every=4)
    model = fit_temporal_hierarchy_absorption_model(
        fitted_at=max(item.observed_at for item in training),
        fit_partition="r8",
        episodes=training,
    )
    assessment = assess_temporal_hierarchy_absorption(
        model=model,
        trajectory=_trajectory(900, terminal=False, partition="runtime"),
    )

    assert assessment.baseline_local_opposition is True
    assert assessment.structural_failure_declared is False
    assert assessment.recoverable_pullback is True
    assert assessment.future_market_used is False
    assert assessment.target_used is False
    assert model.target_used_for_training_only is True
    assert model.runtime_future_market_used is False
    assert model.outcome_used_at_runtime is False
    assert model.methodology_authority is False
    assert model.sizing_authority is False
    assert model.risk_authority is False
    assert model.order_authority is False
    assert model.execution_authority is False


def test_v3_model_and_projection_are_deterministic() -> None:
    training = _episodes(partition="r8", count=300, terminal_every=5)
    fitted_at = max(item.observed_at for item in training)
    first = fit_temporal_hierarchy_absorption_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=training,
    )
    second = fit_temporal_hierarchy_absorption_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=training,
    )
    assert first == second

    trajectory = _trajectory(800, terminal=True, partition="runtime")
    assert assess_temporal_hierarchy_absorption(
        model=first,
        trajectory=trajectory,
    ) == assess_temporal_hierarchy_absorption(
        model=second,
        trajectory=trajectory,
    )


def test_v3_rejects_future_fit_evidence() -> None:
    training = _episodes(partition="r8", count=220, terminal_every=4)
    cutoff = max(item.observed_at for item in training) - timedelta(days=10)

    with pytest.raises(ValueError, match="future training evidence"):
        fit_temporal_hierarchy_absorption_model(
            fitted_at=cutoff,
            fit_partition="r8",
            episodes=training,
        )
