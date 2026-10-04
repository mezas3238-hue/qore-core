"""Deterministic walk-forward and Monte Carlo primitives for QORE Shared Lab."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TimeWindow:
    window_id: str
    start_ns: int
    end_ns: int

    def __post_init__(self) -> None:
        if not self.window_id.strip():
            raise ValueError("window identity is required")
        if self.start_ns >= self.end_ns:
            raise ValueError("window start must be before end")


@dataclass(frozen=True, slots=True)
class WalkForwardFold:
    fold_id: str
    development: TimeWindow
    validation: TimeWindow

    @property
    def chronological(self) -> bool:
        return self.development.end_ns <= self.validation.start_ns


@dataclass(frozen=True, slots=True)
class WalkForwardAssessment:
    fold_count: int
    non_overlapping: bool
    chronological: bool
    all_folds_passed: bool
    failed_fold_ids: tuple[str, ...]
    walk_forward_proven: bool


def assess_walk_forward(
    folds: tuple[WalkForwardFold, ...],
    *,
    fold_pass: dict[str, bool],
) -> WalkForwardAssessment:
    if not folds:
        raise ValueError("walk-forward requires folds")
    ids = tuple(fold.fold_id for fold in folds)
    if len(ids) != len(set(ids)):
        raise ValueError("walk-forward fold ids must be unique")
    if set(ids) != set(fold_pass):
        raise ValueError("fold_pass must cover every fold exactly")

    chronological = all(fold.chronological for fold in folds)
    ordered = sorted(
        (
            fold.development.start_ns,
            fold.validation.end_ns,
            fold.fold_id,
        )
        for fold in folds
    )
    non_overlapping = all(
        left[1] <= right[0]
        for left, right in zip(ordered, ordered[1:], strict=False)
    )
    failed = tuple(sorted(fold_id for fold_id, passed in fold_pass.items() if not passed))
    all_passed = not failed
    return WalkForwardAssessment(
        fold_count=len(folds),
        non_overlapping=non_overlapping,
        chronological=chronological,
        all_folds_passed=all_passed,
        failed_fold_ids=failed,
        walk_forward_proven=chronological and non_overlapping and all_passed,
    )


@dataclass(frozen=True, slots=True)
class MonteCarloSummary:
    seed: int
    path_count: int
    trades_per_path: int
    probability_positive: float
    mean_total_r: float
    p95_max_drawdown_r: float
    deterministic_fingerprint_source: tuple[float, ...]


def _max_drawdown(path: tuple[float, ...]) -> float:
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for result in path:
        equity += result
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    return max_drawdown


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("percentile requires values")
    ordered = sorted(values)
    index = math.ceil(quantile * len(ordered)) - 1
    bounded = min(max(index, 0), len(ordered) - 1)
    return ordered[bounded]


def monte_carlo_resample(
    trade_results_r: tuple[float, ...],
    *,
    seed: int,
    path_count: int,
    trades_per_path: int | None = None,
) -> MonteCarloSummary:
    if not trade_results_r:
        raise ValueError("Monte Carlo requires trade results")
    if path_count <= 0:
        raise ValueError("path_count must be positive")
    sample_size = trades_per_path or len(trade_results_r)
    if sample_size <= 0:
        raise ValueError("trades_per_path must be positive")

    rng = random.Random(seed)
    totals: list[float] = []
    drawdowns: list[float] = []
    for _ in range(path_count):
        path = tuple(rng.choice(trade_results_r) for _ in range(sample_size))
        totals.append(sum(path))
        drawdowns.append(_max_drawdown(path))

    positive = sum(total > 0 for total in totals) / path_count
    mean_total = sum(totals) / path_count
    return MonteCarloSummary(
        seed=seed,
        path_count=path_count,
        trades_per_path=sample_size,
        probability_positive=positive,
        mean_total_r=mean_total,
        p95_max_drawdown_r=_percentile(drawdowns, 0.95),
        deterministic_fingerprint_source=trade_results_r,
    )
