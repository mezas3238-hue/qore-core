"""Research-only five-market cognitive orchestration regression tests.

Synthetic situations only: these are not strategy signals or economic replays.
"""
from dataclasses import fields
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    EXPANSION_MARKETS,
)
from qore.infrastructure.traders.vt08_cognitive_5m_research_scope import (
    MEMORY_STATE,
    RESEARCH_MARKETS,
    Vt08FiveMarketResearchSituation,
    research_market_anchor_context,
)
from qore.infrastructure.traders.vt08_cognitive_orchestrator import (
    evaluate_cognitive_hypothesis,
    evaluate_in_trade_cognition,
)
from qore.infrastructure.traders.vt08_cognitive_position_intelligence import (
    Vt08PositionSnapshot,
)
from qore.infrastructure.traders.vt08_cognitive_situation_model import (
    Vt08ForexSituationModel,
)
from qore.infrastructure.traders.vt08_cognitive_v1_contracts import (
    Vt08CognitiveAction,
    Vt08HypothesisState,
    Vt08KnowledgeState,
    Vt08PositionAction,
)

AS_OF = datetime(2026, 9, 23, 13, 15, tzinfo=UTC)


def _research_payload(market: str = "EURJPY") -> dict[str, object]:
    return {
        "as_of": AS_OF,
        "market": market,
        "anchor_hour_ny": 9,
        "side": "long",
        "ltf_profile": "M3_FRACTAL",
        "methodology_valid": True,
        "source_identity_complete": True,
        "h4_lifecycle_valid": True,
        "bias_state": "RESOLVED",
        "scenario_state": "C2",
        "poi_state": "CONFIRMED",
        "protected_swing_state": "CONFIRMED",
        "cisd_state": "CONFIRMED",
        "displacement_state": "CONFIRMED",
        "entry_state": "ACTIONABLE",
        "entry_freshness_state": "CURRENT",
        "liquidity_state": "OBSERVED",
        "range_state": "KNOWN",
        "volatility_state": "KNOWN",
        "journey_stage": "PRE_ENTRY",
        "structural_destination_state": "SUPPORTED",
        "exhaustion_state": "NOT_OBSERVED",
        "risk_geometry_state": "VALID",
        "position_state": "FLAT",
        "supporting_evidence": ("SOURCE:CISD_CONFIRMED", "SOURCE:PS_CONFIRMED"),
        "source_evidence_id": "synthetic-fixture-v1",
        "latest_available_bar_close": AS_OF,
        "research_only": True,
        "operational_authority": False,
    }


def _situation(
    market: str = "EURJPY", **overrides: object
) -> Vt08FiveMarketResearchSituation:
    data = _research_payload(market)
    data.update(overrides)
    return Vt08FiveMarketResearchSituation(**data)  # type: ignore[arg-type]


def test_five_market_scope_is_exactly_expansion_not_production() -> None:
    assert RESEARCH_MARKETS == EXPANSION_MARKETS
    names = {f.name for f in fields(Vt08ForexSituationModel)}
    base = {k: v for k, v in _research_payload().items() if k in names}
    with pytest.raises(ValueError, match="outside Forex authority"):
        Vt08ForexSituationModel(**base)  # type: ignore[arg-type]


@pytest.mark.parametrize("market", RESEARCH_MARKETS)
def test_research_five_markets_use_actual_sovereign_orchestrator(market: str) -> None:
    situation = _situation(market)
    context = research_market_anchor_context(market, 9)
    result = evaluate_cognitive_hypothesis(
        situation=situation, source_fingerprint=f"synthetic-source-{market}"
    )
    assert result.decision.action is Vt08CognitiveAction.EXECUTE
    assert result.hypothesis.state is Vt08HypothesisState.EXECUTABLE
    assert result.decision.metacognition.state is Vt08KnowledgeState.SUPPORTED
    assert result.decision.market_anchor_context_fingerprint == context["fingerprint"]
    assert len(result.decision.cognitive_memory_fingerprint) == 64
    assert situation.payload()["research_only"] is True
    assert context["cibo_market_prior_state"] == MEMORY_STATE
    assert context["trader_experience_state"] == MEMORY_STATE
    assert context["operational_authority"] is False
    assert not context["execution_gate_from_pnl"]


def test_unknown_metacognition_cannot_execute_even_if_geometry_complete() -> None:
    outcome = evaluate_cognitive_hypothesis(
        situation=_situation(supporting_evidence=()), source_fingerprint="no-evidence"
    )
    assert outcome.decision.metacognition.state is Vt08KnowledgeState.UNKNOWN
    assert outcome.decision.action is Vt08CognitiveAction.WAIT
    assert outcome.hypothesis.state is Vt08HypothesisState.WAITING
    assert "REASONING:NO_EXECUTION_SUPPORT_EVIDENCE" in (
        outcome.decision.reason_codes
    )


def test_source_kill_cannot_fallback_to_execution() -> None:
    invalid = evaluate_cognitive_hypothesis(
        situation=_situation(material_contradictions=("SOURCE:INVALIDATED",)),
        source_fingerprint="same-event",
    )
    assert invalid.decision.action is Vt08CognitiveAction.ABSTAIN
    assert invalid.hypothesis.state is Vt08HypothesisState.KILLED
    with pytest.raises(ValueError, match="cannot be resurrected"):
        evaluate_cognitive_hypothesis(
            situation=_situation(),
            source_fingerprint="same-event",
            hypothesis=invalid.hypothesis,
        )


def test_wait_preserves_source_identity_when_confirmation_arrives() -> None:
    first = evaluate_cognitive_hypothesis(
        situation=_situation(cisd_state="PENDING"),
        source_fingerprint="persistent-event",
    )
    assert first.decision.action is Vt08CognitiveAction.WAIT
    second = evaluate_cognitive_hypothesis(
        situation=_situation(),
        source_fingerprint="persistent-event",
        hypothesis=first.hypothesis,
    )
    assert second.decision.action is Vt08CognitiveAction.EXECUTE


def test_reject_future_bars_and_unbounded_market_or_anchor() -> None:
    with pytest.raises(ValueError, match="future bars"):
        _situation(latest_available_bar_close=AS_OF + timedelta(minutes=3))
    with pytest.raises(ValueError, match="source evidence"):
        _situation(source_evidence_id="")
    with pytest.raises(ValueError, match="five-market scope"):
        _situation("GBPJPY")
    with pytest.raises(ValueError, match="research-only"):
        _situation(research_only=False)
    with pytest.raises(ValueError, match="research-only"):
        _situation(operational_authority=True)
    with pytest.raises(ValueError, match="Owner"):
        research_market_anchor_context("EURJPY", 13)


@pytest.mark.parametrize("market", RESEARCH_MARKETS)
def test_all_five_markets_reach_in_trade_journey_and_position(market: str) -> None:
    situation = _situation(
        market,
        entry_state="FILLED",
        position_state="OPEN",
        journey_stage="IN_TRADE",
        structural_destination_state="APPROACHING",
    )
    position = Vt08PositionSnapshot(
        as_of=AS_OF,
        side="long",
        entry_price=Decimal("100"),
        current_price=Decimal("101"),
        initial_stop=Decimal("99"),
        current_stop=Decimal("99"),
        bound_destination=Decimal("103"),
    )
    decision = evaluate_in_trade_cognition(situation=situation, position=position)
    context = research_market_anchor_context(market, 9)
    assert decision.journey.market_anchor_context_fingerprint == context["fingerprint"]
    assert decision.position_decision.action is Vt08PositionAction.HOLD
    assert not decision.position_decision.execution_authorized
    assert len(decision.position_decision.fingerprint()) == 64
