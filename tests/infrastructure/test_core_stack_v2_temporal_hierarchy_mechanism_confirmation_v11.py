from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.temporal_hierarchy_mechanism_confirmation_v11 import (
    V11_CHECKPOINTS_MINUTES,
    V11CognitiveState,
    V11Mechanism,
    assess_v11_episode,
    evaluate_v11_mechanism_confirmation,
    fit_v11_mechanism_confirmation_model,
    v11_model_fingerprint,
    v11_representation_fingerprint,
    _support_at_confirmation,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_sequential_changepoint_v10 import (
    V10_FEATURE_NAMES,
    SequentialChangePointTrainingEpisode,
    SequentialCheckpointEvidence,
)

_BASE = datetime(2020, 1, 1, tzinfo=UTC)


def _features(
    *,
    terminal: bool,
    minute: int,
    episode_index: int,
) -> tuple[float, ...]:
    # t0 is deliberately only weakly separated. From t3 onward all three frozen
    # mechanisms become coherently terminal/non-terminal in this synthetic proof.
    sign = 1.0 if terminal else -1.0
    time_signal = 0.0 if minute == 0 else sign * (0.20 + minute * 0.01)
    wobble = (episode_index % 11 - 5) * 0.002
    values = []
    for index, _name in enumerate(V10_FEATURE_NAMES):
        if index < 10:
            base = time_signal
        elif index < 13:
            base = 0.0 if minute == 0 else sign * 0.22
        else:
            base = sign * 0.12
        values.append(base + wobble + index * 0.0001)
    return tuple(values)


def _episode(
    index: int,
    *,
    terminal: bool,
) -> SequentialChangePointTrainingEpisode:
    source_at = _BASE + timedelta(minutes=30 * index)
    checkpoints = tuple(
        SequentialCheckpointEvidence(
            episode_id=f"v11-{index}",
            checkpoint_minutes=minute,
            as_of=source_at + timedelta(minutes=minute),
            anchor_direction=1,
            features=_features(
                terminal=terminal,
                minute=minute,
                episode_index=index,
            ),
            breach_observed=minute >= 3,
            safe_reclaim_streak=0 if terminal else (3 if minute >= 5 else 0),
        )
        for minute in V11_CHECKPOINTS_MINUTES
    )
    return SequentialChangePointTrainingEpisode(
        checkpoints=checkpoints,
        observed_at=source_at + timedelta(minutes=30),
        terminal_failure=terminal,
    )


def _episodes(count: int = 900) -> tuple[SequentialChangePointTrainingEpisode, ...]:
    return tuple(
        _episode(index, terminal=index % 3 == 0)
        for index in range(count)
    )


def test_v11_frozen_mechanism_groups_are_disjoint() -> None:
    rows = _episodes()
    model = fit_v11_mechanism_confirmation_model(
        fitted_at=max(item.observed_at for item in rows),
        fit_partition="r8",
        episodes=rows,
    )

    groups = {
        name: set(features)
        for name, features in model.mechanism_feature_names
    }
    assert groups[V11Mechanism.FRONTIER_PATH.value].isdisjoint(
        groups[V11Mechanism.CROSS_MARKET.value]
    )
    assert groups[V11Mechanism.FRONTIER_PATH.value].isdisjoint(
        groups[V11Mechanism.SOURCE_HIERARCHY_PRIOR.value]
    )
    assert groups[V11Mechanism.CROSS_MARKET.value].isdisjoint(
        groups[V11Mechanism.SOURCE_HIERARCHY_PRIOR.value]
    )
    assert set().union(*groups.values()) == set(V10_FEATURE_NAMES)


def test_v11_t0_can_watch_but_never_confirm() -> None:
    rows = _episodes()
    model = fit_v11_mechanism_confirmation_model(
        fitted_at=max(item.observed_at for item in rows),
        fit_partition="r8",
        episodes=rows,
    )
    terminal = next(item for item in rows if item.terminal_failure)
    assessed = assess_v11_episode(model=model, episode=terminal)

    assert assessed.checkpoints[0].state is not V11CognitiveState.TERMINAL_CONFIRMED
    assert assessed.first_confirmation_minute is None or (
        assessed.first_confirmation_minute >= 3
    )


def test_v11_confirmation_requires_at_least_two_mechanisms() -> None:
    rows = _episodes()
    model = fit_v11_mechanism_confirmation_model(
        fitted_at=max(item.observed_at for item in rows),
        fit_partition="r8",
        episodes=rows,
    )
    terminal = next(item for item in rows if item.terminal_failure)
    assessed = assess_v11_episode(model=model, episode=terminal)

    assert assessed.first_confirmation_minute is not None
    assert len(assessed.confirmation_support) >= 2


def test_v11_frontier_spike_requires_adjacent_persistence() -> None:
    threshold = 1_000

    support = _support_at_confirmation(
        frontier_previous=500,
        frontier_current=2_000,
        cross_current=2_000,
        hierarchy_source=500,
        threshold=threshold,
    )
    assert V11Mechanism.FRONTIER_PATH not in support
    assert support == (V11Mechanism.CROSS_MARKET,)

    persistent_support = _support_at_confirmation(
        frontier_previous=1_500,
        frontier_current=2_000,
        cross_current=2_000,
        hierarchy_source=500,
        threshold=threshold,
    )
    assert persistent_support == (
        V11Mechanism.FRONTIER_PATH,
        V11Mechanism.CROSS_MARKET,
    )


def test_v11_synthetic_mechanism_confirmation_has_high_discrimination() -> None:
    rows = _episodes()
    model = fit_v11_mechanism_confirmation_model(
        fitted_at=max(item.observed_at for item in rows),
        fit_partition="r8",
        episodes=rows,
    )
    evaluation = evaluate_v11_mechanism_confirmation(
        model=model,
        partition="r8",
        episodes=rows,
    )

    assert model.calibration_gate_pass is True
    assert evaluation.v11_terminal_detection_preservation_bps >= 9_500
    assert evaluation.v11_false_declaration_reduction_bps >= 2_000
    assert evaluation.confirmation_latency_p95_minutes <= 15


def test_v11_model_and_representation_fingerprints_are_deterministic() -> None:
    rows = _episodes()
    fitted_at = max(item.observed_at for item in rows)
    first = fit_v11_mechanism_confirmation_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=rows,
    )
    second = fit_v11_mechanism_confirmation_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=rows,
    )

    assert first == second
    assert v11_model_fingerprint(first) == v11_model_fingerprint(second)
    assert len(v11_model_fingerprint(first)) == 64
    assert len(v11_representation_fingerprint()) == 64


def test_v11_fit_protocol_is_frozen_to_r8() -> None:
    rows = _episodes(600)
    fitted_at = max(item.observed_at for item in rows)

    with pytest.raises(ValueError, match="fit partition is frozen"):
        fit_v11_mechanism_confirmation_model(
            fitted_at=fitted_at,
            fit_partition="r6",
            episodes=rows,
        )

    with pytest.raises(ValueError, match="discovery split is frozen"):
        fit_v11_mechanism_confirmation_model(
            fitted_at=fitted_at,
            fit_partition="r8",
            episodes=rows,
            discovery_fraction_bps=7_500,
        )

    with pytest.raises(ValueError, match="calibration preservation is frozen"):
        fit_v11_mechanism_confirmation_model(
            fitted_at=fitted_at,
            fit_partition="r8",
            episodes=rows,
            calibration_terminal_preservation_bps=9_700,
        )
