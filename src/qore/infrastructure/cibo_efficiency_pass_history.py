"""Immutable history for CIBO Maximum Capability efficiency passes."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_efficiency_pass_sensor import (
    CiboEfficiencyPassDelta,
    CiboEfficiencyPassSnapshot,
    compare_efficiency_passes,
)


@dataclass(frozen=True, slots=True)
class CiboEfficiencyPassHistory:
    passes: tuple[CiboEfficiencyPassSnapshot, ...] = ()

    def __post_init__(self) -> None:
        ids = tuple(item.pass_id for item in self.passes)
        if len(ids) != len(set(ids)):
            raise CiboCapitalManagementError(
                "Efficiency history pass ids must be unique"
            )

    @property
    def latest(self) -> CiboEfficiencyPassSnapshot | None:
        return self.passes[-1] if self.passes else None

    @property
    def best(self) -> CiboEfficiencyPassSnapshot | None:
        if not self.passes:
            return None
        return max(
            self.passes,
            key=lambda item: (
                item.scorecard.maximum_capability_efficiency,
                item.pass_id,
            ),
        )

    @property
    def target_distance(self) -> Decimal | None:
        if self.latest is None:
            return None
        return max(
            Decimal(0),
            self.latest.scorecard.target_efficiency
            - self.latest.scorecard.maximum_capability_efficiency,
        )

    @property
    def deltas(self) -> tuple[CiboEfficiencyPassDelta, ...]:
        return tuple(
            compare_efficiency_passes(before, after)
            for before, after in zip(
                self.passes,
                self.passes[1:],
                strict=False,
            )
        )

    @property
    def regression_count(self) -> int:
        return sum(
            item.regressed_dimensions > 0
            for item in self.deltas
        )

    @property
    def clean_improvement_count(self) -> int:
        return sum(
            item.improved_without_regression
            for item in self.deltas
        )


def append_efficiency_pass(
    history: CiboEfficiencyPassHistory,
    snapshot: CiboEfficiencyPassSnapshot,
) -> CiboEfficiencyPassHistory:
    """Append one immutable pass, rejecting duplicate identities."""

    if snapshot.pass_id in {item.pass_id for item in history.passes}:
        raise CiboCapitalManagementError(
            "Efficiency history duplicate pass id"
        )
    return CiboEfficiencyPassHistory(
        passes=history.passes + (snapshot,)
    )
