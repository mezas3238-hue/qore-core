"""Journey and destination contracts for the QORE Capitalizer."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_contract import EvidenceStrength


class CapitalizerJourneyStage(StrEnum):
    BUILDING = "BUILDING"
    LIQUIDITY_EVENT = "LIQUIDITY_EVENT"
    CONFIRMATION = "CONFIRMATION"
    DELIVERY = "DELIVERY"
    EXHAUSTED = "EXHAUSTED"


@dataclass(frozen=True, slots=True)
class CapitalizerDestinationState:
    """Decision-time structural destination candidate."""

    destination_id: str
    family: str
    distance_r: Decimal
    consumed: bool
    structurally_available: bool
    evidence_strength: EvidenceStrength

    def __post_init__(self) -> None:
        if not self.destination_id or not self.family:
            raise ValueError("destination identity must be non-empty")
        if not isinstance(self.distance_r, Decimal) or not self.distance_r.is_finite():
            raise ValueError("distance_r must be finite")
        if self.distance_r < 0:
            raise ValueError("distance_r must be non-negative")


@dataclass(frozen=True, slots=True)
class CapitalizerJourneyState:
    """Causal journey snapshot; it does not select targets by itself."""

    stage: CapitalizerJourneyStage
    destinations: tuple[CapitalizerDestinationState, ...] = ()

    def eligible_destinations(self) -> tuple[CapitalizerDestinationState, ...]:
        """Return still-available destinations without inventing a target policy."""

        eligible = tuple(
            destination
            for destination in self.destinations
            if not destination.consumed and destination.structurally_available
        )
        return tuple(sorted(eligible, key=lambda item: (item.distance_r, item.destination_id)))
