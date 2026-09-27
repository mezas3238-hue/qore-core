from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.temporal_hierarchy_causal_trajectory_v9 import (
    V9_FEATURE_NAMES,
    CausalTrajectorySourceState,
    CausalTrajectoryState,
    CausalTrajectoryTrainingEpisode,
    assess_causal_trajectory,
    build_causal_trajectory_source_state,
    causal_trajectory_model_fingerprint,
    causal_trajectory_representation_fingerprint,
    fit_causal_trajectory_model,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_event_manifold_v8 import (
    EventManifoldLabel,
)

BASE = datetime(2020, 1, 1, tzinfo=UTC)


class Bar:
    def __init__(
        self,
        *,
        opened: float,
        high: float,
        low: float,
        close: float,
    ) -> None:
        self.opened = opened
        self.high = high
        self.low = low
        self.close = close


def _bars(count: int, *, drift: float = 0.03) -> list[Bar]:
    rows: list[Bar] = []
    price = 100.0
    for index in range(count):
        opened = price
        close = opened + drift + ((index % 7) - 3) * 0.005
        rows.append(
            Bar(
                opened=opened,
                high=max(opened, close) + 0.08,
                low=min(opened, close) - 0.08,
                close=close,
            )
        )
        price = close
    return rows


def test_v9_source_is_exactly_60_features_and_future_invariant() -> None:
    nas = _bars(100)
    sp = _bars(100, drift=0.02)
    us = _bars(100, drift=0.01)
    first = build_causal_trajectory_source_state(
        episode_id="v9-source",
        as_of=BASE,
        anchor_direction=1,
        nas_bars=nas,
        nas_index=60,
        sp500_bars=sp,
        sp500_index=60,
        us30_bars=us,
        us30_index=60,
    )

    nas_future_changed = list(nas)
    nas_future_changed[61] = Bar(
        opened=100.0,
        high=500.0,
        low=1.0,
        close=400.0,
    )
    second = build_causal_trajectory_source_state(
        episode_id="v9-source",
        as_of=BASE,
        anchor_direction=1,
        nas_bars=nas_future_changed,
        nas_index=60,
        sp500_bars=sp,
        sp500_index=60,
        us30_bars=us,
        us30_index=60,
    )

    assert len(V9_FEATURE_NAMES) == 60
    assert len(first.features) == 60
    assert first.features == second.features
    assert first.future_market_used is False
    assert first.target_used is False


def test_v9_source_changes_when_past_path_changes() -> None:
    nas = _bars(100)
    sp = _bars(100, drift=0.02)
    us = _bars(100, drift=0.01)
    first = build_causal_trajectory_source_state(
        episode_id="v9-source",
        as_of=BASE,
        anchor_direction=1,
        nas_bars=nas,
        nas_index=60,
        sp500_bars=sp,
        sp500_index=60,
        us30_bars=us,
        us30_index=60,
    )
    changed = list(nas)
    changed[55] = Bar(
        opened=changed[55].opened,
        high=changed[55].high + 1.0,
        low=changed[55].low - 1.0,
        close=changed[55].close - 0.5,
    )
    second = build_causal_trajectory_source_state(
        episode_id="v9-source",
        as_of=BASE,
        anchor_direction=1,
        nas_bars=changed,
        nas_index=60,
        sp500_bars=sp,
        sp500_index=60,
        us30_bars=us,
        us30_index=60,
    )
    assert first.features != second.features


def _source(
    index: int,
    *,
    label: EventManifoldLabel,
    censored_shift: float = -2.0,
    complete: bool = True,
) -> CausalTrajectorySourceState:
    wobble = (index % 13 - 6) * 0.01
    if label is EventManifoldLabel.TERMINAL_EVENT:
        eventness = 2.0
        contrast = -2.0
    elif label is EventManifoldLabel.VERIFIED_RECOVERY_EVENT:
        eventness = 2.0
        contrast = 2.0
    else:
        eventness = censored_shift
        contrast = 0.0
    features = (
        eventness + wobble,
        contrast + wobble,
    ) + tuple(
        wobble + feature_index * 0.0001
        for feature_index in range(58)
    )
    return CausalTrajectorySourceState(
        episode_id=f"v9-{index}",
        as_of=BASE + timedelta(minutes=30 * index),
        anchor_direction=1,
        features=features,
        evidence_complete=complete,
    )


def _episodes(
    count: int,
    *,
    censored_shift: float = -2.0,
) -> tuple[CausalTrajectoryTrainingEpisode, ...]:
    rows: list[CausalTrajectoryTrainingEpisode] = []
    for index in range(count):
        cycle = index % 5
        if cycle == 0:
            label = EventManifoldLabel.TERMINAL_EVENT
        elif cycle in (1, 2):
            label = EventManifoldLabel.VERIFIED_RECOVERY_EVENT
        else:
            label = EventManifoldLabel.CENSORED_UNKNOWN
        source = _source(index, label=label, censored_shift=censored_shift)
        rows.append(
            CausalTrajectoryTrainingEpisode(
                source=source,
                observed_at=source.as_of + timedelta(minutes=30),
                label=label,
            )
        )
    return tuple(rows)


def test_v9_recovery_fit_isolated_from_censored_normalization() -> None:
    first_rows = _episodes(600, censored_shift=-2.0)
    second_rows = _episodes(600, censored_shift=-50.0)
    fitted_at = max(item.observed_at for item in first_rows)

    first = fit_causal_trajectory_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=first_rows,
    )
    second = fit_causal_trajectory_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=second_rows,
    )

    assert first.recovery_centers_micros == second.recovery_centers_micros
    assert first.recovery_scales_micros == second.recovery_scales_micros
    assert first.recovery_coefficients_micros == second.recovery_coefficients_micros
    assert first.recovery_intercept_micros == second.recovery_intercept_micros


def test_v9_incomplete_evidence_abstains_and_has_no_authority() -> None:
    rows = _episodes(600)
    model = fit_causal_trajectory_model(
        fitted_at=max(item.observed_at for item in rows),
        fit_partition="r8",
        episodes=rows,
    )
    source = replace(
        _source(900, label=EventManifoldLabel.VERIFIED_RECOVERY_EVENT),
        evidence_complete=False,
    )
    assessment = assess_causal_trajectory(model=model, source=source)

    assert assessment.state is CausalTrajectoryState.UNRESOLVED
    assert assessment.structural_failure_declared is True
    assert assessment.target_used is False
    assert assessment.future_market_used is False
    assert model.methodology_authority is False
    assert model.sizing_authority is False
    assert model.risk_authority is False
    assert model.order_authority is False
    assert model.execution_authority is False


def test_v9_fit_partition_is_hard_frozen_to_r8() -> None:
    rows = _episodes(300)
    with pytest.raises(ValueError, match="fit partition is frozen to r8"):
        fit_causal_trajectory_model(
            fitted_at=max(item.observed_at for item in rows),
            fit_partition="r6",
            episodes=rows,
        )


def test_v9_fingerprints_are_deterministic() -> None:
    rows = _episodes(600)
    fitted_at = max(item.observed_at for item in rows)
    first = fit_causal_trajectory_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=rows,
    )
    second = fit_causal_trajectory_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=rows,
    )

    assert first == second
    assert causal_trajectory_model_fingerprint(first) == (
        causal_trajectory_model_fingerprint(second)
    )
    assert len(causal_trajectory_model_fingerprint(first)) == 64
    assert len(causal_trajectory_representation_fingerprint()) == 64
