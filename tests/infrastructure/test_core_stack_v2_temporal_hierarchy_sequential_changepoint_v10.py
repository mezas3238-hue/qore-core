from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.temporal_hierarchy_competing_survival_v7 import (
    RECOVERY_FEATURE_NAMES,
    TERMINAL_FEATURE_NAMES,
    CompetingSurvivalSourceState,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_sequential_changepoint_v10 import (
    V10_CHECKPOINTS_MINUTES,
    SequentialChangePointTrainingEpisode,
    SequentialCheckpointEvidence,
    build_sequential_checkpoint_evidence,
    evaluate_sequential_changepoint,
    fit_sequential_changepoint_model,
    sequential_changepoint_model_fingerprint,
    sequential_changepoint_representation_fingerprint,
)

BASE = datetime(2020, 1, 1, tzinfo=UTC)


class Bar:
    def __init__(
        self,
        *,
        opened: float = 100.0,
        high: float = 101.0,
        low: float = 99.0,
        close: float = 100.0,
    ) -> None:
        self.opened = opened
        self.high = high
        self.low = low
        self.close = close


def _source(index: int = 0) -> CompetingSurvivalSourceState:
    terminal = {
        name: 0.0
        for name in TERMINAL_FEATURE_NAMES
    }
    recovery = {
        name: 0.0
        for name in RECOVERY_FEATURE_NAMES
    }
    terminal["HIERARCHY_DEPTH"] = 0.5
    terminal["HIGHER_FRAGILITY_MINUS_RESILIENCE"] = 0.2
    recovery["HIGHER_RESILIENCE_MINUS_FRAGILITY"] = -0.2
    return CompetingSurvivalSourceState(
        episode_id=f"v10-source-{index}",
        as_of=BASE + timedelta(minutes=30 * index),
        anchor_direction=1,
        terminal_features=tuple(
            terminal[name] for name in TERMINAL_FEATURE_NAMES
        ),
        recovery_features=tuple(
            recovery[name] for name in RECOVERY_FEATURE_NAMES
        ),
    )


def test_v10_checkpoint_cannot_read_bars_after_checkpoint() -> None:
    source = _source()
    nas = [Bar() for _ in range(50)]
    sp = [Bar() for _ in range(50)]
    us = [Bar() for _ in range(50)]
    source_index = 20

    first = build_sequential_checkpoint_evidence(
        source=source,
        checkpoint_minutes=5,
        as_of=source.as_of + timedelta(minutes=5),
        nas_bars=nas,
        nas_source_index=source_index,
        sp500_bars=sp,
        sp500_source_index=source_index,
        us30_bars=us,
        us30_source_index=source_index,
    )

    nas[source_index + 6] = Bar(
        opened=50.0,
        high=500.0,
        low=1.0,
        close=2.0,
    )
    sp[source_index + 6] = Bar(close=50.0)
    us[source_index + 6] = Bar(close=50.0)

    second = build_sequential_checkpoint_evidence(
        source=source,
        checkpoint_minutes=5,
        as_of=source.as_of + timedelta(minutes=5),
        nas_bars=nas,
        nas_source_index=source_index,
        sp500_bars=sp,
        sp500_source_index=source_index,
        us30_bars=us,
        us30_source_index=source_index,
    )

    assert first == second
    assert first.future_market_used is False
    assert first.target_used is False


def test_v10_checkpoint_responds_to_causal_breach_and_reclaim() -> None:
    source = _source()
    nas = [Bar() for _ in range(50)]
    sp = [Bar() for _ in range(50)]
    us = [Bar() for _ in range(50)]
    source_index = 20

    nas[source_index + 1] = Bar(high=100.0, low=98.0, close=98.5)
    nas[source_index + 2] = Bar(high=100.0, low=98.5, close=99.5)
    nas[source_index + 3] = Bar(high=100.5, low=99.2, close=99.7)
    nas[source_index + 4] = Bar(high=100.8, low=99.3, close=99.8)
    nas[source_index + 5] = Bar(high=101.0, low=99.4, close=100.0)

    evidence = build_sequential_checkpoint_evidence(
        source=source,
        checkpoint_minutes=5,
        as_of=source.as_of + timedelta(minutes=5),
        nas_bars=nas,
        nas_source_index=source_index,
        sp500_bars=sp,
        sp500_source_index=source_index,
        us30_bars=us,
        us30_source_index=source_index,
    )

    assert evidence.breach_observed is True
    assert evidence.safe_reclaim_streak >= 3
    assert evidence.features[0] > 0.0


def _checkpoint(
    *,
    episode_index: int,
    minute: int,
    terminal: bool,
) -> SequentialCheckpointEvidence:
    source_signal = 0.0
    sequential_signal = (
        source_signal
        if minute == 0
        else (0.15 + minute * 0.04 if terminal else -0.10 - minute * 0.02)
    )
    wobble = (episode_index % 13 - 6) * 0.002
    features = tuple(
        sequential_signal + wobble + feature_index * 0.0001
        for feature_index in range(16)
    )
    return SequentialCheckpointEvidence(
        episode_id=f"v9-{episode_index}",
        checkpoint_minutes=minute,
        as_of=BASE
        + timedelta(minutes=30 * episode_index + minute),
        anchor_direction=1,
        features=features,
        breach_observed=minute >= 3,
        safe_reclaim_streak=0 if terminal else (3 if minute >= 10 else 0),
    )


def _episodes(
    count: int,
) -> tuple[SequentialChangePointTrainingEpisode, ...]:
    rows = []
    for index in range(count):
        terminal = index % 3 == 0
        checkpoints = tuple(
            _checkpoint(
                episode_index=index,
                minute=minute,
                terminal=terminal,
            )
            for minute in V10_CHECKPOINTS_MINUTES
        )
        rows.append(
            SequentialChangePointTrainingEpisode(
                checkpoints=checkpoints,
                observed_at=BASE
                + timedelta(minutes=30 * index + 30),
                terminal_failure=terminal,
            )
        )
    return tuple(rows)


def test_v10_sequential_evidence_improves_source_only_discrimination() -> None:
    rows = _episodes(900)
    model = fit_sequential_changepoint_model(
        fitted_at=max(item.observed_at for item in rows),
        fit_partition="r8",
        episodes=rows,
    )
    evaluation = evaluate_sequential_changepoint(
        model=model,
        partition="r8",
        episodes=rows,
    )

    assert model.calibration_gate_pass is True
    assert (
        evaluation.sequential_false_declaration_reduction_bps
        > evaluation.source_only_false_declaration_reduction_bps
    )
    assert evaluation.sequential_terminal_detection_preservation_bps >= 9_500
    assert evaluation.terminal_detection_latency_p95_minutes <= 15


def test_v10_model_and_representation_fingerprints_are_deterministic() -> None:
    rows = _episodes(900)
    fitted_at = max(item.observed_at for item in rows)
    first = fit_sequential_changepoint_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=rows,
    )
    second = fit_sequential_changepoint_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=rows,
    )

    assert first == second
    assert sequential_changepoint_model_fingerprint(first) == (
        sequential_changepoint_model_fingerprint(second)
    )
    assert len(sequential_changepoint_model_fingerprint(first)) == 64
    assert len(sequential_changepoint_representation_fingerprint()) == 64


def test_v10_fit_protocol_is_frozen() -> None:
    rows = _episodes(600)
    fitted_at = max(item.observed_at for item in rows)

    with pytest.raises(ValueError, match="fit partition is frozen"):
        fit_sequential_changepoint_model(
            fitted_at=fitted_at,
            fit_partition="r6",
            episodes=rows,
        )

    with pytest.raises(ValueError, match="discovery split is frozen"):
        fit_sequential_changepoint_model(
            fitted_at=fitted_at,
            fit_partition="r8",
            episodes=rows,
            discovery_fraction_bps=7_500,
        )

    with pytest.raises(ValueError, match="calibration preservation is frozen"):
        fit_sequential_changepoint_model(
            fitted_at=fitted_at,
            fit_partition="r8",
            episodes=rows,
            calibration_terminal_preservation_bps=9_700,
        )
