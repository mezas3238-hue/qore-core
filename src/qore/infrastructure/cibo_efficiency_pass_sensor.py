"""Longitudinal efficiency sensor for CIBO Maximum Capability.

Measures pass-to-pass improvement without granting any productive authority.
The sovereign score remains non-compensatory: it is the weakest mandatory
dimension from the Maximum Capability scorecard.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_maximum_capability_efficiency import (
    CiboMaximumCapabilityScorecard,
)


class CiboEfficiencyTrend(StrEnum):
    IMPROVED = "IMPROVED"
    REGRESSED = "REGRESSED"
    UNCHANGED = "UNCHANGED"


@dataclass(frozen=True, slots=True)
class CiboEfficiencyPassSnapshot:
    pass_id: str
    scorecard: CiboMaximumCapabilityScorecard

    def __post_init__(self) -> None:
        if not self.pass_id:
            raise CiboCapitalManagementError(
                "Efficiency pass_id is required"
            )
        if not isinstance(
            self.scorecard,
            CiboMaximumCapabilityScorecard,
        ):
            raise CiboCapitalManagementError(
                "Efficiency pass requires canonical scorecard"
            )


@dataclass(frozen=True, slots=True)
class CiboEfficiencyDimensionDelta:
    dimension: str
    before: Decimal
    after: Decimal
    absolute_delta: Decimal
    basis_points_delta: Decimal
    trend: CiboEfficiencyTrend

    def __post_init__(self) -> None:
        for name in ("before", "after"):
            value = getattr(self, name)
            if value < 0 or value > 1:
                raise CiboCapitalManagementError(
                    f"Efficiency delta {name} outside [0,1]"
                )
        if self.absolute_delta != self.after - self.before:
            raise CiboCapitalManagementError(
                "Efficiency absolute delta drift"
            )
        if self.basis_points_delta != self.absolute_delta * Decimal(10000):
            raise CiboCapitalManagementError(
                "Efficiency basis-point delta drift"
            )
        expected = (
            CiboEfficiencyTrend.IMPROVED
            if self.absolute_delta > 0
            else (
                CiboEfficiencyTrend.REGRESSED
                if self.absolute_delta < 0
                else CiboEfficiencyTrend.UNCHANGED
            )
        )
        if self.trend is not expected:
            raise CiboCapitalManagementError(
                "Efficiency trend classification drift"
            )


@dataclass(frozen=True, slots=True)
class CiboEfficiencyPassDelta:
    before_pass_id: str
    after_pass_id: str
    sovereign_before: Decimal
    sovereign_after: Decimal
    sovereign_absolute_delta: Decimal
    sovereign_basis_points_delta: Decimal
    sovereign_trend: CiboEfficiencyTrend
    dimension_deltas: tuple[CiboEfficiencyDimensionDelta, ...]
    improved_dimensions: int
    regressed_dimensions: int
    unchanged_dimensions: int
    weakest_dimension_after: str
    target_efficiency: Decimal
    target_proven_after: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.before_pass_id or not self.after_pass_id:
            raise CiboCapitalManagementError(
                "Efficiency pass identities are required"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "Efficiency sensor cannot acquire productive authority"
            )
        if (
            self.improved_dimensions
            + self.regressed_dimensions
            + self.unchanged_dimensions
            != len(self.dimension_deltas)
        ):
            raise CiboCapitalManagementError(
                "Efficiency dimension counts drift"
            )
        if self.sovereign_absolute_delta != (
            self.sovereign_after - self.sovereign_before
        ):
            raise CiboCapitalManagementError(
                "Efficiency sovereign delta drift"
            )
        if self.sovereign_basis_points_delta != (
            self.sovereign_absolute_delta * Decimal(10000)
        ):
            raise CiboCapitalManagementError(
                "Efficiency sovereign basis-point delta drift"
            )

    @property
    def improved_without_regression(self) -> bool:
        return (
            self.sovereign_trend is CiboEfficiencyTrend.IMPROVED
            and self.regressed_dimensions == 0
        )


def compare_efficiency_passes(
    before: CiboEfficiencyPassSnapshot,
    after: CiboEfficiencyPassSnapshot,
) -> CiboEfficiencyPassDelta:
    """Measure exact pass-to-pass efficiency movement."""

    before_map = dict(before.scorecard.dimensions)
    after_map = dict(after.scorecard.dimensions)
    if tuple(before_map) != tuple(after_map):
        raise CiboCapitalManagementError(
            "Efficiency pass dimension identity/order drift"
        )

    deltas = []
    for dimension in before_map:
        prior = before_map[dimension]
        current = after_map[dimension]
        delta = current - prior
        trend = (
            CiboEfficiencyTrend.IMPROVED
            if delta > 0
            else (
                CiboEfficiencyTrend.REGRESSED
                if delta < 0
                else CiboEfficiencyTrend.UNCHANGED
            )
        )
        deltas.append(
            CiboEfficiencyDimensionDelta(
                dimension=dimension,
                before=prior,
                after=current,
                absolute_delta=delta,
                basis_points_delta=delta * Decimal(10000),
                trend=trend,
            )
        )

    sovereign_delta = (
        after.scorecard.maximum_capability_efficiency
        - before.scorecard.maximum_capability_efficiency
    )
    sovereign_trend = (
        CiboEfficiencyTrend.IMPROVED
        if sovereign_delta > 0
        else (
            CiboEfficiencyTrend.REGRESSED
            if sovereign_delta < 0
            else CiboEfficiencyTrend.UNCHANGED
        )
    )
    weakest = min(
        after.scorecard.dimensions,
        key=lambda item: (item[1], item[0]),
    )[0]

    return CiboEfficiencyPassDelta(
        before_pass_id=before.pass_id,
        after_pass_id=after.pass_id,
        sovereign_before=before.scorecard.maximum_capability_efficiency,
        sovereign_after=after.scorecard.maximum_capability_efficiency,
        sovereign_absolute_delta=sovereign_delta,
        sovereign_basis_points_delta=sovereign_delta * Decimal(10000),
        sovereign_trend=sovereign_trend,
        dimension_deltas=tuple(deltas),
        improved_dimensions=sum(
            item.trend is CiboEfficiencyTrend.IMPROVED
            for item in deltas
        ),
        regressed_dimensions=sum(
            item.trend is CiboEfficiencyTrend.REGRESSED
            for item in deltas
        ),
        unchanged_dimensions=sum(
            item.trend is CiboEfficiencyTrend.UNCHANGED
            for item in deltas
        ),
        weakest_dimension_after=weakest,
        target_efficiency=after.scorecard.target_efficiency,
        target_proven_after=after.scorecard.target_proven,
    )
