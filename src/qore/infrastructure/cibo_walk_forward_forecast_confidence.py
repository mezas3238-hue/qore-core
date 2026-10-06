"""Causal maturity diagnostics for CIBO walk-forward expectations.

This module is deliberately predecision-only.  It consumes only the count and
five chronological block means already available to the walk-forward estimator.
It never consumes realized future outcome, PnL, execution results, or target
capital.  The result is diagnostic/read-only until explicitly wired and ablated.

The estimator uses five chronological blocks.  A forecast becomes structurally
mature for capital *consideration* only after each block can contain at least
five completed observations (5 blocks x 5 observations = 25).  This is an
estimator-maturity rule, not a profitability target and not certification.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

_BLOCK_COUNT = 5
_MINIMUM_FORECAST_OBSERVATIONS = 5
_MINIMUM_OBSERVATIONS_PER_BLOCK_FOR_MATURITY = 5
_MINIMUM_MATURE_OBSERVATIONS = (
    _BLOCK_COUNT * _MINIMUM_OBSERVATIONS_PER_BLOCK_FOR_MATURITY
)


class CiboWalkForwardMaturity(StrEnum):
    COLD_START = "COLD_START"
    PROVISIONAL = "PROVISIONAL"
    MATURE = "MATURE"


@dataclass(frozen=True, slots=True)
class CiboWalkForwardForecastConfidence:
    observation_count: int
    maturity: CiboWalkForwardMaturity
    mature_for_capital_consideration: bool
    expected_structural_r: Decimal | None
    positive_block_count: int
    nonpositive_block_count: int
    block_dispersion_r: Decimal
    median_absolute_deviation_r: Decimal
    maturity_fraction: Decimal
    future_outcome_used: bool = False
    capital_pnl_used: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.observation_count, int)
            or isinstance(self.observation_count, bool)
            or self.observation_count < 0
        ):
            raise CiboCapitalManagementError(
                "walk-forward confidence observation_count invalid"
            )
        if type(self.maturity) is not CiboWalkForwardMaturity:
            raise CiboCapitalManagementError(
                "walk-forward confidence maturity must be canonical"
            )
        if type(self.mature_for_capital_consideration) is not bool:
            raise CiboCapitalManagementError(
                "walk-forward confidence maturity-ready flag invalid"
            )
        for name in (
            "block_dispersion_r",
            "median_absolute_deviation_r",
            "maturity_fraction",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"walk-forward confidence {name} invalid"
                )
        if self.maturity_fraction > 1:
            raise CiboCapitalManagementError(
                "walk-forward confidence maturity_fraction exceeds one"
            )
        if self.positive_block_count + self.nonpositive_block_count not in {
            0,
            _BLOCK_COUNT,
        }:
            raise CiboCapitalManagementError(
                "walk-forward confidence block accounting invalid"
            )
        if (
            self.future_outcome_used
            or self.capital_pnl_used
            or self.sizing_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "walk-forward confidence governance violated"
            )


def _median(values: tuple[Decimal, ...]) -> Decimal:
    ordered = tuple(sorted(values))
    if not ordered:
        return Decimal(0)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    with localcontext() as context:
        context.prec = 100
        return (ordered[middle - 1] + ordered[middle]) / Decimal(2)


def assess_walk_forward_forecast_confidence(
    *,
    observation_count: int,
    expected_structural_r: Decimal | None,
    chronological_block_means_r: tuple[Decimal, ...],
) -> CiboWalkForwardForecastConfidence:
    """Assess forecast maturity using causal history only."""

    if (
        not isinstance(observation_count, int)
        or isinstance(observation_count, bool)
        or observation_count < 0
    ):
        raise CiboCapitalManagementError(
            "walk-forward confidence observation_count invalid"
        )

    if observation_count < _MINIMUM_FORECAST_OBSERVATIONS:
        if expected_structural_r is not None or chronological_block_means_r:
            raise CiboCapitalManagementError(
                "cold-start confidence received forecast semantics"
            )
        return CiboWalkForwardForecastConfidence(
            observation_count=observation_count,
            maturity=CiboWalkForwardMaturity.COLD_START,
            mature_for_capital_consideration=False,
            expected_structural_r=None,
            positive_block_count=0,
            nonpositive_block_count=0,
            block_dispersion_r=Decimal(0),
            median_absolute_deviation_r=Decimal(0),
            maturity_fraction=Decimal(0),
        )

    if (
        not isinstance(expected_structural_r, Decimal)
        or not expected_structural_r.is_finite()
        or len(chronological_block_means_r) != _BLOCK_COUNT
        or any(
            not isinstance(value, Decimal) or not value.is_finite()
            for value in chronological_block_means_r
        )
    ):
        raise CiboCapitalManagementError(
            "walk-forward confidence forecast semantics invalid"
        )

    positive_count = sum(
        1 for value in chronological_block_means_r if value > 0
    )
    nonpositive_count = _BLOCK_COUNT - positive_count
    dispersion = (
        max(chronological_block_means_r)
        - min(chronological_block_means_r)
    )
    deviations = tuple(
        abs(value - expected_structural_r)
        for value in chronological_block_means_r
    )
    mad = _median(deviations)
    with localcontext() as context:
        context.prec = 100
        maturity_fraction = min(
            Decimal(1),
            Decimal(observation_count) / Decimal(_MINIMUM_MATURE_OBSERVATIONS),
        )

    mature = observation_count >= _MINIMUM_MATURE_OBSERVATIONS
    return CiboWalkForwardForecastConfidence(
        observation_count=observation_count,
        maturity=(
            CiboWalkForwardMaturity.MATURE
            if mature
            else CiboWalkForwardMaturity.PROVISIONAL
        ),
        mature_for_capital_consideration=mature,
        expected_structural_r=expected_structural_r,
        positive_block_count=positive_count,
        nonpositive_block_count=nonpositive_count,
        block_dispersion_r=dispersion,
        median_absolute_deviation_r=mad,
        maturity_fraction=maturity_fraction,
    )


def walk_forward_mature_observation_count() -> int:
    return _MINIMUM_MATURE_OBSERVATIONS
