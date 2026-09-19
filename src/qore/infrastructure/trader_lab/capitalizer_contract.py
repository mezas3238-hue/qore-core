"""Frozen contracts for the QORE Capitalizer Cognitive Scalper.

Research-only. This module grants no execution, capital, promotion, or production authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


CAPITALIZER_IDENTITY = "QORE_CAPITALIZER_COGNITIVE_SCALPER_V1"
MAX_EXECUTIONS_PER_SESSION = 2


class CapitalizerSession(StrEnum):
    ASIA = "ASIA"
    LONDON = "LONDON"
    NEW_YORK = "NEW_YORK"


class CapitalizerDecision(StrEnum):
    EXECUTE = "EXECUTE"
    WAIT = "WAIT"
    ABSTAIN = "ABSTAIN"


class MarketState(StrEnum):
    BALANCE = "BALANCE"
    COMPRESSION = "COMPRESSION"
    BREAK_ATTEMPT = "BREAK_ATTEMPT"
    FAILED_BREAK = "FAILED_BREAK"
    ACCEPTANCE = "ACCEPTANCE"
    REJECTION = "REJECTION"
    DISPLACEMENT = "DISPLACEMENT"
    PULLBACK = "PULLBACK"
    CONTINUATION = "CONTINUATION"
    EXHAUSTION = "EXHAUSTION"
    REVERSAL = "REVERSAL"
    CHAOS = "CHAOS"


class EvidenceStrength(StrEnum):
    UNKNOWN = "UNKNOWN"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ExecutionQuality(StrEnum):
    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    BAD = "BAD"


class CapitalizationPosture(StrEnum):
    NORMAL = "NORMAL"
    CAUTIOUS = "CAUTIOUS"
    HIGH_SELECTIVITY = "HIGH_SELECTIVITY"
    STOP_SESSION = "STOP_SESSION"
    STOP_DAY = "STOP_DAY"


_SESSION_MARKETS: dict[CapitalizerSession, frozenset[str]] = {
    CapitalizerSession.ASIA: frozenset({"USDJPY", "AUDJPY", "AUDUSD", "GBPJPY"}),
    CapitalizerSession.LONDON: frozenset({"EURUSD", "GBPUSD"}),
    CapitalizerSession.NEW_YORK: frozenset({"XAUUSD", "USDCAD", "NAS100"}),
}


@dataclass(frozen=True, slots=True)
class CapitalizerStrategyIdentity:
    """Immutable methodology boundary for the Capitalizer research candidate."""

    identity: str = CAPITALIZER_IDENTITY
    max_executions_per_session: int = MAX_EXECUTIONS_PER_SESSION
    runtime_mutation_allowed: bool = False
    risk_authority: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if self.identity != CAPITALIZER_IDENTITY:
            raise ValueError("capitalizer identity is frozen")
        if self.max_executions_per_session != MAX_EXECUTIONS_PER_SESSION:
            raise ValueError("session execution ceiling is frozen at two")
        if self.runtime_mutation_allowed:
            raise ValueError("strategy identity cannot self-mutate at runtime")
        if self.risk_authority:
            raise ValueError("Capitalizer cognitive cannot own capital authority")
        if self.production_authority:
            raise ValueError("Capitalizer cognitive cannot own production authority")


def allowed_markets(session: CapitalizerSession) -> frozenset[str]:
    """Return the frozen research universe for one session."""

    return _SESSION_MARKETS[session]


def market_is_allowed(*, session: CapitalizerSession, symbol: str) -> bool:
    """Fail closed when a symbol is outside the frozen session research universe."""

    return symbol.upper() in _SESSION_MARKETS[session]
