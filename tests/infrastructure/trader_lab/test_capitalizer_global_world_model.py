from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_confidence import (
    CapitalizerKnowledgeState,
)
from qore.infrastructure.trader_lab.capitalizer_context_brains import (
    CapitalizerMarketBrainState,
    CapitalizerSessionBrainState,
    CapitalizerSessionPhase,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_global_world_model import (
    CapitalizerGlobalWorldModel,
    CapitalizerMarketWorldState,
    CapitalizerWorldPosition,
)
from qore.infrastructure.trader_lab.capitalizer_master_brain import (
    assess_master_brain,
)
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    CapitalizerAttentionState,
    CapitalizerHypothesisStage,
)
from qore.infrastructure.trader_lab.capitalizer_memory import (
    CapitalizerDailyJourney,
    CapitalizerLossMemory,
    CapitalizerSessionLedger,
)
from qore.infrastructure.trader_lab.capitalizer_microstructure import (
    CapitalizerMicrostructureTrace,
)


def _markets(
    at: datetime,
    *,
    overrides: dict[str, tuple[CapitalizerAttentionState, CapitalizerKnowledgeState]] | None = None,
) -> tuple[CapitalizerMarketWorldState, ...]:
    states: list[CapitalizerMarketWorldState] = []
    overrides = overrides or {}
    for session in CapitalizerSession:
        for symbol in sorted(allowed_markets(session)):
            attention, knowledge = overrides.get(
                symbol,
                (
                    CapitalizerAttentionState.BACKGROUND,
                    CapitalizerKnowledgeState.KNOWN,
                ),
            )
            active = attention in {
                CapitalizerAttentionState.DECISION,
                CapitalizerAttentionState.POSITION,
            }
            states.append(
                CapitalizerMarketWorldState(
                    brain=CapitalizerMarketBrainState(
                        symbol=symbol,
                        session=session,
                        state_family_id="DEVELOPMENT_STATE",
                        microstructure=CapitalizerMicrostructureTrace(
                            decision_at=at,
                            events=(),
                        ),
                    ),
                    attention=attention,
                    knowledge=knowledge,
                    hypothesis_stage=(
                        CapitalizerHypothesisStage.EXECUTABLE if active else None
                    ),
                    hypothesis_id=f"H-{symbol}" if active else None,
                    source_event_id=f"SRC-{symbol}" if active else None,
                )
            )
    return tuple(states)


def _ledgers(*, asia_executions: int = 0) -> tuple[CapitalizerSessionLedger, ...]:
    return (
        CapitalizerSessionLedger(
            session=CapitalizerSession.ASIA,
            executions=asia_executions,
        ),
        CapitalizerSessionLedger(session=CapitalizerSession.LONDON),
        CapitalizerSessionLedger(session=CapitalizerSession.NEW_YORK),
    )


def test_world_model_requires_all_nine_markets_and_derives_exposure() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    markets = _markets(
        at,
        overrides={
            "USDJPY": (
                CapitalizerAttentionState.POSITION,
                CapitalizerKnowledgeState.KNOWN,
            )
        },
    )
    world = CapitalizerGlobalWorldModel(
        observed_at=at,
        current_session=CapitalizerSession.ASIA,
        session_brain=CapitalizerSessionBrainState(
            session=CapitalizerSession.ASIA,
            phase=CapitalizerSessionPhase.ACTIVE,
        ),
        markets=markets,
        session_ledgers=_ledgers(asia_executions=1),
        journey=CapitalizerDailyJourney(),
        loss_memory=CapitalizerLossMemory(),
        open_positions=(
            CapitalizerWorldPosition(
                symbol="USDJPY",
                side=CapitalizerSide.LONG,
                risk_r=Decimal("1"),
                session=CapitalizerSession.ASIA,
                hypothesis_id="H-USDJPY",
                source_event_id="SRC-USDJPY",
                opened_at=at,
            ),
        ),
    )

    assert len(world.markets) == 9
    assert world.execution_slots_remaining == 2
    assert world.position_symbols == ("USDJPY",)
    exposures = {item.factor: item.net_r for item in world.factor_exposure_state}
    assert exposures["USD"] == Decimal("1")
    assert exposures["JPY"] == Decimal("-1")


