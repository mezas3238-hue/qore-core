"""Position Intelligence and genuine rearm boundary for CRT PURE."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.traders.crt_pure_cognitive_contract import (
    CrtPurePositionAction,
)
from qore.infrastructure.traders.crt_pure_cognitive_state import (
    CrtPureSituationModel,
)


class CrtPurePositionSide(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True, slots=True)
class CrtPureOpenPositionState:
    hypothesis_id: str
    source_event_id: str
    side: CrtPurePositionSide
    entry_price: Decimal
    original_stop_price: Decimal
    current_stop_price: Decimal
    original_target_price: Decimal
    current_target_price: Decimal
    structurally_invalidated: bool = False
    authorized_destination_reached: bool = False
    structural_protection_available: bool = False

    def __post_init__(self) -> None:
        if not self.hypothesis_id or not self.source_event_id:
            raise ValueError("position thesis identity must be non-empty")
        for value in (
            self.entry_price,
            self.original_stop_price,
            self.current_stop_price,
            self.original_target_price,
            self.current_target_price,
        ):
            if not isinstance(value, Decimal) or not value.is_finite():
                raise ValueError("position prices must be finite Decimal values")
        if self.side is CrtPurePositionSide.LONG:
            if self.current_stop_price < self.original_stop_price:
                raise ValueError("LONG stop cannot widen below original stop")
        else:
            if self.current_stop_price > self.original_stop_price:
                raise ValueError("SHORT stop cannot widen above original stop")


@dataclass(frozen=True, slots=True)
class CrtPurePositionRecommendation:
    action: CrtPurePositionAction
    reasons: tuple[str, ...]
    next_stop_price: Decimal | None = None
    grants_reentry: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.grants_reentry:
            raise ValueError("CRT Position Intelligence cannot grant re-entry")
        if self.grants_capital_authority:
            raise ValueError("CRT Position Intelligence cannot grant capital authority")


def improves_stop(
    position: CrtPureOpenPositionState,
    candidate_stop: Decimal,
) -> bool:
    if not candidate_stop.is_finite():
        return False
    if position.side is CrtPurePositionSide.LONG:
        return position.current_stop_price < candidate_stop < position.current_target_price
    return position.current_target_price < candidate_stop < position.current_stop_price


def reason_open_position(
    position: CrtPureOpenPositionState,
    *,
    structural_protection_level: Decimal | None = None,
) -> CrtPurePositionRecommendation:
    """Apply only source-agnostic structural safety invariants.

    Break-even, trailing, target extension, Zig-Zig and other advanced management
    policies remain separate CRT research chains and are not invented here.
    """
    if position.structurally_invalidated:
        return CrtPurePositionRecommendation(
            action=CrtPurePositionAction.EXIT,
            reasons=("CRT_STRUCTURAL_INVALIDATION",),
        )

    if (
        position.authorized_destination_reached
        and position.structural_protection_available
        and structural_protection_level is not None
        and improves_stop(position, structural_protection_level)
    ):
        return CrtPurePositionRecommendation(
            action=CrtPurePositionAction.PROTECT,
            reasons=(
                "AUTHORIZED_DESTINATION_REACHED",
                "STRUCTURAL_PROTECTION_AVAILABLE",
                "STOP_IMPROVES_MONOTONICALLY",
            ),
            next_stop_price=structural_protection_level,
        )

    return CrtPurePositionRecommendation(
        action=CrtPurePositionAction.HOLD,
        reasons=("ORIGINAL_CRT_THESIS_REMAINS_ACTIVE",),
    )


def rearm_is_genuinely_new(
    *,
    prior_hypothesis_id: str,
    prior_source_event_id: str,
    prior_event_generation: int,
    new_situation: CrtPureSituationModel,
) -> bool:
    """Require a new hypothesis, source event and later generation after ABSTAIN/exit."""
    return (
        new_situation.hypothesis_id != prior_hypothesis_id
        and new_situation.source_event_id != prior_source_event_id
        and new_situation.event_generation > prior_event_generation
    )
