"""Market/session-specific immutable experience memory for QORE Capitalizer."""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.trader_lab.capitalizer_confidence import (
    CapitalizerEvidenceCalibration,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CAPITALIZER_IDENTITY,
    CapitalizerSession,
    market_is_allowed,
)


@dataclass(frozen=True, slots=True)
class CapitalizerExperienceProfile:
    """One governed state-family profile learned outside the live critical path."""

    strategy_identity: str
    symbol: str
    session: CapitalizerSession
    state_family_id: str
    calibration: CapitalizerEvidenceCalibration
    behavior_tags: tuple[str, ...] = ()
    failure_tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.strategy_identity != CAPITALIZER_IDENTITY:
            raise ValueError("experience profile cannot rewrite strategy identity")
        if not market_is_allowed(session=self.session, symbol=self.symbol):
            raise ValueError("experience profile market must belong to its frozen session")
        if not self.state_family_id:
            raise ValueError("state_family_id must be non-empty")
        if self.calibration.state_family_id != self.state_family_id:
            raise ValueError("calibration must bind the exact state family")


@dataclass(frozen=True, slots=True)
class CapitalizerExperienceMemory:
    """Runtime-immutable collection of market/session experience profiles."""

    profiles: tuple[CapitalizerExperienceProfile, ...] = ()
    runtime_mutation_allowed: bool = False

    def __post_init__(self) -> None:
        if self.runtime_mutation_allowed:
            raise ValueError("experience memory cannot self-train in runtime")

    def lookup(
        self,
        *,
        symbol: str,
        session: CapitalizerSession,
        state_family_id: str,
    ) -> CapitalizerExperienceProfile | None:
        matches = tuple(
            profile
            for profile in self.profiles
            if profile.symbol == symbol
            and profile.session is session
            and profile.state_family_id == state_family_id
        )
        if len(matches) > 1:
            raise ValueError("duplicate experience profiles for the same exact state family")
        return matches[0] if matches else None
