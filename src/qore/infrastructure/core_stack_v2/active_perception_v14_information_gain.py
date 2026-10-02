"""Preregistered scientific primitives for WP-05 V14 peer confirmation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from math import isfinite, log
from statistics import median
from typing import Final

from qore.infrastructure.core_stack_v2.active_perception_v14_observability import (
    V14_CHECKPOINTS_MINUTES,
)
from qore.infrastructure.core_stack_v2.active_perception_v14_peer_acquisition import (
    V14PeerFamily,
)
from qore.infrastructure.core_stack_v2.active_perception_v14_representation import (
    V14_BASE_FEATURES,
)

V14_INFORMATION_GAIN_IDENTITY: Final = (
    "QORE_SHARED_WP05_CROSS_MARKET_MICROSTRUCTURE_CONFIRMATION_V14_001"
)
V14_DISCOVERY_FRACTION_BPS: Final = 7_000
V14_CALIBRATION_TRUE_CONFIRMATION_RETENTION_BPS: Final = 9_800
V14_VALIDATION_TRUE_CONFIRMATION_RETENTION_BPS: Final = 9_800
V14_VALIDATION_ABSOLUTE_TERMINAL_PRESERVATION_BPS: Final = 9_500
V14_POOLED_INCREMENTAL_FALSE_VETO_BPS: Final = 500
V14_VALIDATION_FOLD_COUNT: Final = 4


@dataclass(frozen=True, slots=True)
class V14PeerCheckpointDensity:
    peer: V14PeerFamily
    checkpoint_minutes: int
    feature_names: tuple[str, ...]
    terminal_centers_micros: tuple[int, ...]
    terminal_scales_micros: tuple[int, ...]
    nonterminal_centers_micros: tuple[int, ...]
    nonterminal_scales_micros: tuple[int, ...]
    terminal_count: int
    nonterminal_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.peer, V14PeerFamily):
            raise ValueError("V14 density peer invalid")
        if self.checkpoint_minutes not in V14_CHECKPOINTS_MINUTES:
            raise ValueError("V14 density checkpoint outside frozen schedule")
        if self.feature_names != V14_BASE_FEATURES:
            raise ValueError("V14 density feature schema drift")
        width = len(V14_BASE_FEATURES)
        vectors = (
            self.terminal_centers_micros,
            self.terminal_scales_micros,
            self.nonterminal_centers_micros,
            self.nonterminal_scales_micros,
        )
        if any(len(values) != width for values in vectors):
            raise ValueError("V14 density width mismatch")
        if any(value <= 0 for value in self.terminal_scales_micros):
            raise ValueError("V14 terminal scales must be positive")
        if any(value <= 0 for value in self.nonterminal_scales_micros):
            raise ValueError("V14 nonterminal scales must be positive")
        if self.terminal_count < 10 or self.nonterminal_count < 10:
            raise ValueError("V14 density requires both target classes")


@dataclass(frozen=True, slots=True)
class V14FoldEvaluation:
    fold_index: int
    sample_count: int
    terminal_count: int
    nonterminal_count: int
    baseline_true_confirmation_count: int
    baseline_false_confirmation_count: int
    v14_true_confirmation_count: int
    v14_false_confirmation_count: int
    terminal_confirmation_retention_bps: int
    absolute_terminal_preservation_bps: int
    incremental_false_confirmation_veto_bps: int
    absolute_false_declaration_reduction_bps: int
    gate_pass: bool

    def __post_init__(self) -> None:
        if not 0 <= self.fold_index < V14_VALIDATION_FOLD_COUNT:
            raise ValueError("V14 fold index outside frozen range")
        if self.sample_count != self.terminal_count + self.nonterminal_count:
            raise ValueError("V14 class counts do not sum")
        for name in (
            "terminal_confirmation_retention_bps",
            "absolute_terminal_preservation_bps",
            "incremental_false_confirmation_veto_bps",
            "absolute_false_declaration_reduction_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


def _matrix_row(
    row: Mapping[str, object],
    *,
    peer: V14PeerFamily,
    checkpoint_minutes: int,
) -> tuple[float, ...]:
    if checkpoint_minutes not in V14_CHECKPOINTS_MINUTES:
        raise ValueError("V14 checkpoint outside frozen schedule")
    prefix = f"{peer.value.lower()}_t{checkpoint_minutes}_"
    values: list[float] = []
    for field in V14_BASE_FEATURES:
        raw = row.get(prefix + field)
        if raw is None:
            value = 0.0
        elif type(raw) is int:
            value = float(raw)
        else:
            raise ValueError(f"V14 feature {field} must be int or null")
        if not isfinite(value):
            raise ValueError("V14 model matrix must be finite")
        values.append(value)
    return tuple(values)


def _center_scale(
    rows: tuple[tuple[float, ...], ...],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if not rows:
        raise ValueError("V14 robust density requires rows")
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


def fit_v14_peer_checkpoint_density(
    *,
    peer: V14PeerFamily,
    checkpoint_minutes: int,
    rows: Sequence[Mapping[str, object]],
    labels: Sequence[bool],
) -> V14PeerCheckpointDensity:
    if len(rows) != len(labels) or not rows:
        raise ValueError("V14 rows/labels must be non-empty and aligned")
    matrix = tuple(
        _matrix_row(
            row,
            peer=peer,
            checkpoint_minutes=checkpoint_minutes,
        )
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
        raise ValueError("V14 density requires at least 10 rows per class")
    terminal_center, terminal_scale = _center_scale(terminal)
    nonterminal_center, nonterminal_scale = _center_scale(nonterminal)
    return V14PeerCheckpointDensity(
        peer=peer,
        checkpoint_minutes=checkpoint_minutes,
        feature_names=V14_BASE_FEATURES,
        terminal_centers_micros=_micros(terminal_center),
        terminal_scales_micros=_micros(terminal_scale, positive=True),
        nonterminal_centers_micros=_micros(nonterminal_center),
        nonterminal_scales_micros=_micros(nonterminal_scale, positive=True),
        terminal_count=len(terminal),
        nonterminal_count=len(nonterminal),
    )


def score_v14_peer_checkpoint_micros(
    model: V14PeerCheckpointDensity,
    row: Mapping[str, object],
) -> int:
    values = _matrix_row(
        row,
        peer=model.peer,
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


def peer_confirmation_score_micros(
    *,
    densities: Sequence[V14PeerCheckpointDensity],
    row: Mapping[str, object],
    confirmation_minute: int,
) -> int:
    if confirmation_minute not in V14_CHECKPOINTS_MINUTES[1:]:
        raise ValueError("V14 requires V11 confirmation after t0")
    lookup = {
        (item.peer, item.checkpoint_minutes): item
        for item in densities
    }
    expected_keys = {
        (peer, minute)
        for peer in V14PeerFamily
        for minute in V14_CHECKPOINTS_MINUTES
    }
    if set(lookup) != expected_keys:
        raise ValueError("V14 density set incomplete")
    scores = tuple(
        score_v14_peer_checkpoint_micros(
            lookup[(peer, confirmation_minute)],
            row,
        )
        for peer in V14PeerFamily
    )
    return min(scores)


def select_v14_peer_confirmation_threshold_micros(
    true_confirmation_scores_micros: Sequence[int],
    *,
    minimum_retention_bps: int = (
        V14_CALIBRATION_TRUE_CONFIRMATION_RETENTION_BPS
    ),
) -> tuple[int, int]:
    if not true_confirmation_scores_micros:
        raise ValueError("V14 threshold calibration requires true confirmations")
    if minimum_retention_bps != V14_CALIBRATION_TRUE_CONFIRMATION_RETENTION_BPS:
        raise ValueError("V14 calibration retention gate is frozen at 9800 bps")
    scores = tuple(int(value) for value in true_confirmation_scores_micros)
    candidates = tuple(sorted(set(scores), reverse=True))
    selected = min(scores)
    selected_retention = 10_000
    for threshold in candidates:
        retained = sum(score >= threshold for score in scores)
        retention = retained * 10_000 // len(scores)
        if retention >= minimum_retention_bps:
            selected = threshold
            selected_retention = retention
            break
    return selected, selected_retention


def evaluate_v14_fold(
    *,
    fold_index: int,
    labels: Sequence[bool],
    baseline_confirmation_minutes: Sequence[int | None],
    peer_confirmation_scores_micros: Sequence[int | None],
    peer_confirmation_threshold_micros: int,
) -> V14FoldEvaluation:
    if not (
        len(labels)
        == len(baseline_confirmation_minutes)
        == len(peer_confirmation_scores_micros)
    ) or not labels:
        raise ValueError("V14 fold vectors must be non-empty and aligned")

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
        raise ValueError("V14 fold requires both target classes")
    if baseline_true <= 0 or baseline_false <= 0:
        raise ValueError("V14 fold requires V11 true and false confirmations")

    v14_declared: list[bool] = []
    for minute, score in zip(
        baseline_confirmation_minutes,
        peer_confirmation_scores_micros,
        strict=True,
    ):
        if minute is None:
            if score is not None:
                raise ValueError("V14 score exists without V11 confirmation")
            v14_declared.append(False)
            continue
        if score is None:
            raise ValueError("V14 V11-confirmed episode lacks peer score")
        v14_declared.append(score >= peer_confirmation_threshold_micros)

    v14_true = sum(
        bool(label) and declared
        for label, declared in zip(labels, v14_declared, strict=True)
    )
    v14_false = sum(
        (not bool(label)) and declared
        for label, declared in zip(labels, v14_declared, strict=True)
    )
    retention = v14_true * 10_000 // baseline_true
    absolute_terminal = v14_true * 10_000 // terminal_count
    incremental_false_veto = (
        (baseline_false - v14_false) * 10_000 // baseline_false
    )
    absolute_false_reduction = (
        (nonterminal_count - v14_false) * 10_000 // nonterminal_count
    )
    gate_pass = (
        retention >= V14_VALIDATION_TRUE_CONFIRMATION_RETENTION_BPS
        and absolute_terminal >= V14_VALIDATION_ABSOLUTE_TERMINAL_PRESERVATION_BPS
        and incremental_false_veto > 0
    )
    return V14FoldEvaluation(
        fold_index=fold_index,
        sample_count=len(labels),
        terminal_count=terminal_count,
        nonterminal_count=nonterminal_count,
        baseline_true_confirmation_count=baseline_true,
        baseline_false_confirmation_count=baseline_false,
        v14_true_confirmation_count=v14_true,
        v14_false_confirmation_count=v14_false,
        terminal_confirmation_retention_bps=retention,
        absolute_terminal_preservation_bps=absolute_terminal,
        incremental_false_confirmation_veto_bps=incremental_false_veto,
        absolute_false_declaration_reduction_bps=absolute_false_reduction,
        gate_pass=gate_pass,
    )


def pooled_v14_false_veto_bps(folds: Sequence[V14FoldEvaluation]) -> int:
    if len(folds) != V14_VALIDATION_FOLD_COUNT:
        raise ValueError("V14 requires exactly four validation folds")
    baseline_false = sum(item.baseline_false_confirmation_count for item in folds)
    v14_false = sum(item.v14_false_confirmation_count for item in folds)
    if baseline_false <= 0:
        raise ValueError("V14 pooled baseline false confirmations must be positive")
    return (baseline_false - v14_false) * 10_000 // baseline_false


def v14_density_set_fingerprint(
    densities: Sequence[V14PeerCheckpointDensity],
) -> str:
    ordered = tuple(
        sorted(
            densities,
            key=lambda item: (item.peer.value, item.checkpoint_minutes),
        )
    )
    expected = tuple(
        (peer.value, minute)
        for peer in V14PeerFamily
        for minute in V14_CHECKPOINTS_MINUTES
    )
    actual = tuple((item.peer.value, item.checkpoint_minutes) for item in ordered)
    if actual != expected:
        raise ValueError("V14 density set does not cover exact peer/checkpoint grid")
    return hashlib.sha256(
        json.dumps(
            [asdict(item) for item in ordered],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
