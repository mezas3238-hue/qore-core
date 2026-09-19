"""Causal session-to-session handoff for the QORE Capitalizer."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerFactorExposure
from qore.infrastructure.trader_lab.capitalizer_memory import (
    CapitalizerDailyJourney,
    CapitalizerLossMemory,
    CapitalizerSessionLedger,
)

_NEXT_SESSION: dict[CapitalizerSession, CapitalizerSession] = {
    CapitalizerSession.ASIA: CapitalizerSession.LONDON,
    CapitalizerSession.LONDON: CapitalizerSession.NEW_YORK,
}


@dataclass(frozen=True, slots=True)
class CapitalizerSessionHandoff:
    """Immutable causal payload passed from one completed session to the next."""

    from_session: CapitalizerSession
    to_session: CapitalizerSession
    prior_executions: int
    killed_hypotheses: frozenset[str]
    killed_source_events: frozenset[str]
    unresolved_failure_fingerprints: frozenset[str]
    consumed_destinations: frozenset[str]
    dominant_factors: tuple[str, ...]
    factor_exposures: tuple[CapitalizerFactorExposure, ...]
    realized_day_r: Decimal


def build_session_handoff(
    *,
    from_session: CapitalizerSession,
    to_session: CapitalizerSession,
    ledger: CapitalizerSessionLedger,
    journey: CapitalizerDailyJourney,
    loss_memory: CapitalizerLossMemory,
    factor_exposure_state: tuple[CapitalizerFactorExposure, ...],
) -> CapitalizerSessionHandoff:
    """Build forward-only handoff so later sessions retain the causal day history."""

    expected = _NEXT_SESSION.get(from_session)
    if expected is None or expected is not to_session:
        raise ValueError("session handoff must move Asia -> London -> New York")
    if ledger.session is not from_session:
        raise ValueError("ledger session must match handoff source session")
    if from_session not in journey.completed_sessions:
        raise ValueError("source session must be completed before handoff")

    return CapitalizerSessionHandoff(
        from_session=from_session,
        to_session=to_session,
        prior_executions=ledger.executions,
        killed_hypotheses=ledger.killed_hypotheses,
        killed_source_events=ledger.killed_source_events,
        unresolved_failure_fingerprints=frozenset(
            item.failure_state_fingerprint for item in loss_memory.unresolved
        ),
        consumed_destinations=journey.consumed_destinations,
        dominant_factors=journey.dominant_factors,
        factor_exposures=factor_exposure_state,
        realized_day_r=journey.realized_r,
    )