def test_world_model_rejects_future_market_brain_state() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    markets = list(_markets(at))
    markets[0] = replace(
        markets[0],
        brain=replace(
            markets[0].brain,
            microstructure=CapitalizerMicrostructureTrace(
                decision_at=at + timedelta(seconds=1),
                events=(),
            ),
        ),
    )

    with pytest.raises(ValueError, match="future Market Brain"):
        CapitalizerGlobalWorldModel(
            observed_at=at,
            current_session=CapitalizerSession.ASIA,
            session_brain=CapitalizerSessionBrainState(
                session=CapitalizerSession.ASIA,
                phase=CapitalizerSessionPhase.ACTIVE,
            ),
            markets=tuple(markets),
            session_ledgers=_ledgers(),
            journey=CapitalizerDailyJourney(),
            loss_memory=CapitalizerLossMemory(),
        )


def test_world_model_rejects_cross_session_position_roll() -> None:
    at = datetime(2026, 1, 5, 8, 0, tzinfo=UTC)
    markets = _markets(
        at,
        overrides={
            "USDJPY": (
                CapitalizerAttentionState.POSITION,
                CapitalizerKnowledgeState.KNOWN,
            )
        },
    )

    with pytest.raises(ValueError, match="cannot roll across sessions"):
        CapitalizerGlobalWorldModel(
            observed_at=at,
            current_session=CapitalizerSession.LONDON,
            session_brain=CapitalizerSessionBrainState(
                session=CapitalizerSession.LONDON,
                phase=CapitalizerSessionPhase.ACTIVE,
            ),
            markets=markets,
            session_ledgers=_ledgers(),
            journey=CapitalizerDailyJourney(
                completed_sessions=(CapitalizerSession.ASIA,)
            ),
            loss_memory=CapitalizerLossMemory(),
            open_positions=(
                CapitalizerWorldPosition(
                    symbol="USDJPY",
                    side=CapitalizerSide.LONG,
                    risk_r=Decimal("1"),
                    session=CapitalizerSession.ASIA,
                    hypothesis_id="H-USDJPY",
                    source_event_id="SRC-USDJPY",
                    opened_at=at - timedelta(hours=1),
                ),
            ),
        )


def test_master_brain_sees_competing_decisions_and_slot_pressure() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    markets = _markets(
        at,
        overrides={
            "AUDJPY": (
                CapitalizerAttentionState.DECISION,
                CapitalizerKnowledgeState.KNOWN,
            ),
            "USDJPY": (
                CapitalizerAttentionState.DECISION,
                CapitalizerKnowledgeState.PARTIAL,
            ),
        },
    )
    world = CapitalizerGlobalWorldModel(
        observed_at=at,
        current_session=CapitalizerSession.ASIA,
        session_brain=CapitalizerSessionBrainState(
            session=CapitalizerSession.ASIA,
            phase=CapitalizerSessionPhase.ACTIVE,
        ),
        markets=markets,
        session_ledgers=_ledgers(asia_executions=2),
        journey=CapitalizerDailyJourney(),
        loss_memory=CapitalizerLossMemory(),
    )

    assessment = assess_master_brain(world)

    assert assessment.execution_slots_remaining == 1
    assert assessment.decision_symbols == ("AUDJPY", "USDJPY")
    assert "USDJPY" in assessment.partial_symbols
    assert "DECISION_DEMAND_EXCEEDS_AVAILABLE_SLOTS" in assessment.causal_warnings
    assert assessment.ranks_opportunities is False
    assert assessment.grants_capital_authority is False
