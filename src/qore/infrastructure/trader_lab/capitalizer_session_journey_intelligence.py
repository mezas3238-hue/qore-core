"""Cross-session journey intelligence for QORE Capitalizer.

This layer makes the trading day continuous: Asia -> London -> New York. It exposes inherited
causal state to the current Session Brain without carrying positions across sessions and without
inventing capital authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_context_brains import (
    CapitalizerSessionBrainState,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_memory import (
    CapitalizerDailyJourney,
    CapitalizerLossMemory,
)
from qore.infrastructure.trader_lab.capitalizer_session_handoff import (
    CapitalizerSessionHandoff,
)

_PREVIOUS_SESSION: dict[CapitalizerSession, CapitalizerSession | None] = {
    CapitalizerSession.ASIA: None,
    CapitalizerSession.LONDON: CapitalizerSession.ASIA,
    CapitalizerSession.NEW_YORK: CapitalizerSession.LONDON,
}


@dataclass(frozen=True, slots=True)
class CapitalizerSessionJourneyAssessment:
    current_session: CapitalizerSession
    inherited_from: CapitalizerSession | None
    completed_sessions: tuple[CapitalizerSession, ...]
    realized_day_r: Decimal
    consumed_destinations: frozenset[str]
    failed_hypotheses: frozenset[str]
    killed_hypotheses: frozenset[str]
    killed_source_events: frozenset[str]
    unresolved_failure_fingerprints: frozenset[str]
    dominant_factors: tuple[str, ...]
    prior_factor_names: tuple[str, ...]
    requires_forward_memory: bool
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.grants_capital_authority:
            raise ValueError("Session/Journey intelligence cannot grant capital authority")


def assess_session_journey(
    *,
    session_brain: CapitalizerSessionBrainState,
    journey: CapitalizerDailyJourney,
    loss_memory: CapitalizerLossMemory,
) -> CapitalizerSessionJourneyAssessment:
    """Expose causal day history required by the current session."""

    current = session_brain.session
    previous = _PREVIOUS_SESSION[current]
    handoff = session_brain.prior_handoff

    if previous is None:
        if handoff is not None:
            raise ValueError("Asia cannot inherit a prior Capitalizer session handoff")
    else:
        if handoff is None:
            raise ValueError("London/New York require a causal prior-session handoff")
        if handoff.from_session is not previous or handoff.to_session is not current:
            raise ValueError("session handoff does not match chronological predecessor")
        if previous not in journey.completed_sessions:
            raise ValueError("prior session must be completed before current-session reasoning")
        if handoff.realized_day_r != journey.realized_r:
            raise ValueError("handoff/day journey realized R must agree")
        if handoff.consumed_destinations != journey.consumed_destinations:
            raise ValueError("handoff/day journey consumed destinations must agree")

    memory_failures = frozenset(
        item.failure_state_fingerprint for item in loss_memory.unresolved
    )
    inherited_failures = (
        handoff.unresolved_failure_fingerprints if handoff is not None else frozenset()
    )
    if handoff is not None and not inherited_failures.issubset(memory_failures):
        raise ValueError("handoff cannot contain failure state absent from current loss memory")

    killed_hypotheses = (
        handoff.killed_hypotheses if handoff is not None else frozenset()
    )
    killed_source_events = (
        handoff.killed_source_events if handoff is not None else frozenset()
    )
    prior_factor_names = tuple(
        exposure.factor
        for exposure in (handoff.factor_exposures if handoff is not None else ())
    )

    return CapitalizerSessionJourneyAssessment(
        current_session=current,
        inherited_from=previous,
        completed_sessions=journey.completed_sessions,
        realized_day_r=journey.realized_r,
        consumed_destinations=journey.consumed_destinations,
        failed_hypotheses=journey.failed_hypotheses,
        killed_hypotheses=killed_hypotheses,
        killed_source_events=killed_source_events,
        unresolved_failure_fingerprints=memory_failures,
        dominant_factors=journey.dominant_factors,
        prior_factor_names=prior_factor_names,
        requires_forward_memory=previous is not None,
    )
