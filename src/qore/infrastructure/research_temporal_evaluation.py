from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from qore.infrastructure.research_run import ResearchRunEvidence
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class ResearchTemporalEvaluationError(InfrastructureError):
    """Base error for research temporal-evaluation evidence."""

    __slots__ = ()


class ResearchTemporalEvaluationValidationError(ResearchTemporalEvaluationError):
    """Violation of a temporal evaluation partition invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ResearchTemporalEvaluationValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResearchTemporalEvaluationValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class ResearchTemporalEvaluationPlanId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchTemporalEvaluationValidationError(
                "temporal evaluation plan id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchEvaluationWindow:
    """Half-open simulated-time interval [opened_at, closed_at)."""

    opened_at: datetime
    closed_at: datetime

    def __post_init__(self) -> None:
        _validate_timestamp(self.opened_at, field_name="evaluation opened_at")
        _validate_timestamp(self.closed_at, field_name="evaluation closed_at")
        if self.closed_at <= self.opened_at:
            raise ResearchTemporalEvaluationValidationError(
                "evaluation closed_at must be after opened_at"
            )

    def logical_values(self) -> tuple[str, str]:
        return (
            self.opened_at.astimezone(UTC).isoformat(timespec="microseconds"),
            self.closed_at.astimezone(UTC).isoformat(timespec="microseconds"),
        )


@dataclass(frozen=True, slots=True)
class ResearchWalkForwardFold:
    """One chronological in-sample window followed by out-of-sample evaluation.

    This fold proves temporal separation only. It does not prove that a human or
    optimizer had never inspected the out-of-sample data before the plan existed.
    """

    fold_number: int
    in_sample: ResearchEvaluationWindow
    out_of_sample: ResearchEvaluationWindow

    def __post_init__(self) -> None:
        if type(self.fold_number) is not int or self.fold_number <= 0:
            raise ResearchTemporalEvaluationValidationError(
                "walk-forward fold_number must be a positive integer"
            )
        if not isinstance(self.in_sample, ResearchEvaluationWindow):
            raise ResearchTemporalEvaluationValidationError(
                "walk-forward in_sample must be ResearchEvaluationWindow"
            )
        if not isinstance(self.out_of_sample, ResearchEvaluationWindow):
            raise ResearchTemporalEvaluationValidationError(
                "walk-forward out_of_sample must be ResearchEvaluationWindow"
            )
        if self.in_sample.closed_at > self.out_of_sample.opened_at:
            raise ResearchTemporalEvaluationValidationError(
                "in-sample window must close before or at out-of-sample opening"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.fold_number,
            self.in_sample.logical_values(),
            self.out_of_sample.logical_values(),
        )


def _canonical_folds(
    folds: tuple[ResearchWalkForwardFold, ...],
) -> tuple[ResearchWalkForwardFold, ...]:
    if not isinstance(folds, tuple) or not folds or any(
        not isinstance(item, ResearchWalkForwardFold) for item in folds
    ):
        raise ResearchTemporalEvaluationValidationError(
            "temporal evaluation requires a non-empty immutable fold tuple"
        )
    ordered = tuple(
        sorted(
            folds,
            key=lambda item: (
                item.out_of_sample.opened_at.astimezone(UTC),
                item.fold_number,
            ),
        )
    )
    expected_numbers = tuple(range(1, len(ordered) + 1))
    actual_numbers = tuple(item.fold_number for item in ordered)
    if actual_numbers != expected_numbers:
        raise ResearchTemporalEvaluationValidationError(
            "walk-forward folds must use contiguous numbering from one"
        )
    previous_out_of_sample: ResearchEvaluationWindow | None = None
    for fold in ordered:
        if previous_out_of_sample is not None and (
            fold.out_of_sample.opened_at < previous_out_of_sample.closed_at
        ):
            raise ResearchTemporalEvaluationValidationError(
                "out-of-sample windows must not overlap"
            )
        previous_out_of_sample = fold.out_of_sample
    return ordered


@dataclass(frozen=True, slots=True)
class ResearchTemporalEvaluationPlan:
    """Immutable chronological partition plan for one research run.

    The contract makes in-sample/out-of-sample overlap structurally invalid and
    keeps every fold inside the run's simulated window. It does not execute
    training, optimization, performance statistics, or prove epistemic blindness.
    """

    plan_id: ResearchTemporalEvaluationPlanId
    run: ResearchRunEvidence
    folds: tuple[ResearchWalkForwardFold, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.plan_id, ResearchTemporalEvaluationPlanId):
            raise ResearchTemporalEvaluationValidationError(
                "plan_id must be ResearchTemporalEvaluationPlanId"
            )
        if not isinstance(self.run, ResearchRunEvidence):
            raise ResearchTemporalEvaluationValidationError(
                "temporal evaluation plan requires ResearchRunEvidence"
            )
        _validate_timestamp(self.created_at, field_name="evaluation plan created_at")
        ordered = _canonical_folds(self.folds)
        if self.folds != ordered:
            raise ResearchTemporalEvaluationValidationError(
                "walk-forward folds must be stored in canonical evaluation order"
            )
        for fold in ordered:
            for window in (fold.in_sample, fold.out_of_sample):
                if (
                    window.opened_at < self.run.simulated_start
                    or window.closed_at > self.run.simulated_end
                ):
                    raise ResearchTemporalEvaluationValidationError(
                        "every evaluation window must remain inside research run bounds"
                    )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.plan_id.logical_values(),
            self.run.logical_values(),
            tuple(item.logical_values() for item in self.folds),
            self.created_at.isoformat(),
        )


def build_research_temporal_evaluation_plan(
    *,
    plan_id: ResearchTemporalEvaluationPlanId,
    run: ResearchRunEvidence,
    folds: tuple[ResearchWalkForwardFold, ...],
    created_at: datetime,
) -> Result[ResearchTemporalEvaluationPlan, ResearchTemporalEvaluationError]:
    """Build a deterministic temporal partition without performing validation."""

    try:
        ordered = _canonical_folds(folds)
        return Success(
            ResearchTemporalEvaluationPlan(
                plan_id=plan_id,
                run=run,
                folds=ordered,
                created_at=created_at,
            )
        )
    except ResearchTemporalEvaluationError as error:
        return Failure(error)
