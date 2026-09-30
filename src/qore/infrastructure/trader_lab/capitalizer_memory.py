"""Immutable cognitive memories for the QORE Capitalizer research candidate."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerDecision,
    CapitalizerSession,
)


@dataclass(frozen=True, slots=True)
class CapitalizerLossCause:
    """Causal description of a losing hypothesis, separate from its PnL."""

    loss_id: str
    symbol: str
    session: CapitalizerSession
    hypothesis_id: str
    failure_state_fingerprint: str
    realized_r: Decimal
    causes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.loss_id or not self.hypothesis_id or not self.failure_state_fingerprint:
            raise ValueError("loss identity fields must be non-empty")
        if self.symbol != self.symbol.upper() or not self.symbol:
            raise ValueError("symbol must be uppercase")
        if not isinstance(self.realized_r, Decimal) or not self.realized_r.is_finite():
            raise ValueError("realized_r must be finite")
        if self.realized_r >= 0:
            raise ValueError("loss memory accepts losing outcomes only")
        if not self.causes:
            raise ValueError("a loss requires at least one causal label")


@dataclass(frozen=True, slots=True)
class CapitalizerLossMemory:
    """Runtime-immutable view of unresolved failure states supplied to the fast brain."""

    unresolved: tuple[CapitalizerLossCause, ...] = ()

    def repeats_unresolved_failure(self, fingerprint: str | None) -> bool:
        if fingerprint is None:
            return False
        return any(item.failure_state_fingerprint == fingerprint for item in self.unresolved)


@dataclass(frozen=True, slots=True)
class CapitalizerSessionLedger:
    """Causal opportunity budget and reasoning-sovereignty ledger for one session."""

    session: CapitalizerSession
    executions: int = 0
    killed_hypotheses: frozenset[str] = frozenset()
    killed_source_events: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if self.executions < 0 or self.executions > MAX_EXECUTIONS_PER_SESSION:
            raise ValueError("session execution count violates frozen opportunity budget")

    @property
    def execution_budget_remaining(self) -> int:
        return MAX_EXECUTIONS_PER_SESSION - self.executions

    def record_decision(
        self,
        *,
        decision: CapitalizerDecision,
        hypothesis_id: str,
        source_event_id: str,
    ) -> CapitalizerSessionLedger:
        if decision is CapitalizerDecision.EXECUTE:
            if self.executions >= MAX_EXECUTIONS_PER_SESSION:
                raise ValueError("cannot execute beyond frozen session ceiling")
            return replace(self, executions=self.executions + 1)
        if decision is CapitalizerDecision.ABSTAIN:
            return replace(
                self,
                killed_hypotheses=self.killed_hypotheses | {hypothesis_id},
                killed_source_events=self.killed_source_events | {source_event_id},
            )
        return self


@dataclass(frozen=True, slots=True)
class CapitalizerDailyJourney:
    """Decision-time cross-session memory for the current operating day."""

    completed_sessions: tuple[CapitalizerSession, ...] = ()
    consumed_destinations: frozenset[str] = frozenset()
    failed_hypotheses: frozenset[str] = frozenset()
    dominant_factors: tuple[str, ...] = ()
    realized_r: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if not isinstance(self.realized_r, Decimal) or not self.realized_r.is_finite():
            raise ValueError("realized_r must be finite")

    def with_completed_session(self, session: CapitalizerSession) -> CapitalizerDailyJourney:
        if session in self.completed_sessions:
            return self
        return replace(self, completed_sessions=(*self.completed_sessions, session))
