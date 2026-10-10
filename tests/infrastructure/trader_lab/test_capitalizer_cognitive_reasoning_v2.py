from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_cognitive_audit import (
    CapitalizerCognitiveAuditLedger,
    CapitalizerCognitiveAuditRecord,
)
from qore.infrastructure.trader_lab.capitalizer_confidence import (
    CapitalizerKnowledgeState,
)
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
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_global_world_model import (
    CapitalizerGlobalWorldModel,
    CapitalizerMarketWorldState,
    CapitalizerWorldPosition,
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
from qore.infrastructure.trader_lab.capitalizer_opportunity_competition import (
    build_opportunity_competition_state,
)
from qore.infrastructure.trader_lab.capitalizer_portfolio_position_supervisor import (
    assess_portfolio_positions,
)
from qore.infrastructure.trader_lab.capitalizer_regime_intelligence import (
    CapitalizerRegimeHypothesis,
    CapitalizerRegimeResolution,
    assess_regime,
)


def _market_worlds(
    at: datetime,
    overrides: dict[
        str,
        tuple[
            CapitalizerAttentionState,
            CapitalizerKnowledgeState,
            CapitalizerHypothesisStage | None,
        ],
    ],
) -> tuple[CapitalizerMarketWorldState, ...]:
    rows: list[CapitalizerMarketWorldState] = []
    for session in CapitalizerSession:
        for symbol in sorted(allowed_markets(session)):
            attention, knowledge, stage = overrides.get(
                symbol,
                (
                    CapitalizerAttentionState.BACKGROUND,
                    CapitalizerKnowledgeState.KNOWN,
                    None,
                ),
            )
            rows.append(
                CapitalizerMarketWorldState(
                    brain=CapitalizerMarketBrainState(
                        symbol=symbol,
                        session=session,
                        state_family_id="STATE",
                        microstructure=CapitalizerMicrostructureTrace(
                            decision_at=at,
                            events=(),
                        ),
                    ),
                    attention=attention,
                    knowledge=knowledge,
                    hypothesis_stage=stage,
                    hypothesis_id=f"H-{symbol}" if stage is not None else None,
                    source_event_id=f"SRC-{symbol}" if stage is not None else None,
                )
            )
    return tuple(rows)


def _ledgers(
    *,
    asia: int = 0,
    london: int = 0,
) -> tuple[CapitalizerSessionLedger, ...]:
    return (
        CapitalizerSessionLedger(CapitalizerSession.ASIA, executions=asia),
        CapitalizerSessionLedger(CapitalizerSession.LONDON, executions=london),
        CapitalizerSessionLedger(CapitalizerSession.NEW_YORK),
    )


def test_regime_intelligence_can_admit_unknown_and_conflicted_states() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    unknown = assess_regime(
        CapitalizerRegimeHypothesis(
            symbol="USDJPY",
            observed_at=at,
            family_id=None,
            causal_evidence=(),
            contradictions=(),
            knowledge=CapitalizerKnowledgeState.UNKNOWN,
        )
    )
    supported = assess_regime(
        CapitalizerRegimeHypothesis(
            symbol="USDJPY",
            observed_at=at,
            family_id="RESEARCH_EXPANSION_FAMILY",
            causal_evidence=("COMPRESSION_PRECEDED_BREAK", "DISPLACEMENT_PRESENT"),
            contradictions=(),
            knowledge=CapitalizerKnowledgeState.KNOWN,
        )
    )
    conflicted = assess_regime(
        CapitalizerRegimeHypothesis(
            symbol="USDJPY",
            observed_at=at,
            family_id="RESEARCH_EXPANSION_FAMILY",
            causal_evidence=("DISPLACEMENT_PRESENT",),
            contradictions=("OPPOSITE_ACCEPTANCE",),
            knowledge=CapitalizerKnowledgeState.CONFLICTED,
        )
    )

    assert unknown.resolution is CapitalizerRegimeResolution.UNRESOLVED
    assert supported.resolution is CapitalizerRegimeResolution.SUPPORTED
    assert conflicted.resolution is CapitalizerRegimeResolution.CONFLICTED
    assert supported.grants_entry_authority is False


def test_opportunity_competition_detects_slot_pressure_without_picking_winner() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    world = CapitalizerGlobalWorldModel(
        observed_at=at,
        current_session=CapitalizerSession.ASIA,
        session_brain=CapitalizerSessionBrainState(
            session=CapitalizerSession.ASIA,
            phase=CapitalizerSessionPhase.ACTIVE,
        ),
        markets=_market_worlds(
            at,
            {
                "AUDJPY": (
                    CapitalizerAttentionState.DECISION,
                    CapitalizerKnowledgeState.KNOWN,
                    CapitalizerHypothesisStage.EXECUTABLE,
                ),
                "USDJPY": (
                    CapitalizerAttentionState.DECISION,
                    CapitalizerKnowledgeState.KNOWN,
                    CapitalizerHypothesisStage.EXECUTABLE,
                ),
                "EURUSD": (
                    CapitalizerAttentionState.DECISION,
                    CapitalizerKnowledgeState.KNOWN,
                    CapitalizerHypothesisStage.EXECUTABLE,
                ),
            },
        ),
        session_ledgers=_ledgers(asia=2),
        journey=CapitalizerDailyJourney(),
        loss_memory=CapitalizerLossMemory(),
    )

    competition = build_opportunity_competition_state(world)

    assert tuple(item.symbol for item in competition.eligible_candidates) == (
        "AUDJPY",
        "USDJPY",
    )
    assert competition.available_slots == 1
    assert competition.arbitration_required is True
    assert "EURUSD" in competition.blocked_symbols
    assert competition.winner_selected is False
    assert competition.outcome_aware_ranking_used is False


def test_portfolio_supervisor_exposes_shared_factor_without_managing_trade() -> None:
    at = datetime(2026, 1, 5, 8, 0, tzinfo=UTC)
    markets = _market_worlds(
        at,
        {
            "EURUSD": (
                CapitalizerAttentionState.POSITION,
                CapitalizerKnowledgeState.KNOWN,
                CapitalizerHypothesisStage.POSITION_ACTIVE,
            ),
            "GBPUSD": (
                CapitalizerAttentionState.POSITION,
                CapitalizerKnowledgeState.KNOWN,
                CapitalizerHypothesisStage.THESIS_STABLE,
            ),
        },
    )
    world = CapitalizerGlobalWorldModel(
        observed_at=at,
        current_session=CapitalizerSession.LONDON,
        session_brain=CapitalizerSessionBrainState(
            session=CapitalizerSession.LONDON,
            phase=CapitalizerSessionPhase.ACTIVE,
        ),
        markets=markets,
        session_ledgers=_ledgers(london=2),
        journey=CapitalizerDailyJourney(
            completed_sessions=(CapitalizerSession.ASIA,)
        ),
        loss_memory=CapitalizerLossMemory(),
        open_positions=(
            CapitalizerWorldPosition(
                symbol="EURUSD",
                side=CapitalizerSide.LONG,
                risk_r=Decimal("1"),
                session=CapitalizerSession.LONDON,
                hypothesis_id="H-EURUSD",
                source_event_id="SRC-EURUSD",
                opened_at=at,
            ),
            CapitalizerWorldPosition(
                symbol="GBPUSD",
                side=CapitalizerSide.LONG,
                risk_r=Decimal("1"),
                session=CapitalizerSession.LONDON,
                hypothesis_id="H-GBPUSD",
                source_event_id="SRC-GBPUSD",
                opened_at=at,
            ),
        ),
    )

    assessment = assess_portfolio_positions(world)

    usd = next(group for group in assessment.shared_factor_groups if group.factor == "USD")
    assert usd.symbols == ("EURUSD", "GBPUSD")
    assert usd.gross_r == Decimal("2")
    assert assessment.review_required is True
    assert assessment.stop_widening_allowed is False
    assert assessment.grants_capital_authority is False


def test_cognitive_audit_requires_a_causal_why_and_is_chronological() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="requires causal reasons"):
        CapitalizerCognitiveAuditRecord(
            audit_id="A-INVALID",
            observed_at=at,
            session=CapitalizerSession.ASIA,
            symbol="USDJPY",
            attention=CapitalizerAttentionState.DECISION,
            knowledge=CapitalizerKnowledgeState.KNOWN,
            hypothesis_stage=CapitalizerHypothesisStage.EXECUTABLE,
            hypothesis_id="H-1",
            source_event_id="SRC-1",
            regime_family_id=None,
            observations=("LIQUIDITY_EVENT",),
            contradictions=(),
            adversarial_findings=(),
            decision=CapitalizerDecision.EXECUTE,
            reasons=(),
        )

    first = CapitalizerCognitiveAuditRecord(
        audit_id="A-1",
        observed_at=at,
        session=CapitalizerSession.ASIA,
        symbol="USDJPY",
        attention=CapitalizerAttentionState.DECISION,
        knowledge=CapitalizerKnowledgeState.KNOWN,
        hypothesis_stage=CapitalizerHypothesisStage.EXECUTABLE,
        hypothesis_id="H-1",
        source_event_id="SRC-1",
        regime_family_id="RESEARCH_STATE",
        observations=("LIQUIDITY_EVENT", "DISPLACEMENT"),
        contradictions=(),
        adversarial_findings=("COUNTERFACTUAL_CHECK_PASSED",),
        decision=CapitalizerDecision.EXECUTE,
        reasons=("CAUSAL_THESIS_PASSED",),
        selected_for_slot=True,
    )
    ledger = CapitalizerCognitiveAuditLedger().append(first)
    assert ledger.records == (first,)

    earlier = CapitalizerCognitiveAuditRecord(
        audit_id="A-0",
        observed_at=at - timedelta(seconds=1),
        session=CapitalizerSession.ASIA,
        symbol="AUDJPY",
        attention=CapitalizerAttentionState.WATCH,
        knowledge=CapitalizerKnowledgeState.PARTIAL,
        hypothesis_stage=None,
        hypothesis_id=None,
        source_event_id=None,
        regime_family_id=None,
        observations=("EVENT_WATCH",),
        contradictions=(),
        adversarial_findings=(),
        decision=None,
        reasons=(),
    )
    with pytest.raises(ValueError, match="backward in time"):
        ledger.append(earlier)
