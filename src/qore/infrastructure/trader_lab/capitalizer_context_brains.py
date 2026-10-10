"""Market and session brain state contracts for the QORE Capitalizer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    market_is_allowed,
)
from qore.infrastructure.trader_lab.capitalizer_experience_memory import (
    CapitalizerExperienceProfile,
)
from qore.infrastructure.trader_lab.capitalizer_microstructure import (
    CapitalizerMicrostructureTrace,
)
from qore.infrastructure.trader_lab.capitalizer_session_handoff import (
    CapitalizerSessionHandoff,
)


class CapitalizerSessionPhase(StrEnum):
    PREOPEN = "PREOPEN"
    OPEN = "OPEN"
    ACTIVE = "ACTIVE"
    LATE = "LATE"
    HANDOFF = "HANDOFF"


@dataclass(frozen=True, slots=True)
class CapitalizerSessionBrainState:
    session: CapitalizerSession
    phase: CapitalizerSessionPhase
    prior_handoff: CapitalizerSessionHandoff | None = None

    def __post_init__(self) -> None:
        if self.prior_handoff is not None and self.prior_handoff.to_session is not self.session:
            raise ValueError("session brain handoff must target the current session")


@dataclass(frozen=True, slots=True)
class CapitalizerMarketBrainState:
    """Market-specific state with optional governed experience attached."""

    symbol: str
    session: CapitalizerSession
    state_family_id: str
    microstructure: CapitalizerMicrostructureTrace
    experience: CapitalizerExperienceProfile | None = None

    def __post_init__(self) -> None:
        if not market_is_allowed(session=self.session, symbol=self.symbol):
            raise ValueError("market brain symbol is outside frozen session universe")
        if not self.state_family_id:
            raise ValueError("state_family_id must be non-empty")
        if self.experience is not None:
            if self.experience.symbol != self.symbol:
                raise ValueError("experience profile must match market brain symbol")
            if self.experience.session is not self.session:
                raise ValueError("experience profile must match market brain session")
            if self.experience.state_family_id != self.state_family_id:
                raise ValueError("experience profile must match market brain state family")
