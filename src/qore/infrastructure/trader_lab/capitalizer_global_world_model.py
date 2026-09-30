"""Causal global world model for QORE Capitalizer Master Brain.

The world model is one immutable decision-time representation of the trading day. It binds all
nine Market Brains, the current Session Brain, session ledgers, Daily Journey, unresolved loss
memory, open positions and derived factor exposure without granting execution/capital authority.

No field may contain information observed after the global observed timestamp.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_confidence import (
    CapitalizerKnowledgeState,
)
from qore.infrastructure.trader_lab.capitalizer_context_brains import (
    CapitalizerMarketBrainState,
    CapitalizerSessionBrainState,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerExposurePosition,
    CapitalizerFactorExposure,
    CapitalizerSide,
    factor_exposures,
)
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    NINE_MARKET_UNIVERSE,
    CapitalizerAttentionState,
    CapitalizerHypothesisStage,
)
from qore.infrastructure.trader_lab.capitalizer_memory import (
    CapitalizerDailyJourney,
    CapitalizerLossMemory,
    CapitalizerSessionLedger,
)

_SESSION_ORDER = (
    CapitalizerSession.ASIA,
    CapitalizerSession.LONDON,
    CapitalizerSession.NEW_YORK,
)


@dataclass(frozen=True, slots=True)
class CapitalizerMarketWorldState:
    """Cognitive state of one market as known at the global decision timestamp."""

    brain: CapitalizerMarketBrainState
    attention: CapitalizerAttentionState
    knowledge: CapitalizerKnowledgeState
    hypothesis_stage: CapitalizerHypothesisStage | None = None
    hypothesis_id: str | None = None
    source_event_id: str | None = None
    contradictions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        active = self.hypothesis_stage is not None
        if active != (self.hypothesis_id is not None):
            raise ValueError("hypothesis stage and hypothesis id must appear together")
        if active != (self.source_event_id is not None):
            raise ValueError("active hypothesis requires a source event identity")
        if self.attention is CapitalizerAttentionState.POSITION and not active:
            raise ValueError("POSITION attention requires an active hypothesis")
        if self.hypothesis_stage is CapitalizerHypothesisStage.THESIS_KILLED:
            if self.attention in {
                CapitalizerAttentionState.DECISION,
                CapitalizerAttentionState.POSITION,
            }:
                raise ValueError("killed hypothesis cannot remain DECISION/POSITION attention")

    @property
    def symbol(self) -> str:
        return self.brain.symbol

    @property
    def observed_at(self) -> datetime:
        return self.brain.microstructure.decision_at


@dataclass(frozen=True, slots=True)
class CapitalizerWorldPosition:
    """One open position visible to the Master Brain."""

    symbol: str
    side: CapitalizerSide
    risk_r: Decimal
    session: CapitalizerSession
    hypothesis_id: str
    source_event_id: str
    opened_at: datetime

    def __post_init__(self) -> None:
        if not self.hypothesis_id or not self.source_event_id:
            raise ValueError("world position requires hypothesis/source identity")
        if self.opened_at.tzinfo is None or self.opened_at.utcoffset() is None:
            raise ValueError("world position opened_at must be timezone-aware")
        CapitalizerExposurePosition(
            symbol=self.symbol,
            side=self.side,
            risk_r=self.risk_r,
        )

    @property
    def exposure_position(self) -> CapitalizerExposurePosition:
        return CapitalizerExposurePosition(
            symbol=self.symbol,
            side=self.side,
            risk_r=self.risk_r,
        )


@dataclass(frozen=True, slots=True)
class CapitalizerGlobalWorldModel:
    """Complete nine-market causal state consumed by the Capitalizer Master Brain."""

    observed_at: datetime
    current_session: CapitalizerSession
    session_brain: CapitalizerSessionBrainState
    markets: tuple[CapitalizerMarketWorldState, ...]
    session_ledgers: tuple[CapitalizerSessionLedger, ...]
    journey: CapitalizerDailyJourney
    loss_memory: CapitalizerLossMemory
    open_positions: tuple[CapitalizerWorldPosition, ...] = ()
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("world observed_at must be timezone-aware")
        if self.grants_capital_authority:
            raise ValueError("Global World Model cannot grant capital authority")
        if self.session_brain.session is not self.current_session:
            raise ValueError("session brain must match current world session")

        symbols = tuple(item.symbol for item in self.markets)
        if len(symbols) != 9 or frozenset(symbols) != NINE_MARKET_UNIVERSE:
            raise ValueError("Global World Model requires exactly the frozen nine markets")
        if len(set(symbols)) != len(symbols):
            raise ValueError("Global World Model cannot contain duplicate market brains")
        for market in self.markets:
            if market.observed_at > self.observed_at:
                raise ValueError("future Market Brain state cannot enter Global World Model")

        ledger_sessions = tuple(item.session for item in self.session_ledgers)
        if len(ledger_sessions) != 3 or set(ledger_sessions) != set(_SESSION_ORDER):
            raise ValueError("Global World Model requires one ledger per session")
        if len(set(ledger_sessions)) != len(ledger_sessions):
            raise ValueError("Global World Model cannot contain duplicate session ledgers")

        current_index = _SESSION_ORDER.index(self.current_session)
        allowed_completed = set(_SESSION_ORDER[:current_index])
        if not set(self.journey.completed_sessions).issubset(allowed_completed):
            raise ValueError("Daily Journey cannot contain future/completed-late sessions")

        for position in self.open_positions:
            if position.opened_at > self.observed_at:
                raise ValueError("future position cannot enter Global World Model")
            if position.session is not self.current_session:
                raise ValueError("Capitalizer positions cannot roll across sessions")
            matching = tuple(item for item in self.markets if item.symbol == position.symbol)
            if len(matching) != 1:
                raise ValueError("open position must map to exactly one Market Brain")
            market = matching[0]
            if market.attention is not CapitalizerAttentionState.POSITION:
                raise ValueError("open position market must have POSITION attention")
            if market.hypothesis_id != position.hypothesis_id:
                raise ValueError("open position hypothesis must match Market Brain")
            if market.source_event_id != position.source_event_id:
                raise ValueError("open position source event must match Market Brain")

    @property
    def current_ledger(self) -> CapitalizerSessionLedger:
        return next(
            ledger for ledger in self.session_ledgers if ledger.session is self.current_session
        )

    @property
    def execution_slots_remaining(self) -> int:
        return self.current_ledger.execution_budget_remaining

    @property
    def factor_exposure_state(self) -> tuple[CapitalizerFactorExposure, ...]:
        return factor_exposures(
            tuple(position.exposure_position for position in self.open_positions)
        )

    @property
    def unresolved_failure_fingerprints(self) -> frozenset[str]:
        return frozenset(
            item.failure_state_fingerprint for item in self.loss_memory.unresolved
        )

    @property
    def decision_symbols(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                item.symbol
                for item in self.markets
                if item.attention is CapitalizerAttentionState.DECISION
            )
        )

    @property
    def position_symbols(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                item.symbol
                for item in self.markets
                if item.attention is CapitalizerAttentionState.POSITION
            )
        )
