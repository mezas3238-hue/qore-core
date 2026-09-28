"""Preregistered scientific primitives for WP-05 V13 sequential active perception."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from math import isfinite, log
from statistics import median
from typing import Final

from qore.infrastructure.core_stack_v2.active_perception_v13_sequential_representation import (
    V13_BASE_FEATURES,
    V13_CHECKPOINTS_MINUTES,
)

V13_INFORMATION_GAIN_IDENTITY: Final = (
    "QORE_SHARED_WP05_SEQUENTIAL_ACTIVE_PERCEPTION_V13_001"
)
V13_DISCOVERY_FRACTION_BPS: Final = 7_000
V13_CALIBRATION_TRUE_CONFIRMATION_RETENTION_BPS: Final = 9_800
V13_VALIDATION_TRUE_CONFIRMATION_RETENTION_BPS: Final = 9_800
V13_VALIDATION_ABSOLUTE_TERMINAL_PRESERVATION_BPS: Final = 9_500
V13_POOLED_INCREMENTAL_FALSE_VETO_BPS: Final = 500
V13_VALIDATION_FOLD_COUNT: Final = 4


@dataclass(frozen=True, slots=True)
class V13CheckpointDensity:
    checkpoint_minutes: int
    feature_names: tuple[str, ...]
    terminal_centers_micros: tuple[int, ...]
    terminal_scales_micros: tuple[int, ...]
    nonterminal_centers_micros: tuple[int, ...]
    nonterminal_scales_micros: tuple[int, ...]
    terminal_count: int
    nonterminal_count: int

    def __post_init__(self) -> None:
        if self.checkpoint_minutes not in V13_CHECKPOINTS_MINUTES:
            raise ValueError("V13 density checkpoint outside frozen schedule")
        if self.feature_names != V13_BASE_FEATURES:
            raise ValueError("V13 density feature schema drift")
        width = len(V13_BASE_FEATURES)
        vectors = (
            self.terminal_centers_micros,
            self.terminal_scales_micros,
            self.nonterminal_centers_micros,
            self.nonterminal_scales_micros,
        )
        if any(len(values) != width for values in vectors):
            raise ValueError("V13 checkpoint density width mismatch")
        if any(value <= 0 for value in self.terminal_scales_micros):
            raise ValueError("V13 terminal scales must be positive")
        if any(value <= 0 for value in self.nonterminal_scales_micros):
            raise ValueError("V13 nonterminal scales must be positive")
        if self.terminal_count < 10 or self.nonterminal_count < 10:
            raise ValueError("V13 density requires both target classes")


@dataclass(frozen=True, slots=True)
class V13FoldEvaluation:
    fold_index: int
    sample_count: int
    terminal_count: int
    nonterminal_count: int
    baseline_true_confirmation_count: int
    baseline_false_confirmation_count: int
    v13_true_confirmation_count: int
    v13_false_confirmation_count: int
    terminal_confirmation_retention_bps: int
    absolute_terminal_preservation_bps: int
    incremental_false_confirmation_veto_bps: int
    absolute_false_declaration_reduction_bps: int
    gate_pass: bool

    def __post_init__(self) -> None:
        if not 0 <= self.fold_index < V13_VALIDATION_FOLD_COUNT:
            raise ValueError("V13 fold index outside frozen range")
        if self.sample_count != self.terminal_count + self.nonterminal_count:
            raise ValueError("V13 class counts do not sum to sample count")
        for name in (
            "terminal_confirmation_retention_bps",
            "absolute_terminal_preservation_bps",
            "incremental_false_confirmation_veto_bps",
            "absolute_false_declaration_reduction_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


def _checkpoint_matrix_row(
    row: Mapping[str, object],
    *,
    checkpoint_minutes: int,
) -> tuple[float, ...]:
    if checkpoint_minutes not in V13_CHECKPOINTS_MINUTES:
        raise ValueError("V13 checkpoint outside frozen schedule")
    values: list[float] = []
    for field in V13_BASE_FEATURES:
        raw = row.get(f"t{checkpoint_minutes}_{field}")
        if raw is None:
            value = 0.0
        elif type(raw) is int:
            value = float(raw)
        else:
            raise ValueError(f"V13 feature {field} must be int or null")
        if not isfinite(value):
            raise ValueError("V13 model matrix must be finite")
        values.append(value)
    return tuple(values)


def _center_scale(
    rows: tuple[tuple[float, ...], ...],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if not rows:
        raise ValueError("V13 robust density requires rows")
    width = len(rows[0])
    centers = tuple(median(row[index] for row in rows) for index in range(width))
    scales: list[float] = []
    for index, center in enumerate(centers):
        mad = median(abs(row[index] - center) for row in rows)
        scales.append(max(1e-4, mad * 1.4826))
    return centers, tuple(scales)


def _micros(
    values: tuple[float, ...],
    *,
    positive: bool = False,
) -> tuple[int, ...]:
    if positive:
        return tuple(max(1, int(round(value * 1_000_000))) for value in values)
    return tuple(int(round(value * 1_000_000)) for value in values)


def fit_v13_checkpoint_density(
    *,
    checkpoint_minutes: int,
    rows: Sequence[Mapping[str, object]],
    labels: Sequence[bool],
) -> V13CheckpointDensity:
    if len(rows) != len(labels) or not rows:
        raise ValueError("V13 rows/labels must be non-empty and aligned")
    matrix = tuple(
        _checkpoint_matrix_row(row, checkpoint_minutes=checkpoint_minutes)
        for row in rows
    )
    terminal = tuple(
        vector
        for vector, label in zip(matrix, labels, strict=True)
        if bool(label)
    )
    nonterminal = tuple(
        vector
        for vector, label in zip(matrix, labels, strict=True)
        if not bool(label)
    )
    if len(terminal) < 10 or len(nonterminal) < 10:
        raise ValueError("V13 checkpoint density requires at least 10 rows per class")
    terminal_center, terminal_scale = _center_scale(terminal)
    nonterminal_center, nonterminal_scale = _center_scale(nonterminal)
    return V13CheckpointDensity(
        checkpoint_minutes=checkpoint_minutes,
        feature_names=V13_BASE_FEATURES,
        terminal_centers_micros=_micros(terminal_center),
        terminal_scales_micros=_micros(terminal_scale, positive=True),
        nonterminal_centers_micros=_micros(nonterminal_center),
        nonterminal_scales_micros=_micros(nonterminal_scale, positive=True),
        terminal_count=len(terminal),
        nonterminal_count=len(nonterminal),
    )


def score_v13_checkpoint_micros(
    model: V13CheckpointDensity,
    row: Mapping[str, object],
) -> int:
    values = _checkpoint_matrix_row(
        row,
        checkpoint_minutes=model.checkpoint_minutes,
    )
    total = 0.0
    for value, tc, ts, nc, ns in zip(
        values,
        model.terminal_centers_micros,
        model.terminal_scales_micros,
        model.nonterminal_centers_micros,
        model.nonterminal_scales_micros,
        strict=True,
    ):
        terminal_center = tc / 1_000_000.0
        terminal_scale = ts / 1_000_000.0
        nonterminal_center = nc / 1_000_000.0
        nonterminal_scale = ns / 1_000_000.0
        terminal_log = -log(terminal_scale) - 0.5 * (
            (value - terminal_center) / terminal_scale
        ) ** 2
        nonterminal_log = -log(nonterminal_scale) - 0.5 * (
            (value - nonterminal_center) / nonterminal_scale
        ) ** 2
        total += max(-20.0, min(20.0, terminal_log - nonterminal_log))
    return int(round(total / len(values) * 1_000_000))


def persistent_recovery_score_micros(
    *,
    checkpoint_scores_micros: Mapping[int, int],
    confirmation_minute: int,
) -> int:
    if confirmation_minute not in V13_CHECKPOINTS_MINUTES[1:]:
        raise ValueError("V13 requires V11 confirmation after t0")
    scheduled = tuple(
        minute
        for minute in V13_CHECKPOINTS_MINUTES
        if minute <= confirmation_minute
    )
    if len(scheduled) < 2:
        raise ValueError("V13 persistent recovery requires adjacent checkpoints")
    if any(minute not in checkpoint_scores_micros for minute in scheduled):
        raise ValueError("V13 checkpoint score set is incomplete")
    pair_scores = tuple(
        max(
            checkpoint_scores_micros[left],
            checkpoint_scores_micros[right],
        )
        for left, right in zip(scheduled, scheduled[1:])
    )
    return min(pair_scores)


def select_v13_recovery_veto_threshold_micros(
    true_confirmation_scores_micros: Sequence[int],
    *,
    minimum_retention_bps: int = (
        V13_CALIBRATION_TRUE_CONFIRMATION_RETENTION_BPS
    ),
) -> tuple[int, int]:
    if not true_confirmation_scores_micros:
        raise ValueError("V13 threshold calibration requires true confirmations")
    if minimum_retention_bps != V13_CALIBRATION_TRUE_CONFIRMATION_RETENTION_BPS:
        raise ValueError("V13 calibration retention gate is frozen at 9800 bps")
    scores = tuple(int(value) for value in true_confirmation_scores_micros)
    candidates = tuple(sorted(set((min(scores) - 1, *scores))))
    selected = candidates[0]
    selected_retention = 10_000
    for threshold in candidates:
        retained = sum(score > threshold for score in scores)
        retention = retained * 10_000 // len(scores)
        if retention >= minimum_retention_bps:
            selected = threshold
            selected_retention = retention
        else:
            break
    return selected, selected_retention


def evaluate_v13_fold(
    *,
    fold_index: int,
    labels: Sequence[bool],
    baseline_confirmation_minutes: Sequence[int | None],
    persistent_recovery_scores_micros: Sequence[int | None],
    recovery_veto_threshold_micros: int,
) -> V13FoldEvaluation:
    if not (
        len(labels)
        == len(baseline_confirmation_minutes)
        == len(persistent_recovery_scores_micros)
    ) or not labels:
        raise ValueError("V13 fold vectors must be non-empty and aligned")

    terminal_count = sum(bool(label) for label in labels)
    nonterminal_count = len(labels) - terminal_count
    baseline_declared = tuple(
        minute is not None for minute in baseline_confirmation_minutes
    )
    baseline_true = sum(
        bool(label) and declared
        for label, declared in zip(labels, baseline_declared, strict=True)
    )
    baseline_false = sum(
        (not bool(label)) and declared
        for label, declared in zip(labels, baseline_declared, strict=True)
    )
    if terminal_count <= 0 or nonterminal_count <= 0:
        raise ValueError("V13 fold requires both target classes")
    if baseline_true <= 0 or baseline_false <= 0:
        raise ValueError("V13 fold requires V11 true and false confirmations")

    v13_declared: list[bool] = []
    for minute, score in zip(
        baseline_confirmation_minutes,
        persistent_recovery_scores_micros,
        strict=True,
    ):
        if minute is None:
            if score is not None:
                raise ValueError("V13 score exists without V11 confirmation")
            v13_declared.append(False)
            continue
        if score is None:
            raise ValueError("V13 confirmed episode lacks persistent recovery score")
        v13_declared.append(score > recovery_veto_threshold_micros)

    v13_true = sum(
        bool(label) and declared
        for label, declared in zip(labels, v13_declared, strict=True)
    )
    v13_false = sum(
        (not bool(label)) and declared
        for label, declared in zip(labels, v13_declared, strict=True)
    )
    retention = v13_true * 10_000 // baseline_true
    absolute_terminal = v13_true * 10_000 // terminal_count
    incremental_false_veto = (
        (baseline_false - v13_false) * 10_000 // baseline_false
    )
    absolute_false_reduction = (
        (nonterminal_count - v13_false) * 10_000 // nonterminal_count
    )
    gate_pass = (
        retention >= V13_VALIDATION_TRUE_CONFIRMATION_RETENTION_BPS
        and absolute_terminal
        >= V13_VALIDATION_ABSOLUTE_TERMINAL_PRESERVATION_BPS
        and incremental_false_veto > 0
    )
    return V13FoldEvaluation(
        fold_index=fold_index,
        sample_count=len(labels),
        terminal_count=terminal_count,
        nonterminal_count=nonterminal_count,
        baseline_true_confirmation_count=baseline_true,
        baseline_false_confirmation_count=baseline_false,
        v13_true_confirmation_count=v13_true,
        v13_false_confirmation_count=v13_false,
        terminal_confirmation_retention_bps=retention,
        absolute_terminal_preservation_bps=absolute_terminal,
        incremental_false_confirmation_veto_bps=incremental_false_veto,
        absolute_false_declaration_reduction_bps=absolute_false_reduction,
        gate_pass=gate_pass,
    )


def pooled_v13_false_veto_bps(folds: Sequence[V13FoldEvaluation]) -> int:
    if len(folds) != V13_VALIDATION_FOLD_COUNT:
        raise ValueError("V13 requires exactly four validation folds")
    baseline_false = sum(item.baseline_false_confirmation_count for item in folds)
    v13_false = sum(item.v13_false_confirmation_count for item in folds)
    if baseline_false <= 0:
        raise ValueError("V13 pooled baseline false confirmations must be positive")
    return (baseline_false - v13_false) * 10_000 // baseline_false


def v13_density_set_fingerprint(
    densities: Sequence[V13CheckpointDensity],
) -> str:
    ordered = tuple(
        sorted(densities, key=lambda item: item.checkpoint_minutes)
    )
    if tuple(item.checkpoint_minutes for item in ordered) != V13_CHECKPOINTS_MINUTES:
        raise ValueError("V13 density set does not cover exact checkpoints")
    payload = [asdict(item) for item in ordered]
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
