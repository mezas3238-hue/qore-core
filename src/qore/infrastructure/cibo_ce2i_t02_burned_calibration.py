"""Burned-only structural-precision calibration probe for CE2I T02.

The probe uses only already-consumed Phase18 trade geometry. It fits one simple
structural precision threshold on the first 60% of each lineage and evaluates
it on the final 40% of that same burned interval. It is a falsification probe,
not a search loop: no alternative threshold is selected from validation results.

2017H1 is not read or referenced as an outcome source.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from math import ceil
from statistics import median

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


@dataclass(frozen=True, slots=True)
class T02StructuralObservation:
    entry_at: datetime
    stop_to_target_ratio: Decimal
    stopped: bool
    structural_outcome_r: Decimal

    def __post_init__(self) -> None:
        if self.entry_at.tzinfo is None or self.entry_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "T02 observation timestamp must be timezone-aware"
            )
        if (
            not self.stop_to_target_ratio.is_finite()
            or self.stop_to_target_ratio <= 0
        ):
            raise CiboCapitalManagementError(
                "T02 stop/target ratio must be finite positive"
            )
        if not self.structural_outcome_r.is_finite():
            raise CiboCapitalManagementError(
                "T02 structural outcome must be finite"
            )
        if type(self.stopped) is not bool:
            raise CiboCapitalManagementError("T02 stopped must be bool")


@dataclass(frozen=True, slots=True)
class T02StructuralCalibrationResult:
    lineage: str
    train_rows: int
    validation_rows: int
    train_threshold_stop_to_target: Decimal
    validation_candidate_rows: int
    baseline_stop_rate: Decimal
    candidate_stop_rate: Decimal
    baseline_p95_loss_r: Decimal
    candidate_p95_loss_r: Decimal
    strict_stop_rate_improvement: bool
    tail_loss_not_worse: bool
    minimum_validation_sample_met: bool
    eligible_for_structural_leverage: bool


def calibrate_t02_structural_precision(
    *,
    lineage: str,
    observations: tuple[T02StructuralObservation, ...],
    train_fraction: Decimal = Decimal("0.60"),
    minimum_validation_candidate_rows: int = 30,
) -> T02StructuralCalibrationResult:
    if not lineage:
        raise CiboCapitalManagementError("T02 lineage is required")
    if len(observations) < 2:
        raise CiboCapitalManagementError(
            "T02 calibration requires at least two observations"
        )
    if train_fraction <= 0 or train_fraction >= 1:
        raise CiboCapitalManagementError(
            "T02 train fraction must be strictly between zero and one"
        )
    if minimum_validation_candidate_rows <= 0:
        raise CiboCapitalManagementError(
            "T02 minimum validation sample must be positive"
        )

    ordered = tuple(sorted(observations, key=lambda item: item.entry_at))
    cut = int(Decimal(len(ordered)) * train_fraction)
    if cut <= 0 or cut >= len(ordered):
        raise CiboCapitalManagementError("T02 train/validation split invalid")
    train = ordered[:cut]
    validation = ordered[cut:]

    threshold = Decimal(
        str(median([float(item.stop_to_target_ratio) for item in train]))
    )
    candidate = tuple(
        item
        for item in validation
        if item.stop_to_target_ratio <= threshold
    )
    baseline_stop_rate = _stop_rate(validation)
    candidate_stop_rate = (
        _stop_rate(candidate)
        if candidate
        else Decimal(1)
    )
    baseline_p95 = _p95_loss_r(validation)
    candidate_p95 = (
        _p95_loss_r(candidate)
        if candidate
        else Decimal("Infinity")
    )
    strict_improvement = candidate_stop_rate < baseline_stop_rate
    tail_not_worse = candidate_p95 <= baseline_p95
    sample_ok = len(candidate) >= minimum_validation_candidate_rows

    return T02StructuralCalibrationResult(
        lineage=lineage,
        train_rows=len(train),
        validation_rows=len(validation),
        train_threshold_stop_to_target=threshold,
        validation_candidate_rows=len(candidate),
        baseline_stop_rate=baseline_stop_rate,
        candidate_stop_rate=candidate_stop_rate,
        baseline_p95_loss_r=baseline_p95,
        candidate_p95_loss_r=candidate_p95,
        strict_stop_rate_improvement=strict_improvement,
        tail_loss_not_worse=tail_not_worse,
        minimum_validation_sample_met=sample_ok,
        eligible_for_structural_leverage=(
            strict_improvement and tail_not_worse and sample_ok
        ),
    )


def _stop_rate(rows: tuple[T02StructuralObservation, ...]) -> Decimal:
    if not rows:
        raise CiboCapitalManagementError("T02 stop rate requires rows")
    stopped = sum(1 for item in rows if item.stopped)
    return Decimal(stopped) / Decimal(len(rows))


def _p95_loss_r(rows: tuple[T02StructuralObservation, ...]) -> Decimal:
    losses = sorted(
        abs(item.structural_outcome_r)
        for item in rows
        if item.structural_outcome_r < 0
    )
    if not losses:
        return Decimal(0)
    rank = max(1, ceil(Decimal("0.95") * Decimal(len(losses))))
    return losses[rank - 1]
