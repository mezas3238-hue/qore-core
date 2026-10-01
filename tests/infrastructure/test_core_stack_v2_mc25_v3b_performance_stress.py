from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np

from qore.infrastructure.core_stack_v2.mc25_v3b_performance_stress import (
    FROZEN_STRESS_SCENARIOS,
    V3BStressKind,
    apply_v3b_performance_stress,
    summarize_v3b_stress_evaluations,
)
from qore.infrastructure.core_stack_v2.representation_predictive_nonlinear_probe_v3b import (
    PredictiveSecondOrderEvaluation,
    PreparedSecondOrderDesign,
)


def _prepared(rows: int = 100) -> PreparedSecondOrderDesign:
    baseline = np.arange(rows * 3, dtype=np.float64).reshape(rows, 3)
    augmented = np.hstack(
        (
            baseline,
            np.ones((rows, 2), dtype=np.float64),
        )
    )
    baseline.setflags(write=False)
    augmented.setflags(write=False)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return PreparedSecondOrderDesign(
        partitions=("stress",),
        episode_ids=tuple(f"episode-{i:04d}" for i in range(rows)),
        as_of=tuple(start + timedelta(minutes=i) for i in range(rows)),
        baseline=baseline,
        augmented=augmented,
    )


def test_frozen_scenario_ids_are_unique() -> None:
    ids = [item.scenario_id for item in FROZEN_STRESS_SCENARIOS]
    assert len(ids) == 6
    assert len(set(ids)) == 6


def test_hash_row_drop_is_deterministic_and_target_blind() -> None:
    prepared = _prepared()
    scenario = next(
        item
        for item in FROZEN_STRESS_SCENARIOS
        if item.kind is V3BStressKind.HASH_ROW_DROP
        and item.drop_bps == 1_000
    )
    first = apply_v3b_performance_stress(prepared, scenario)
    second = apply_v3b_performance_stress(prepared, scenario)
    assert first.episode_ids == second.episode_ids
    assert 75 <= len(first.episode_ids) < 100
    assert np.array_equal(first.baseline, second.baseline)


def test_latent_attenuation_preserves_baseline_design() -> None:
    prepared = _prepared()
    scenario = next(
        item
        for item in FROZEN_STRESS_SCENARIOS
        if item.kind is V3BStressKind.LATENT_ATTENUATION
    )
    stressed = apply_v3b_performance_stress(prepared, scenario)
    assert np.array_equal(stressed.baseline, prepared.baseline)
    assert np.array_equal(
        stressed.augmented[:, : prepared.baseline.shape[1]],
        prepared.augmented[:, : prepared.baseline.shape[1]],
    )
    assert np.allclose(
        stressed.augmented[:, prepared.baseline.shape[1] :],
        prepared.augmented[:, prepared.baseline.shape[1] :] * 0.9,
    )


def test_contiguous_drop_removes_one_time_block() -> None:
    prepared = _prepared()
    scenario = next(
        item
        for item in FROZEN_STRESS_SCENARIOS
        if item.kind is V3BStressKind.CONTIGUOUS_TIME_DROP
    )
    stressed = apply_v3b_performance_stress(prepared, scenario)
    assert len(stressed.episode_ids) == 90
    missing = [
        item
        for item in prepared.episode_ids
        if item not in set(stressed.episode_ids)
    ]
    assert missing == list(prepared.episode_ids[45:55])


def _evaluation(
    target: str,
    *,
    baseline_mse: int,
    augmented_mse: int,
    incremental_bps: int,
) -> PredictiveSecondOrderEvaluation:
    return PredictiveSecondOrderEvaluation(
        partition="stress",
        target_name=target,
        sample_count=100,
        baseline_mse_micros=baseline_mse,
        augmented_mse_micros=augmented_mse,
        incremental_information_bps=incremental_bps,
        probe_fingerprint="a" * 64,
    )


def test_stress_summary_preserves_original_conjunctive_gate() -> None:
    passing = [
        _evaluation(
            f"T{i}",
            baseline_mse=1_000_000,
            augmented_mse=970_000 if i < 4 else 1_000_000,
            incremental_bps=300 if i < 4 else 0,
        )
        for i in range(8)
    ]
    summary = summarize_v3b_stress_evaluations(passing)
    assert summary["pooled_incremental_information_bps"] == 150
    assert summary["positive_target_count"] == 4
    assert summary["pass"] is True

    too_few_positive = [
        _evaluation(
            f"P{i}",
            baseline_mse=1_000_000,
            augmented_mse=940_000 if i < 3 else 1_000_000,
            incremental_bps=600 if i < 3 else 0,
        )
        for i in range(8)
    ]
    summary = summarize_v3b_stress_evaluations(too_few_positive)
    assert summary["pooled_incremental_information_bps"] > 100
    assert summary["positive_target_count"] == 3
    assert summary["pass"] is False

    insufficient_pooled = [
        _evaluation(
            f"I{i}",
            baseline_mse=1_000_000,
            augmented_mse=990_000 if i < 4 else 1_010_000,
            incremental_bps=100 if i < 4 else -100,
        )
        for i in range(8)
    ]
    summary = summarize_v3b_stress_evaluations(insufficient_pooled)
    assert summary["positive_target_count"] == 4
    assert summary["pooled_incremental_information_bps"] == 0
    assert summary["pass"] is False
