"""Phase19N direction-only factor topology for CE2I T08 research.

The topology maps symbol + side into qualitative factor directions. It never
assigns monetary factor magnitude, correlation, hedge effectiveness, margin
relief, or netting credit.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


class FactorDirection(IntEnum):
    SHORT = -1
    LONG = 1


class FactorTopologyRelation(StrEnum):
    NO_SHARED_FACTOR = "NO_SHARED_FACTOR"
    SAME_DIRECTION = "SAME_DIRECTION"
    OPPOSING_DIRECTION = "OPPOSING_DIRECTION"
    MIXED_DIRECTION = "MIXED_DIRECTION"


@dataclass(frozen=True, slots=True)
class DirectionalFactorExposure:
    factor: str
    direction: FactorDirection

    def __post_init__(self) -> None:
        if not self.factor:
            raise CiboCapitalManagementError("factor name is required")
        if type(self.direction) is not FactorDirection:
            raise CiboCapitalManagementError(
                "factor direction must be canonical"
            )


@dataclass(frozen=True, slots=True)
class FactorTopologyComparison:
    relation: FactorTopologyRelation
    shared_factors: tuple[str, ...]
    same_direction_factors: tuple[str, ...]
    opposing_direction_factors: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.relation) is not FactorTopologyRelation:
            raise CiboCapitalManagementError(
                "factor topology relation must be canonical"
            )
        shared = set(self.shared_factors)
        if shared != (
            set(self.same_direction_factors)
            | set(self.opposing_direction_factors)
        ):
            raise CiboCapitalManagementError(
                "factor topology shared-factor accounting drift"
            )
        if set(self.same_direction_factors) & set(
            self.opposing_direction_factors
        ):
            raise CiboCapitalManagementError(
                "factor cannot be same- and opposing-direction"
            )


_SUPPORTED_PAIR_SYMBOLS = frozenset(
    {
        "AUDJPY",
        "EURUSD",
        "GBPJPY",
        "GBPUSD",
        "XAUUSD",
    }
)


def directional_factor_exposures(
    *,
    qore_symbol: str,
    side: str,
) -> tuple[DirectionalFactorExposure, ...]:
    """Return qualitative factor directions without exposure magnitude."""

    symbol = qore_symbol.strip().upper()
    normalized_side = side.strip().lower()
    if normalized_side not in {"long", "short"}:
        raise CiboCapitalManagementError(
            "factor topology side must be long or short"
        )
    sign = (
        FactorDirection.LONG
        if normalized_side == "long"
        else FactorDirection.SHORT
    )

    if symbol == "NAS100":
        return (
            DirectionalFactorExposure(
                factor="US_TECH_EQUITY_BETA",
                direction=sign,
            ),
        )
    if symbol not in _SUPPORTED_PAIR_SYMBOLS:
        raise CiboCapitalManagementError(
            "factor topology symbol is outside frozen CIBO universe"
        )

    base = symbol[:3]
    quote = symbol[3:]
    return (
        DirectionalFactorExposure(factor=base, direction=sign),
        DirectionalFactorExposure(
            factor=quote,
            direction=FactorDirection(-int(sign)),
        ),
    )


def compare_factor_topology(
    *,
    left: tuple[DirectionalFactorExposure, ...],
    right: tuple[DirectionalFactorExposure, ...],
) -> FactorTopologyComparison:
    left_map = {item.factor: item.direction for item in left}
    right_map = {item.factor: item.direction for item in right}
    if len(left_map) != len(left) or len(right_map) != len(right):
        raise CiboCapitalManagementError(
            "duplicate factor in directional topology"
        )

    shared = tuple(sorted(set(left_map) & set(right_map)))
    same = tuple(
        factor
        for factor in shared
        if left_map[factor] is right_map[factor]
    )
    opposing = tuple(
        factor
        for factor in shared
        if left_map[factor] is not right_map[factor]
    )
    if not shared:
        relation = FactorTopologyRelation.NO_SHARED_FACTOR
    elif same and opposing:
        relation = FactorTopologyRelation.MIXED_DIRECTION
    elif same:
        relation = FactorTopologyRelation.SAME_DIRECTION
    else:
        relation = FactorTopologyRelation.OPPOSING_DIRECTION

    return FactorTopologyComparison(
        relation=relation,
        shared_factors=shared,
        same_direction_factors=same,
        opposing_direction_factors=opposing,
    )
