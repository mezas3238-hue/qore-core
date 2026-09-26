from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_context_brains import (
    CapitalizerMarketBrainState,
    CapitalizerSessionBrainState,
    CapitalizerSessionPhase,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerDecision,
    CapitalizerSession,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_market_brain_registry import (
    CapitalizerMarketBrainRegistry,
)
from qore.infrastructure.trader_lab.capitalizer_memory import (
    CapitalizerDailyJourney,
    CapitalizerLossCause,
    CapitalizerLossMemory,
    CapitalizerSessionLedger,
)
from qore.infrastructure.trader_lab.capitalizer_microstructure import (
    CapitalizerMicrostructureTrace,
)
from qore.infrastructure.trader_lab.capitalizer_session_handoff import (
    build_session_handoff,
)
from qore.infrastructure.trader_lab.capitalizer_session_journey_intelligence import (
    assess_session_journey,
)


def _brains(at: datetime) -> tuple[CapitalizerMarketBrainState, ...]:
    return tuple(
        CapitalizerMarketBrainState(
            symbol=symbol,
            session=session,
            state_family_id=f"{session.value}_{symbol}_STATE",
            microstructure=CapitalizerMicrostructureTrace(
                decision_at=at,
                events=(),
            ),
        )
        for session in CapitalizerSession
        for symbol in sorted(allowed_markets(session))
    )


def test_market_brain_registry_binds_exact_nine_market_identity() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    registry = CapitalizerMarketBrainRegistry(_brains(at))

    assert len(registry.symbols) == 9
    assert len(registry.for_session(CapitalizerSession.ASIA)) == 4
    assert len(registry.for_session(CapitalizerSession.LONDON)) == 2
    assert len(registry.for_session(CapitalizerSession.NEW_YORK)) == 3
    assert registry.get("nas100").symbol == "NAS100"
    assert registry.runtime_mutation_allowed is False


def test_market_brain_registry_rejects_incomplete_universe() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="exactly the frozen nine markets"):
        CapitalizerMarketBrainRegistry(_brains(at)[:-1])


def test_london_requires_asia_handoff_and_inherits_failure_memory() -> None:
    loss = CapitalizerLossCause(
        loss_id="LOSS-ASIA-1",
        symbol="USDJPY",
        session=CapitalizerSession.ASIA,
        hypothesis_id="H-ASIA-LOSS",
        failure_state_fingerprint="FP-FALSE-EXPANSION",
        realized_r=Decimal("-1"),
        causes=("FALSE_EXPANSION",),
    )
    loss_memory = CapitalizerLossMemory(unresolved=(loss,))
    journey = CapitalizerDailyJourney(
        completed_sessions=(CapitalizerSession.ASIA,),
        consumed_destinations=frozenset({"ASIA_LOW"}),
        failed_hypotheses=frozenset({"H-ASIA-LOSS"}),
        dominant_factors=("JPY",),
        realized_r=Decimal("-1"),
    )
    asia_ledger = CapitalizerSessionLedger(CapitalizerSession.ASIA).record_decision(
        decision=CapitalizerDecision.ABSTAIN,
        hypothesis_id="H-KILLED",
        source_event_id="SRC-KILLED",
    )
    handoff = build_session_handoff(
        from_session=CapitalizerSession.ASIA,
        to_session=CapitalizerSession.LONDON,
        ledger=asia_ledger,
        journey=journey,
        loss_memory=loss_memory,
        factor_exposure_state=(),
    )
    session_brain = CapitalizerSessionBrainState(
        session=CapitalizerSession.LONDON,
        phase=CapitalizerSessionPhase.OPEN,
        prior_handoff=handoff,
    )

    assessment = assess_session_journey(
        session_brain=session_brain,
        journey=journey,
        loss_memory=loss_memory,
    )

    assert assessment.inherited_from is CapitalizerSession.ASIA
    assert assessment.realized_day_r == Decimal("-1")
    assert assessment.consumed_destinations == frozenset({"ASIA_LOW"})
    assert assessment.failed_hypotheses == frozenset({"H-ASIA-LOSS"})
    assert assessment.killed_hypotheses == frozenset({"H-KILLED"})
    assert assessment.killed_source_events == frozenset({"SRC-KILLED"})
    assert assessment.unresolved_failure_fingerprints == frozenset(
        {"FP-FALSE-EXPANSION"}
    )
    assert assessment.requires_forward_memory is True
    assert assessment.grants_capital_authority is False


def test_london_cannot_reason_without_prior_handoff() -> None:
    with pytest.raises(ValueError, match="require a causal prior-session handoff"):
        assess_session_journey(
            session_brain=CapitalizerSessionBrainState(
                session=CapitalizerSession.LONDON,
                phase=CapitalizerSessionPhase.OPEN,
            ),
            journey=CapitalizerDailyJourney(
                completed_sessions=(CapitalizerSession.ASIA,)
            ),
            loss_memory=CapitalizerLossMemory(),
        )


def test_asia_starts_without_prior_session_handoff() -> None:
    assessment = assess_session_journey(
        session_brain=CapitalizerSessionBrainState(
            session=CapitalizerSession.ASIA,
            phase=CapitalizerSessionPhase.OPEN,
        ),
        journey=CapitalizerDailyJourney(),
        loss_memory=CapitalizerLossMemory(),
    )

    assert assessment.inherited_from is None
    assert assessment.requires_forward_memory is False
