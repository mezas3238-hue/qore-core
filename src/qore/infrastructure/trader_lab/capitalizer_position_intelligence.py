"""Position intelligence contracts for the QORE Capitalizer.

Position intelligence cannot change the original strategy identity or grant re-entry after an
ABSTAIN without a genuinely new structural event.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_situation_model import (
    CapitalizerSituationModel,
)


class CapitalizerPositionAction(StrEnum):
    HOLD = "HOLD"
    PROTECT = "PROTECT"
    EXIT = "EXIT"


@dataclass(frozen=True, slots=True)
class CapitalizerOpenPositionState:
    hypothesis_id: str
    source_event_id: str
    invalidated: bool
    destination_reached: bool
    structural_protection_available: bool

    def __post_init__(self) -> None:
        if not self.hypothesis_id or not self.source_event_id:
            raise ValueError("position thesis identity must be non-empty")


@dataclass(frozen=True, slots=True)
class CapitalizerPositionRecommendation:
    action: CapitalizerPositionAction
    reasons: tuple[str, ...]
    grants_reentry: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.grants_reentry:
            raise ValueError("position intelligence cannot grant re-entry")
        if self.grants_capital_authority:
            raise ValueError("position intelligence cannot grant capital authority")


def reason_open_position(
    position: CapitalizerOpenPositionState,
) -> CapitalizerPositionRecommendation:
    """Apply only structural lifecycle invariants; economics remain strategy-certified elsewhere."""

    if position.invalidated:
        return CapitalizerPositionRecommendation(
            action=CapitalizerPositionAction.EXIT,
            reasons=("STRUCTURAL_INVALIDATION",),
        )
    if position.destination_reached and position.structural_protection_available:
        return CapitalizerPositionRecommendation(
            action=CapitalizerPositionAction.PROTECT,
            reasons=("DESTINATION_REACHED", "STRUCTURAL_PROTECTION_AVAILABLE"),
        )
    return CapitalizerPositionRecommendation(
        action=CapitalizerPositionAction.HOLD,
        reasons=("ORIGINAL_THESIS_STILL_ACTIVE",),
    )


def rearm_is_genuinely_new(
    *,
    prior_hypothesis_id: str,
    prior_source_event_id: str,
    prior_event_generation: int,
    new_situation: CapitalizerSituationModel,
) -> bool:
    """Require new hypothesis + source + later event generation before rearm can be considered."""

    return (
        new_situation.hypothesis_id != prior_hypothesis_id
        and new_situation.source_event_id != prior_source_event_id
        and new_situation.event_generation > prior_event_generation
    )


@dataclass(frozen=True, slots=True)
class CapitalizerPositionBoundaryState:
    """Non-economic position-management boundary for Cognitive Closure V2."""

    side: CapitalizerSide
    entry_price: Decimal
    original_stop_price: Decimal
    current_stop_price: Decimal
    original_target_price: Decimal
    current_target_price: Decimal

    def __post_init__(self) -> None:
        for value in (
            self.entry_price,
            self.original_stop_price,
            self.current_stop_price,
            self.original_target_price,
            self.current_target_price,
        ):
            if not isinstance(value, Decimal) or not value.is_finite():
                raise ValueError("position prices must be finite Decimal values")
        if self.current_target_price != self.original_target_price:
            raise ValueError(
                "base Position Intelligence cannot mutate target before Target Intelligence"
            )
        if self.side is CapitalizerSide.LONG:
            if self.current_stop_price < self.original_stop_price:
                raise ValueError("LONG stop cannot widen below original stop")
        else:
            if self.current_stop_price > self.original_stop_price:
                raise ValueError("SHORT stop cannot widen above original stop")


@dataclass(frozen=True, slots=True)
class CapitalizerPositionBoundaryAssessment:
    stop_monotonic: bool
    target_unchanged: bool
    break_even_policy_frozen: bool = False
    trailing_stop_policy_frozen: bool = False
    trailing_target_policy_frozen: bool = False
    zig_zig_policy_frozen: bool = False
    grants_reentry: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if not self.stop_monotonic:
            raise ValueError("Position Intelligence cannot accept a widening stop")
        if not self.target_unchanged:
            raise ValueError("Position Intelligence base cannot mutate target")
        if (
            self.break_even_policy_frozen
            or self.trailing_stop_policy_frozen
            or self.trailing_target_policy_frozen
            or self.zig_zig_policy_frozen
        ):
            raise ValueError(
                "advanced position policies remain separate research chains"
            )
        if self.grants_reentry:
            raise ValueError("Position Intelligence cannot grant re-entry")
        if self.grants_capital_authority:
            raise ValueError("Position Intelligence cannot grant capital authority")


def assess_position_boundary(
    position: CapitalizerPositionBoundaryState,
) -> CapitalizerPositionBoundaryAssessment:
    """Prove the frozen base boundary without selecting BE/trailing/target policies."""

    if position.side is CapitalizerSide.LONG:
        monotonic = position.current_stop_price >= position.original_stop_price
    else:
        monotonic = position.current_stop_price <= position.original_stop_price

    return CapitalizerPositionBoundaryAssessment(
        stop_monotonic=monotonic,
        target_unchanged=position.current_target_price == position.original_target_price,
    )
