"""Portfolio-aware supervision for open Capitalizer positions.

The supervisor exposes shared factor concentration and thesis identity across simultaneously open
positions. It does not size, widen stops, select exits or grant capital authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_global_world_model import (
    CapitalizerGlobalWorldModel,
)


@dataclass(frozen=True, slots=True)
class CapitalizerSharedFactorPositionGroup:
    factor: str
    symbols: tuple[str, ...]
    gross_r: Decimal
    net_r: Decimal


@dataclass(frozen=True, slots=True)
class CapitalizerPortfolioPositionAssessment:
    position_symbols: tuple[str, ...]
    shared_factor_groups: tuple[CapitalizerSharedFactorPositionGroup, ...]
    review_required: bool
    reasons: tuple[str, ...]
    stop_widening_allowed: bool = False
    grants_exit_authority: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.stop_widening_allowed:
            raise ValueError("portfolio supervisor cannot widen stops")
        if self.grants_exit_authority:
            raise ValueError("portfolio supervisor does not own exit authority")
        if self.grants_capital_authority:
            raise ValueError("portfolio supervisor cannot grant capital authority")


def assess_portfolio_positions(
    world: CapitalizerGlobalWorldModel,
) -> CapitalizerPortfolioPositionAssessment:
    factor_to_symbols: dict[str, set[str]] = {}
    exposure_by_factor = {item.factor: item for item in world.factor_exposure_state}

    for position in world.open_positions:
        for exposure in (
            item
            for item in world.factor_exposure_state
            if item.gross_r > 0
        ):
            # Exposure membership is derived below from the canonical position map.
            del exposure
        from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
            factor_exposures,
        )

        one = factor_exposures((position.exposure_position,))
        for factor in one:
            factor_to_symbols.setdefault(factor.factor, set()).add(position.symbol)

    groups = tuple(
        CapitalizerSharedFactorPositionGroup(
            factor=factor,
            symbols=tuple(sorted(symbols)),
            gross_r=exposure_by_factor[factor].gross_r,
            net_r=exposure_by_factor[factor].net_r,
        )
        for factor, symbols in sorted(factor_to_symbols.items())
        if len(symbols) > 1
    )

    reasons: list[str] = []
    if groups:
        reasons.append("SHARED_FACTOR_OPEN_POSITIONS")
    if len(world.open_positions) > 1:
        reasons.append("MULTIPLE_OPEN_POSITIONS")

    return CapitalizerPortfolioPositionAssessment(
        position_symbols=tuple(sorted(position.symbol for position in world.open_positions)),
        shared_factor_groups=groups,
        review_required=bool(reasons),
        reasons=tuple(reasons) if reasons else ("NO_PORTFOLIO_POSITION_CONFLICT",),
    )
