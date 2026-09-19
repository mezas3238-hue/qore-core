"""Position intelligence contracts for the QORE Capitalizer.

Position intelligence cannot change the original strategy identity or grant re-entry after an
ABSTAIN without a genuinely new structural event.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

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
