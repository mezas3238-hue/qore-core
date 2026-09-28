"""Preregistered R8 information-gain primitives for Shared WP-05 V12."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from math import isfinite, log
from statistics import median
from typing import Final, Mapping, Sequence

from qore.infrastructure.core_stack_v2.active_perception_v12_microstructure_representation import (
    v12_microstructure_candidate_fields,
)

INFORMATION_GAIN_IDENTITY: Final = (
    "QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_R8_INFORMATION_GAIN_001"
)
MIN_TERMINAL_CONFIRMATION_RETENTION_BPS: Final = 9_800
MIN_ABSOLUTE_TERMINAL_PRESERVATION_BPS: Final = 9_500
MIN_POOLED_INCREMENTAL_FALSE_VETO_BPS: Final = 500
MICROSTRUCTURE_VETO_THRESHOLD_MICROS: Final = 0
FOLD_COUNT: Final = 4


@dataclass(frozen=True, slots=True)
class V12MicrostructureDensity:
    candidate: str
    feature_names: tuple[str, ...]
    terminal_centers_micros: tuple[int, ...]
    terminal_scales_micros: tuple[int, ...]
    nonterminal_centers_micros: tuple[int, ...]
    nonterminal_scales_micros: tuple[int, ...]
    terminal_count: int
    nonterminal_count: int

    def __post_init__(self) -> None:
        candidates = v12_microstructure_candidate_fields()
        if self.candidate not in candidates:
            raise ValueError("unknown V12 microstructure candidate")
        if self.feature_names != candidates[self.candidate]:
            raise ValueError("V12 candidate feature schema drift")
        width = len(self.feature_names)
        vectors = (
            self.terminal_centers_micros,
            self.terminal_scales_micros,
            self.nonterminal_centers_micros,
            self.nonterminal_scales_micros,
        )
        if any(len(values) != width for values in vectors):
            raise ValueError("V12 density width mismatch")
        if any(value <= 0 for value in self.terminal_scales_micros):
            raise ValueError("V12 terminal scales must be positive")
        if any(value <= 0 for value in self.nonterminal_scales_micros):
            raise ValueError("V12 nonterminal scales must be positive")
        if self.terminal_count < 10 or self.nonterminal_count < 10:
            raise ValueError("V12 density requires both target classes")


@dataclass(frozen=True, slots=True)
class V12InformationGainFold:
    fold_index: int
    sample_count: int
    terminal_count: int
    nonterminal_count: int
    baseline_true_confirmation_count: int
    baseline_false_confirmation_count: int
    v12_true_confirmation_count: int
    v12_false_confirmation_count: int
    terminal_confirmation_retention_bps: int
    absolute_terminal_preservation_bps: int
    incremental_false_confirmation_veto_bps: int
    absolute_false_declaration_reduction_bps: int
    gate_pass: bool

    def __post_init__(self) -> None:
        if not 0 <= self.fold_index < FOLD_COUNT:
            raise ValueError("V12 fold index outside frozen range")
        if self.sample_count != self.terminal_count + self.nonterminal_count:
            raise ValueError("V12 fold class counts do not sum to sample count")
        for name in (
            "terminal_confirmation_retention_bps",
            "absolute_terminal_preservation_bps",
            "incremental_false_confirmation_veto_bps",
            "absolute_false_declaration_reduction_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class V12CandidateInformationGain:
    candidate: str
    folds: tuple[V12InformationGainFold, ...]
    pooled_baseline_false_confirmation_count: int
    pooled_v12_false_confirmation_count: int
    pooled_incremental_false_confirmation_veto_bps: int
    eligible: bool

    def __post_init__(self) -> None:
        if self.candidate not in v12_microstructure_candidate_fields():
            raise ValueError("unknown V12 candidate")
        if len(self.folds) != FOLD_COUNT:
            raise ValueError("V12 candidate requires exactly four validation folds")
        if tuple(item.fold_index for item in self.folds) != tuple(range(FOLD_COUNT)):
            raise ValueError("V12 fold order drift")
        if not 0 <= self.pooled_incremental_false_confirmation_veto_bps <= 10_000:
            raise ValueError("pooled veto bps must be within 0..10000")


def _matrix_row(
    row: Mapping[str, object],
    feature_names: tuple[str, ...],
) -> tuple[float, ...]:
    values: list[float] = []
    for name in feature_names:
        raw = row.get(name)
        if raw is None:
            value = 0.0
        elif type(raw) is int:
            value = float(raw)
        else:
            raise ValueError(f"V12 feature {name} must be int or null")
        if not isfinite(value):
            raise ValueError("V12 model matrix must be finite")
        values.append(value)
    return tuple(values)


def _center_scale(
    rows: tuple[tuple[float, ...], ...],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if not rows:
        raise ValueError("V12 robust density requires rows")
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


def fit_v12_microstructure_density(
    *,
    candidate: str,
    rows: Sequence[Mapping[str, object]],
    labels: Sequence[bool],
) -> V12MicrostructureDensity:
    candidates = v12_microstructure_candidate_fields()
    if candidate not in candidates:
        raise ValueError("unknown V12 microstructure candidate")
    if len(rows) != len(labels) or not rows:
        raise ValueError("V12 rows/labels must be non-empty and aligned")
    feature_names = candidates[candidate]
    matrix = tuple(_matrix_row(row, feature_names) for row in rows)
    terminal = tuple(vector for vector, label in zip(matrix, labels, strict=True) if label)
    nonterminal = tuple(
        vector for vector, label in zip(matrix, labels, strict=True) if not label
    )
    if len(terminal) < 10 or len(nonterminal) < 10:
        raise ValueError("V12 density requires at least 10 rows per class")
    terminal_center, terminal_scale = _center_scale(terminal)
    nonterminal_center, nonterminal_scale = _center_scale(nonterminal)
    return V12MicrostructureDensity(
        candidate=candidate,
        feature_names=feature_names,
        terminal_centers_micros=_micros(terminal_center),
        terminal_scales_micros=_micros(terminal_scale, positive=True),
        nonterminal_centers_micros=_micros(nonterminal_center),
        nonterminal_scales_micros=_micros(nonterminal_scale, positive=True),
        terminal_count=len(terminal),
        nonterminal_count=len(nonterminal),
    )


def score_v12_microstructure_micros(
    model: V12MicrostructureDensity,
    row: Mapping[str, object],
) -> int:
    values = _matrix_row(row, model.feature_names)
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


def evaluate_v12_information_gain_fold(
    *,
    fold_index: int,
    labels: Sequence[bool],
    baseline_declared: Sequence[bool],
    microstructure_scores_micros: Sequence[int],
) -> V12InformationGainFold:
    if not (
        len(labels)
        == len(baseline_declared)
        == len(microstructure_scores_micros)
    ) or not labels:
        raise ValueError("V12 fold vectors must be non-empty and aligned")

    terminal_count = sum(bool(label) for label in labels)
    nonterminal_count = len(labels) - terminal_count
    baseline_true = sum(
        bool(label) and bool(declared)
        for label, declared in zip(labels, baseline_declared, strict=True)
    )
    baseline_false = sum(
        (not bool(label)) and bool(declared)
        for label, declared in zip(labels, baseline_declared, strict=True)
    )
    v12_declared = tuple(
        bool(declared) and score >= MICROSTRUCTURE_VETO_THRESHOLD_MICROS
        for declared, score in zip(
            baseline_declared,
            microstructure_scores_micros,
            strict=True,
        )
    )
    v12_true = sum(
        bool(label) and declared
        for label, declared in zip(labels, v12_declared, strict=True)
    )
    v12_false = sum(
        (not bool(label)) and declared
        for label, declared in zip(labels, v12_declared, strict=True)
    )
    if terminal_count <= 0 or nonterminal_count <= 0:
        raise ValueError("V12 fold requires both target classes")
    if baseline_true <= 0 or baseline_false <= 0:
        raise ValueError("V12 fold requires V11 true and false confirmations")

    retention = v12_true * 10_000 // baseline_true
    absolute_terminal = v12_true * 10_000 // terminal_count
    incremental_veto = (baseline_false - v12_false) * 10_000 // baseline_false
    absolute_false_reduction = (
        (nonterminal_count - v12_false) * 10_000 // nonterminal_count
    )
    gate_pass = (
        retention >= MIN_TERMINAL_CONFIRMATION_RETENTION_BPS
        and absolute_terminal >= MIN_ABSOLUTE_TERMINAL_PRESERVATION_BPS
        and incremental_veto > 0
    )
    return V12InformationGainFold(
        fold_index=fold_index,
        sample_count=len(labels),
        terminal_count=terminal_count,
        nonterminal_count=nonterminal_count,
        baseline_true_confirmation_count=baseline_true,
        baseline_false_confirmation_count=baseline_false,
        v12_true_confirmation_count=v12_true,
        v12_false_confirmation_count=v12_false,
        terminal_confirmation_retention_bps=retention,
        absolute_terminal_preservation_bps=absolute_terminal,
        incremental_false_confirmation_veto_bps=incremental_veto,
        absolute_false_declaration_reduction_bps=absolute_false_reduction,
        gate_pass=gate_pass,
    )


def summarize_v12_candidate_information_gain(
    *,
    candidate: str,
    folds: tuple[V12InformationGainFold, ...],
) -> V12CandidateInformationGain:
    baseline_false = sum(item.baseline_false_confirmation_count for item in folds)
    v12_false = sum(item.v12_false_confirmation_count for item in folds)
    if baseline_false <= 0:
        raise ValueError("V12 pooled baseline false confirmations must be positive")
    pooled_veto = (baseline_false - v12_false) * 10_000 // baseline_false
    eligible = (
        all(item.gate_pass for item in folds)
        and pooled_veto >= MIN_POOLED_INCREMENTAL_FALSE_VETO_BPS
    )
    return V12CandidateInformationGain(
        candidate=candidate,
        folds=folds,
        pooled_baseline_false_confirmation_count=baseline_false,
        pooled_v12_false_confirmation_count=v12_false,
        pooled_incremental_false_confirmation_veto_bps=pooled_veto,
        eligible=eligible,
    )


def select_v12_information_gain_candidate(
    candidates: Sequence[V12CandidateInformationGain],
) -> str | None:
    by_name = {item.candidate: item for item in candidates}
    frozen_order = tuple(v12_microstructure_candidate_fields())
    if set(by_name) != set(frozen_order):
        raise ValueError("V12 candidate result set must contain exact M0-M3 family")
    for name in frozen_order:
        if by_name[name].eligible:
            return name
    return None


def v12_microstructure_density_fingerprint(
    model: V12MicrostructureDensity,
) -> str:
    return hashlib.sha256(
        json.dumps(
            asdict(model),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
