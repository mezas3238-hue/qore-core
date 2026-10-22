"""Research-only five-market cognitive orchestration regression tests.

Synthetic situations only: these are not strategy signals or economic replays.
"""
import json
from dataclasses import fields
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    EXPANSION_MARKETS,
)
from qore.infrastructure.traders.vt08_cognitive_5m_research_scope import (
    CAUSAL_FIELDS,
    MEMORY_STATE,
    RESEARCH_MARKETS,
    Vt08FiveMarketResearchSituation,
    research_cognitive_memory_fingerprint,
    research_market_anchor_context,
    research_strategy_identity_fingerprint,
)
from qore.infrastructure.traders.vt08_cognitive_memory import (
    cognitive_memory_fingerprint,
    validate_cognitive_memory,
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
        "feature_cutoffs": tuple((name, AS_OF) for name in CAUSAL_FIELDS),
        "source_cycle_id": "synthetic-h4-cycle-09",
        "cycle_expires_at": AS_OF + timedelta(hours=4),
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


@pytest.mark.parametrize("market", RESEARCH_MARKETS)
@pytest.mark.parametrize("anchor", (1, 5, 9))
def test_all_market_anchor_memories_are_bounded_unknown_not_pnl_gate(
    market: str, anchor: int
) -> None:
    value = research_market_anchor_context(market, anchor)
    assert value["cibo_market_prior_state"] == MEMORY_STATE
    assert value["trader_experience_state"] == MEMORY_STATE
    assert value["market_memory_version"] is None
    assert value["experience_memory_version"] is None
    assert value["execution_gate_from_pnl"] is False
    assert value["operational_authority"] is False
    assert research_market_anchor_context(market, anchor) == value


def test_research_memory_and_identity_not_misrepresented_as_legacy_memory() -> None:
    validate_cognitive_memory()
    assert research_cognitive_memory_fingerprint() != cognitive_memory_fingerprint()
    assert len(research_strategy_identity_fingerprint()) == 64
    assert len(research_cognitive_memory_fingerprint()) == 64


def test_research_envelope_rejects_missing_duplicate_and_unknown_features() -> None:
    cutoffs = tuple((field, AS_OF) for field in CAUSAL_FIELDS)
    with pytest.raises(ValueError, match="complete feature"):
        _situation(feature_cutoffs=cutoffs[:-1])
    with pytest.raises(ValueError, match="duplicate or unordered"):
        _situation(feature_cutoffs=(cutoffs[1], cutoffs[0], *cutoffs[2:]))
    with pytest.raises(ValueError, match="unknown feature"):
        _situation(feature_cutoffs=(("pnl_future", AS_OF), *cutoffs[1:]))
    with pytest.raises(ValueError, match="immutable"):
        _situation(feature_cutoffs=list(cutoffs))


@pytest.mark.parametrize("feature", CAUSAL_FIELDS)
def test_research_envelope_rejects_each_future_feature(feature: str) -> None:
    future = AS_OF + timedelta(minutes=1)
    feature_cutoffs = tuple(
        (field, future if field == feature else AS_OF)
        for field in CAUSAL_FIELDS
    )
    with pytest.raises(ValueError, match="future information"):
        _situation(feature_cutoffs=feature_cutoffs)


def test_research_envelope_rejects_inconsistent_latest_bar_and_naive_proof() -> None:
    lagging = tuple(
        (field, AS_OF - timedelta(minutes=1)) for field in CAUSAL_FIELDS
    )
    with pytest.raises(ValueError, match="maximum feature cutoff"):
        _situation(feature_cutoffs=lagging, latest_available_bar_close=AS_OF)
    malformed = tuple(
        (field, AS_OF.replace(tzinfo=None) if i == 3 else AS_OF)
        for i, field in enumerate(CAUSAL_FIELDS)
    )
    with pytest.raises(ValueError, match="feature cutoff must be timezone-aware"):
        _situation(feature_cutoffs=malformed)


def test_research_payload_is_json_safe_and_every_provenance_byte_is_hashed() -> None:
    first = _situation()
    json.dumps(first.payload(), sort_keys=True)
    assert len(first.fingerprint()) == 64
    changed = tuple(
        (field, AS_OF - timedelta(minutes=1) if i == 0 else AS_OF)
        for i, field in enumerate(CAUSAL_FIELDS)
    )
    revised = _situation(feature_cutoffs=changed)
    assert first.fingerprint() != revised.fingerprint()
    assert first.payload()["schema"].startswith("qore.vt08.cognitive_5m.")
    assert revised.payload()["feature_cutoffs"][0][1] != (
        first.payload()["feature_cutoffs"][0][1]
    )


def test_research_requires_source_cycle_and_timezone_bound() -> None:
    with pytest.raises(ValueError, match="cycle id"):
        _situation(source_cycle_id="")
    with pytest.raises(ValueError, match="cycle expiry"):
        _situation(cycle_expires_at=None)
    with pytest.raises(ValueError, match="cycle expiry"):
        _situation(cycle_expires_at=AS_OF.replace(tzinfo=None))


@pytest.mark.parametrize(
    ("state", "expected_action"),
    (
        ("INVALID", Vt08CognitiveAction.ABSTAIN),
        ("UNKNOWN", Vt08CognitiveAction.WAIT),
    ),
)
def test_risk_geometry_does_not_execute_if_not_valid(
    state: str, expected_action: Vt08CognitiveAction
) -> None:
    outcome = evaluate_cognitive_hypothesis(
        situation=_situation(risk_geometry_state=state),
        source_fingerprint=f"synthetic-risk-{state}",
    )
    assert outcome.decision.action is expected_action
