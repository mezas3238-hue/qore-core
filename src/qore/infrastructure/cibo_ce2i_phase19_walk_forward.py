"""Phase 19J causal walk-forward contracts for normalized capital policies.

The candidate policy suite is frozen by Phase 19I before any Phase 19J
validation outcome is consumed. Phase 19J may qualify or reject candidates, but
it may not tune their parameters, refit them between folds, rank them by a
validation score, or grant allocation/Risk/execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_normalized_capital import (
    Phase19NormalizedAllocationStatus,
)
from qore.infrastructure.cibo_ce2i_phase19_simple_policy import (
    Phase19SimplePolicyReplay,
)


def _aware(value: datetime, *, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(f"{name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class Phase19WalkForwardFold:
    fold_id: str
    history_cutoff_at: datetime
    validation_start_at: datetime
    validation_end_at: datetime
    policy_refit_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.fold_id:
            raise CiboCapitalManagementError(
                "walk-forward fold identity is required"
            )
        for name in (
            "history_cutoff_at",
            "validation_start_at",
            "validation_end_at",
        ):
            _aware(getattr(self, name), name=name)
        if self.history_cutoff_at != self.validation_start_at:
            raise CiboCapitalManagementError(
                "walk-forward history cutoff must equal validation start"
            )
        if self.validation_end_at <= self.validation_start_at:
            raise CiboCapitalManagementError(
                "walk-forward validation interval must be positive"
            )
        if self.policy_refit_authorized:
            raise CiboCapitalManagementError(
                "Phase 19J policy refit is not authorized"
            )


def build_phase19j_walk_forward_folds(
    *,
    frozen_at: datetime,
    common_end: datetime,
) -> tuple[Phase19WalkForwardFold, Phase19WalkForwardFold]:
    """Split the post-freeze interval into two outcome-agnostic time folds."""

    _aware(frozen_at, name="frozen_at")
    _aware(common_end, name="common_end")
    if common_end <= frozen_at:
        raise CiboCapitalManagementError(
            "walk-forward common end must follow freeze time"
        )
    remaining_seconds = int((common_end - frozen_at).total_seconds())
    midpoint = frozen_at + timedelta(seconds=remaining_seconds // 2)
    if midpoint <= frozen_at or midpoint >= common_end:
        raise CiboCapitalManagementError(
            "walk-forward midpoint must be strictly internal"
        )
    return (
        Phase19WalkForwardFold(
            fold_id="WF1_POST_FREEZE_FIRST_HALF",
            history_cutoff_at=frozen_at,
            validation_start_at=frozen_at,
            validation_end_at=midpoint,
        ),
        Phase19WalkForwardFold(
            fold_id="WF2_POST_FREEZE_SECOND_HALF",
            history_cutoff_at=midpoint,
            validation_start_at=midpoint,
            validation_end_at=common_end,
        ),
    )


def phase19j_survival_failures(
    *,
    combined: Phase19SimplePolicyReplay,
    folds: tuple[Phase19SimplePolicyReplay, ...],
) -> tuple[str, ...]:
    """Apply predeclared sign/survival gates without policy ranking."""

    if len(folds) != 2:
        raise CiboCapitalManagementError(
            "Phase 19J requires exactly two forward folds"
        )
    failures: list[str] = []
    if combined.replay.total_realized_delta_ncu <= 0:
        failures.append("COMBINED_REALIZED_DELTA_NOT_POSITIVE")
    if combined.replay.capacity_breach_observed:
        failures.append("COMBINED_CAPACITY_BREACH")
    if any(
        item.status
        is Phase19NormalizedAllocationStatus.REJECTED_INSOLVENT_CAPITAL
        for item in combined.replay.decisions
    ):
        failures.append("COMBINED_INSOLVENT_REJECTION")

    for index, result in enumerate(folds, start=1):
        if result.replay.total_realized_delta_ncu <= 0:
            failures.append(f"FOLD_{index}_REALIZED_DELTA_NOT_POSITIVE")
        if result.replay.capacity_breach_observed:
            failures.append(f"FOLD_{index}_CAPACITY_BREACH")
        if any(
            item.status
            is Phase19NormalizedAllocationStatus.REJECTED_INSOLVENT_CAPITAL
            for item in result.replay.decisions
        ):
            failures.append(f"FOLD_{index}_INSOLVENT_REJECTION")
    return tuple(failures)
