"""Burned-only categorical structural calibration for CE2I T02.

One pre-entry categorical state is selected per lineage from training data only.
The final 40% of each already-burned Phase18 lineage is used only to evaluate
that frozen training selection. No 2017H1 data, MAE/MFE, post-entry path state,
or validation-driven threshold search is allowed.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from math import ceil


@dataclass(frozen=True, slots=True)
class T02CategoricalObservation:
    entry_at: datetime
    contexts: tuple[tuple[str, str], ...]
    stopped: bool
    structural_outcome_r: Decimal

    def __post_init__(self) -> None:
        if self.entry_at.tzinfo is None or self.entry_at.utcoffset() is None:
            raise ValueError("T02 categorical timestamp must be timezone-aware")
        if not self.contexts:
            raise ValueError("T02 categorical contexts are required")
        names = tuple(name for name, _ in self.contexts)
        if len(names) != len(set(names)):
            raise ValueError("T02 categorical context names must be unique")
        if any(not name or not value for name, value in self.contexts):
            raise ValueError("T02 categorical contexts must be non-empty")
        if type(self.stopped) is not bool:
            raise ValueError("T02 stopped must be bool")
        if not self.structural_outcome_r.is_finite():
            raise ValueError("T02 structural outcome must be finite")

    def context_value(self, field: str) -> str | None:
        return next(
            (value for name, value in self.contexts if name == field),
            None,
        )


@dataclass(frozen=True, slots=True)
class T02CategoricalCalibrationResult:
    lineage: str
    train_rows: int
    validation_rows: int
    selected_field: str | None
    selected_value: str | None
    training_candidate_rows: int
    validation_candidate_rows: int
    training_baseline_stop_rate: Decimal
    training_candidate_stop_rate: Decimal | None
    validation_baseline_stop_rate: Decimal
    validation_candidate_stop_rate: Decimal | None
    validation_baseline_p95_loss_r: Decimal
    validation_candidate_p95_loss_r: Decimal | None
    minimum_train_support_met: bool
    minimum_validation_support_met: bool
    strict_validation_stop_rate_improvement: bool
    validation_tail_loss_not_worse: bool
    eligible_for_structural_leverage: bool


def calibrate_t02_categorical_structure(
    *,
    lineage: str,
    observations: tuple[T02CategoricalObservation, ...],
    allowed_fields: tuple[str, ...],
    train_fraction: Decimal = Decimal("0.60"),
    minimum_train_rows: int = 15,
    minimum_train_fraction: Decimal = Decimal("0.08"),
    required_train_relative_improvement: Decimal = Decimal("0.10"),
    minimum_validation_rows: int = 20,
) -> T02CategoricalCalibrationResult:
    if not lineage or not observations or not allowed_fields:
        raise ValueError("T02 categorical lineage/observations/fields required")
    if train_fraction <= 0 or train_fraction >= 1:
        raise ValueError("T02 train fraction must be in (0,1)")
    if minimum_train_rows <= 0 or minimum_validation_rows <= 0:
        raise ValueError("T02 support minima must be positive")
    if minimum_train_fraction <= 0 or minimum_train_fraction >= 1:
        raise ValueError("T02 minimum train fraction must be in (0,1)")
    if (
        required_train_relative_improvement <= 0
        or required_train_relative_improvement >= 1
    ):
        raise ValueError("T02 train improvement must be in (0,1)")

    ordered = tuple(sorted(observations, key=lambda item: item.entry_at))
    cut = int(Decimal(len(ordered)) * train_fraction)
    if cut <= 0 or cut >= len(ordered):
        raise ValueError("T02 train/validation split invalid")
    train = ordered[:cut]
    validation = ordered[cut:]
    train_baseline = _stop_rate(train)
    validation_baseline = _stop_rate(validation)

    minimum_support = max(
        minimum_train_rows,
        ceil(float(Decimal(len(train)) * minimum_train_fraction)),
    )
    groups: dict[tuple[str, str], list[T02CategoricalObservation]] = defaultdict(list)
    allowed = set(allowed_fields)
    for row in train:
        for field, value in row.contexts:
            if field in allowed:
                groups[(field, value)].append(row)

    eligible_training: list[
        tuple[Decimal, int, str, str, tuple[T02CategoricalObservation, ...]]
    ] = []
    maximum_train_rate = train_baseline * (
        Decimal(1) - required_train_relative_improvement
    )
    for (field, value), rows in groups.items():
        frozen_rows = tuple(rows)
        if len(frozen_rows) < minimum_support:
            continue
        rate = _stop_rate(frozen_rows)
        if rate <= maximum_train_rate:
            eligible_training.append(
                (rate, -len(frozen_rows), field, value, frozen_rows)
            )
    eligible_training.sort(key=lambda item: item[:4])

    if not eligible_training:
        return T02CategoricalCalibrationResult(
            lineage=lineage,
            train_rows=len(train),
            validation_rows=len(validation),
            selected_field=None,
            selected_value=None,
            training_candidate_rows=0,
            validation_candidate_rows=0,
            training_baseline_stop_rate=train_baseline,
            training_candidate_stop_rate=None,
            validation_baseline_stop_rate=validation_baseline,
            validation_candidate_stop_rate=None,
            validation_baseline_p95_loss_r=_p95_loss_r(validation),
            validation_candidate_p95_loss_r=None,
            minimum_train_support_met=False,
            minimum_validation_support_met=False,
            strict_validation_stop_rate_improvement=False,
            validation_tail_loss_not_worse=False,
            eligible_for_structural_leverage=False,
        )

    train_rate, negative_support, field, value, _ = eligible_training[0]
    candidate_validation = tuple(
        row for row in validation if row.context_value(field) == value
    )
    validation_rate = (
        _stop_rate(candidate_validation)
        if candidate_validation
        else None
    )
    baseline_p95 = _p95_loss_r(validation)
    candidate_p95 = (
        _p95_loss_r(candidate_validation)
        if candidate_validation
        else None
    )
    validation_support_ok = len(candidate_validation) >= minimum_validation_rows
    strict_improvement = (
        validation_rate is not None
        and validation_rate < validation_baseline
    )
    tail_not_worse = (
        candidate_p95 is not None
        and candidate_p95 <= baseline_p95
    )
    return T02CategoricalCalibrationResult(
        lineage=lineage,
        train_rows=len(train),
        validation_rows=len(validation),
        selected_field=field,
        selected_value=value,
        training_candidate_rows=-negative_support,
        validation_candidate_rows=len(candidate_validation),
        training_baseline_stop_rate=train_baseline,
        training_candidate_stop_rate=train_rate,
        validation_baseline_stop_rate=validation_baseline,
        validation_candidate_stop_rate=validation_rate,
        validation_baseline_p95_loss_r=baseline_p95,
        validation_candidate_p95_loss_r=candidate_p95,
        minimum_train_support_met=True,
        minimum_validation_support_met=validation_support_ok,
        strict_validation_stop_rate_improvement=strict_improvement,
        validation_tail_loss_not_worse=tail_not_worse,
        eligible_for_structural_leverage=(
            validation_support_ok
            and strict_improvement
            and tail_not_worse
        ),
    )


def _stop_rate(rows: tuple[T02CategoricalObservation, ...]) -> Decimal:
    if not rows:
        raise ValueError("T02 stop rate requires rows")
    return Decimal(sum(row.stopped for row in rows)) / Decimal(len(rows))


def _p95_loss_r(rows: tuple[T02CategoricalObservation, ...]) -> Decimal:
    losses = sorted(
        abs(row.structural_outcome_r)
        for row in rows
        if row.structural_outcome_r < 0
    )
    if not losses:
        return Decimal(0)
    rank = max(1, ceil(0.95 * len(losses)))
    return losses[rank - 1]
