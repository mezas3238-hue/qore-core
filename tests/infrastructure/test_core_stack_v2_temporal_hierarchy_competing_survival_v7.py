from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.temporal_hierarchy_competing_survival_v7 import (
    RECOVERY_FEATURE_NAMES,
    TERMINAL_FEATURE_NAMES,
    CompetingSurvivalSourceState,
    CompetingSurvivalState,
    CompetingSurvivalTrainingEpisode,
    assess_competing_survival,
    competing_survival_model_fingerprint,
    evaluate_competing_survival,
    fit_competing_survival_model,
)

BASE = datetime(2020, 1, 1, tzinfo=UTC)


def _feature_values(
    names: tuple[str, ...],
    *,
    terminal: bool,
    wobble: float,
) -> tuple[float, ...]:
    values = []
    for index, name in enumerate(names):
        scale = 1.0 + (index % 5) * 0.03
        terminal_like = name in TERMINAL_FEATURE_NAMES and name not in {
            "DISTANCE_NOW",
        }
        if name == "DISTANCE_NOW":
            value = 0.35 if terminal else 1.65
        elif names is TERMINAL_FEATURE_NAMES:
            value = (0.9 if terminal_like and terminal else 0.15) * scale
        else:
            value = (0.15 if terminal else 0.9) * scale
        values.append(value + wobble)
    return tuple(values)


def _episode(
    index: int,
    *,
    terminal: bool,
    evidence_complete: bool = True,
    shift: float = 0.0,
) -> CompetingSurvivalTrainingEpisode:
    wobble = (index % 17 - 8) * 0.004 + shift
    at = BASE + timedelta(minutes=30 * index)
    source = CompetingSurvivalSourceState(
        episode_id=f"v7-{index}",
        as_of=at,
        anchor_direction=1,
        terminal_features=_feature_values(
            TERMINAL_FEATURE_NAMES,
            terminal=terminal,
            wobble=wobble,
        ),
        recovery_features=_feature_values(
            RECOVERY_FEATURE_NAMES,
            terminal=terminal,
            wobble=wobble,
        ),
        evidence_complete=evidence_complete,
    )
    return CompetingSurvivalTrainingEpisode(
        source=source,
        observed_at=at + timedelta(minutes=30),
        terminal_failure=terminal,
    )


def _population(
    count: int,
    *,
    shift: float = 0.0,
) -> tuple[CompetingSurvivalTrainingEpisode, ...]:
    return tuple(
        _episode(
            index,
            terminal=index % 4 == 0,
            shift=shift,
        )
        for index in range(count)
    )


def test_v7_competing_heads_separate_recovery_without_losing_terminals() -> None:
    training = _population(800)
    model = fit_competing_survival_model(
        fitted_at=max(item.observed_at for item in training),
        fit_partition="r8",
        episodes=training,
    )
    evaluation = evaluate_competing_survival(
        model=model,
        partition="r6",
        episodes=_population(480, shift=0.01),
    )

    assert model.calibration_gate_pass is True
    assert model.calibration_terminal_preservation_bps >= 9_800
    assert evaluation.false_declaration_reduction_bps >= 8_000
    assert evaluation.terminal_detection_preservation_bps >= 9_500


def test_v7_runtime_assessment_is_label_independent() -> None:
    training = _population(700)
    model = fit_competing_survival_model(
        fitted_at=max(item.observed_at for item in training),
        fit_partition="r8",
        episodes=training,
    )
    source = _episode(901, terminal=False).source
    assessment = assess_competing_survival(model=model, source=source)

    relabeled = CompetingSurvivalTrainingEpisode(
        source=source,
        observed_at=source.as_of + timedelta(minutes=30),
        terminal_failure=True,
    )
    relabeled_assessment = assess_competing_survival(
        model=model,
        source=relabeled.source,
    )

    assert assessment == relabeled_assessment
    assert assessment.state is CompetingSurvivalState.RECOVERY_SUPPORTED
    assert assessment.structural_failure_declared is False
    assert model.runtime_future_market_used is False
    assert model.outcome_used_at_runtime is False
    assert model.methodology_authority is False
    assert model.sizing_authority is False
    assert model.risk_authority is False
    assert model.order_authority is False
    assert model.execution_authority is False


def test_v7_incomplete_evidence_abstains_and_preserves_baseline() -> None:
    training = _population(700)
    model = fit_competing_survival_model(
        fitted_at=max(item.observed_at for item in training),
        fit_partition="r8",
        episodes=training,
    )
    source = _episode(
        905,
        terminal=False,
        evidence_complete=False,
    ).source
    assessment = assess_competing_survival(model=model, source=source)

    assert assessment.state is CompetingSurvivalState.UNRESOLVED
    assert assessment.structural_failure_declared is True
    assert assessment.mechanism_conflict_micros == 1_000_000


def test_v7_rejects_unidentifiable_anchor_and_forbidden_evidence() -> None:
    base = _episode(20, terminal=True).source

    with pytest.raises(ValueError, match="identifiable anchor"):
        replace(base, anchor_direction=0)

    with pytest.raises(ValueError, match="forbidden evidence"):
        replace(base, pnl_used=True)

    with pytest.raises(ValueError, match="forbidden evidence"):
        replace(base, future_market_used=True)

    with pytest.raises(ValueError, match="forbidden evidence"):
        replace(base, trader_identity_used=True)


def test_v7_rejects_future_fit_evidence() -> None:
    training = _population(300)
    with pytest.raises(ValueError, match="future training evidence"):
        fit_competing_survival_model(
            fitted_at=max(item.observed_at for item in training)
            - timedelta(days=1),
            fit_partition="r8",
            episodes=training,
        )


def test_v7_fit_protocol_is_frozen() -> None:
    training = _population(300)
    fitted_at = max(item.observed_at for item in training)

    with pytest.raises(ValueError, match="fit partition is frozen"):
        fit_competing_survival_model(
            fitted_at=fitted_at,
            fit_partition="r6",
            episodes=training,
        )

    with pytest.raises(ValueError, match="discovery split is frozen"):
        fit_competing_survival_model(
            fitted_at=fitted_at,
            fit_partition="r8",
            episodes=training,
            discovery_fraction_bps=7_500,
        )

    with pytest.raises(ValueError, match="calibration preservation is frozen"):
        fit_competing_survival_model(
            fitted_at=fitted_at,
            fit_partition="r8",
            episodes=training,
            calibration_terminal_preservation_bps=9_700,
        )

    with pytest.raises(ValueError, match="ridge is frozen"):
        fit_competing_survival_model(
            fitted_at=fitted_at,
            fit_partition="r8",
            episodes=training,
            ridge=3.0,
        )


def test_v7_chronological_split_purges_maturing_discovery_labels() -> None:
    training = _population(300)
    model = fit_competing_survival_model(
        fitted_at=max(item.observed_at for item in training),
        fit_partition="r8",
        episodes=training,
    )

    assert model.purged_discovery_count == 1
    assert model.discovery_observed_max < model.calibration_source_min
    assert model.fit_count == 209
    assert model.calibration_count == 90


def test_v7_model_fingerprint_is_deterministic() -> None:
    training = _population(420)
    fitted_at = max(item.observed_at for item in training)
    first = fit_competing_survival_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=training,
    )
    second = fit_competing_survival_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=training,
    )

    assert first == second
    assert competing_survival_model_fingerprint(first) == (
        competing_survival_model_fingerprint(second)
    )
    assert len(competing_survival_model_fingerprint(first)) == 64
