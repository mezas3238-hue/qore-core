"""Synthetic event-driven proof of VT08 5M cognitive admission and tracing.

No price-path economic replay and no historical source-entry authority is claimed.
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_cognitive_5m_consumed_gate_v1 import (
    Vt08FiveMarketCognitiveGate,
)
from qore.infrastructure.traders.vt08_cognitive_5m_research_scope import (
    CAUSAL_FIELDS,
    Vt08FiveMarketResearchSituation,
)
from qore.infrastructure.traders.vt08_cognitive_position_intelligence import (
    Vt08PositionSnapshot,
)
from qore.infrastructure.traders.vt08_cognitive_v1_contracts import (
    Vt08CognitiveAction,
    Vt08KnowledgeState,
    Vt08PositionAction,
)

T0 = datetime(2026, 9, 23, 13, 15, tzinfo=UTC)


def _snapshot(
    source: str = "synthetic-source-01",
    when: datetime = T0,
    market: str = "EURJPY",
    **overrides: object,
) -> Vt08FiveMarketResearchSituation:
    fields: dict[str, object] = {
        "as_of": when,
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
        "supporting_evidence": ("SOURCE:CISD", "SOURCE:PS"),
        "source_evidence_id": source,
        "latest_available_bar_close": when,
        "feature_cutoffs": tuple((name, when) for name in CAUSAL_FIELDS),
        "source_cycle_id": "synthetic-h4-cycle-09",
        "cycle_expires_at": T0 + timedelta(hours=4),
        "research_only": True,
        "operational_authority": False,
    }
    fields.update(overrides)
    return Vt08FiveMarketResearchSituation(**fields)  # type: ignore[arg-type]


def _position(when: datetime) -> Vt08PositionSnapshot:
    return Vt08PositionSnapshot(
        as_of=when,
        side="long",
        entry_price=Decimal("100"),
        current_price=Decimal("101"),
        initial_stop=Decimal("99"),
        current_stop=Decimal("99"),
        bound_destination=Decimal("103"),
    )


def test_wait_remains_alive_and_can_advance_to_execution() -> None:
    gate = Vt08FiveMarketCognitiveGate()
    first = gate.evaluate(_snapshot(cisd_state="PENDING"))
    assert first.action is Vt08CognitiveAction.WAIT
    second = gate.evaluate(_snapshot(when=T0 + timedelta(minutes=3)))
    assert second.action is Vt08CognitiveAction.EXECUTE
    assert len(gate.decisions) == 2
    assert all(
        trace.research_only and not trace.broker_order_authorized
        for trace in gate.decisions
    )
    assert all(len(trace.memory_fingerprint) == 64 for trace in gate.decisions)
    assert all(len(trace.decision_fingerprint) == 64 for trace in gate.decisions)
    with pytest.raises(ValueError, match="only once"):
        gate.evaluate(_snapshot(when=T0 + timedelta(minutes=6)))


def test_abstain_kills_source_and_no_fallback() -> None:
    gate = Vt08FiveMarketCognitiveGate()
    first = gate.evaluate(
        _snapshot(material_contradictions=("SOURCE:INVALID",))
    )
    assert first.action is Vt08CognitiveAction.ABSTAIN
    with pytest.raises(ValueError, match="cannot be resurrected"):
        gate.evaluate(_snapshot(when=T0 + timedelta(minutes=3)))
    assert len(gate.decisions) == 1
    valid_new_event = gate.evaluate(_snapshot(source="genuinely-new-source"))
    assert valid_new_event.action is Vt08CognitiveAction.EXECUTE


def test_reject_timestamp_regression_and_cross_market_fingerprint() -> None:
    gate = Vt08FiveMarketCognitiveGate()
    gate.evaluate(_snapshot(cisd_state="PENDING"))
    with pytest.raises(ValueError, match="timestamp must advance"):
        gate.evaluate(_snapshot(cisd_state="PENDING"))
    with pytest.raises(ValueError, match="cannot drift"):
        gate.evaluate(_snapshot(market="CADJPY", when=T0 + timedelta(minutes=3)))


def test_position_cognition_requires_admitted_source_and_causal_timestamps() -> None:
    gate = Vt08FiveMarketCognitiveGate()
    later = T0 + timedelta(minutes=3)
    pos = _position(later)
    filled = _snapshot(
        when=later,
        entry_state="FILLED",
        position_state="OPEN",
        journey_stage="IN_TRADE",
    )
    with pytest.raises(ValueError, match="unadmitted"):
        gate.evaluate_position(filled, pos)
    gate.evaluate(_snapshot())
    with pytest.raises(ValueError, match="as_of must match"):
        gate.evaluate_position(filled, _position(T0))
    actual = gate.evaluate_position(filled, pos)
    assert actual.action is Vt08PositionAction.HOLD
    assert actual.research_only and not actual.broker_order_authorized
    assert len(actual.journey_fingerprint) == 64
    assert len(actual.position_fingerprint) == 64
    with pytest.raises(ValueError, match="timestamp must advance"):
        gate.evaluate_position(filled, pos)
    assert len(gate.positions) == 1


def test_deterministic_immutable_decision_ledger() -> None:
    left = Vt08FiveMarketCognitiveGate()
    right = Vt08FiveMarketCognitiveGate()
    for gate in (left, right):
        gate.evaluate(_snapshot(market="USDCAD"))
        gate.evaluate_position(
            _snapshot(
                market="USDCAD",
                when=T0 + timedelta(minutes=3),
                entry_state="FILLED",
                position_state="OPEN",
            ),
            _position(T0 + timedelta(minutes=3)),
        )
    assert left.decisions == right.decisions
    assert left.positions == right.positions


@pytest.mark.parametrize(
    "overrides",
    (
        {"side": "short"},
        {"anchor_hour_ny": 5},
        {"ltf_profile": "M5_FRACTAL"},
        {"source_cycle_id": "different-h4"},
        {"cycle_expires_at": T0 + timedelta(hours=8)},
    ),
)
def test_event_identity_drift_of_side_anchor_profile_cycle_fails_closed(
    overrides: dict[str, object]
) -> None:
    gate = Vt08FiveMarketCognitiveGate()
    gate.evaluate(_snapshot(cisd_state="PENDING"))
    with pytest.raises(ValueError, match="identity cannot drift"):
        gate.evaluate(_snapshot(when=T0 + timedelta(minutes=3), **overrides))


def test_wait_event_expires_at_h4_boundary_without_late_execution() -> None:
    gate = Vt08FiveMarketCognitiveGate()
    original = gate.evaluate(_snapshot(cisd_state="PENDING"))
    assert original.action is Vt08CognitiveAction.WAIT
    with pytest.raises(ValueError, match="expired at H4"):
        gate.evaluate(_snapshot(when=T0 + timedelta(hours=4)))
    assert len(gate.decisions) == 1
    assert gate.evaluate(
        _snapshot(
            source="new-cycle-distinct-source",
            when=T0 + timedelta(hours=4),
            source_cycle_id="next-h4",
            cycle_expires_at=T0 + timedelta(hours=8),
        )
    ).action is Vt08CognitiveAction.EXECUTE


def test_source_id_cannot_be_reused_across_new_york_date() -> None:
    gate = Vt08FiveMarketCognitiveGate()
    gate.evaluate(_snapshot(cisd_state="PENDING"))
    tomorrow = T0 + timedelta(days=1)
    with pytest.raises(ValueError, match="identity cannot drift"):
        gate.evaluate(
            _snapshot(
                when=tomorrow,
                cycle_expires_at=tomorrow + timedelta(hours=4),
            )
        )


@pytest.mark.parametrize(
    ("entry_state", "position_state", "expected"),
    (
        ("ACTIONABLE", "OPEN", "filled entry"),
        ("FILLED", "FLAT", "open position"),
        ("FILLED", "CLOSED", "open position"),
    ),
)
def test_position_requires_actual_open_filled_source_state(
    entry_state: str, position_state: str, expected: str
) -> None:
    gate = Vt08FiveMarketCognitiveGate()
    gate.evaluate(_snapshot())
    later = T0 + timedelta(minutes=3)
    with pytest.raises(ValueError, match=expected):
        gate.evaluate_position(
            _snapshot(
                when=later,
                entry_state=entry_state,
                position_state=position_state,
            ),
            _position(later),
        )


def test_position_refuses_unauthorized_side_change_and_old_candle() -> None:
    gate = Vt08FiveMarketCognitiveGate()
    gate.evaluate(_snapshot())
    with pytest.raises(ValueError, match="post-admission"):
        gate.evaluate_position(
            _snapshot(entry_state="FILLED", position_state="OPEN"),
            _position(T0),
        )
    later = T0 + timedelta(minutes=3)
    with pytest.raises(ValueError, match="identity cannot drift"):
        gate.evaluate_position(
            _snapshot(
                when=later,
                side="short",
                entry_state="FILLED",
                position_state="OPEN",
            ),
            _position(later),
        )


def test_every_sovereign_decision_component_is_in_auditable_trace() -> None:
    gate = Vt08FiveMarketCognitiveGate()
    supported = gate.evaluate(_snapshot())
    assert supported.metacognitive_state is Vt08KnowledgeState.SUPPORTED
    assert supported.supporting_evidence == ("SOURCE:CISD", "SOURCE:PS")
    assert supported.adversarial_challenges == ()
    assert supported.adversarial_unknowns == ()
    assert len(supported.memory_fingerprint) == 64
    assert len(supported.market_context_fingerprint) == 64
    assert len(supported.strategy_identity_fingerprint) == 64

    unknown = gate.evaluate(
        _snapshot(
            source="different-source-unknown",
            supporting_evidence=(),
        )
    )
    assert unknown.action is Vt08CognitiveAction.WAIT
    assert unknown.metacognitive_state is Vt08KnowledgeState.UNKNOWN
    assert unknown.supporting_evidence == ()

    disputed = gate.evaluate(
        _snapshot(
            source="different-source-contradicted",
            material_contradictions=("SOURCE:THESIS_INVALID",),
        )
    )
    assert disputed.action is Vt08CognitiveAction.ABSTAIN
    assert disputed.metacognitive_state is Vt08KnowledgeState.CONTRADICTED
    assert disputed.adversarial_challenges == ("SOURCE:THESIS_INVALID",)


def test_no_cross_market_event_clock_regression() -> None:
    gate = Vt08FiveMarketCognitiveGate()
    later = T0 + timedelta(minutes=3)
    gate.evaluate(_snapshot(source="A", market="EURJPY", when=later))
    with pytest.raises(ValueError, match="global replay clock"):
        gate.evaluate(_snapshot(source="B", market="CADJPY", when=T0))
    assert gate.evaluate(
        _snapshot(source="B", market="CADJPY", when=later)
    ).action is Vt08CognitiveAction.EXECUTE


def test_position_trace_exposes_journey_destination_and_management_provenance() -> None:
    gate = Vt08FiveMarketCognitiveGate()
    gate.evaluate(_snapshot())
    later = T0 + timedelta(minutes=3)
    state = gate.evaluate_position(
        _snapshot(
            when=later,
            entry_state="FILLED",
            position_state="OPEN",
            journey_stage="IN_TRADE",
            structural_destination_state="APPROACHING",
        ),
        _position(later),
    )
    assert state.journey_state == "ADVANCING"
    assert state.destination_state == "APPROACHING"
    assert state.action is Vt08PositionAction.HOLD
    assert state.next_stop is None
    assert state.policy_calibrated is False
    assert not state.broker_order_authorized


def test_h4_expiry_position_has_an_explicit_cognitive_exit_proposal() -> None:
    gate = Vt08FiveMarketCognitiveGate()
    gate.evaluate(_snapshot())
    at_expiry = T0 + timedelta(hours=4)
    outcome = gate.evaluate_position(
        _snapshot(
            when=at_expiry,
            entry_state="FILLED",
            position_state="OPEN",
            journey_stage="IN_TRADE",
            h4_lifecycle_valid=False,
        ),
        _position(at_expiry),
    )
    assert outcome.action is Vt08PositionAction.EXIT
    assert "POSITION:EXIT_H4_LIFECYCLE_END" in outcome.reason_codes
    assert outcome.journey_state == "INVALIDATED"
    assert outcome.research_only
    assert not outcome.broker_order_authorized


def test_full_five_market_stream_every_admission_gets_cognition() -> None:
    """Causal five-market acceptance fixture, NOT historical economic replay."""
    gate = Vt08FiveMarketCognitiveGate()
    first: dict[str, Vt08CognitiveAction] = {
        "EURJPY": Vt08CognitiveAction.WAIT,
        "USDCHF": Vt08CognitiveAction.ABSTAIN,
        "NZDUSD": Vt08CognitiveAction.EXECUTE,
        "CADJPY": Vt08CognitiveAction.WAIT,
        "USDCAD": Vt08CognitiveAction.EXECUTE,
    }
    for market, expected in first.items():
        overrides: dict[str, object] = {}
        if expected is Vt08CognitiveAction.WAIT:
            overrides["cisd_state"] = "PENDING"
        elif expected is Vt08CognitiveAction.ABSTAIN:
            overrides["material_contradictions"] = ("SOURCE:THESIS_INVALIDATED",)
        assessed = gate.evaluate(
            _snapshot(source=f"synthetic-{market}", market=market, **overrides)
        )
        assert assessed.action is expected

    confirmed_at = T0 + timedelta(minutes=3)
    for market in ("EURJPY", "CADJPY"):
        assessed = gate.evaluate(
            _snapshot(
                source=f"synthetic-{market}", market=market, when=confirmed_at
            )
        )
        assert assessed.action is Vt08CognitiveAction.EXECUTE

    assessed_at = T0 + timedelta(minutes=6)
    for market in ("EURJPY", "NZDUSD", "CADJPY", "USDCAD"):
        outcome = gate.evaluate_position(
            _snapshot(
                source=f"synthetic-{market}",
                market=market,
                when=assessed_at,
                entry_state="FILLED",
                position_state="OPEN",
                journey_stage="IN_TRADE",
            ),
            _position(assessed_at),
        )
        assert outcome.action is Vt08PositionAction.HOLD
        assert outcome.research_only and not outcome.broker_order_authorized

    assert len(gate.decisions) == 7
    assert len(gate.positions) == 4
    assert sum(x.action is Vt08CognitiveAction.EXECUTE for x in gate.decisions) == 4
    assert sum(x.action is Vt08CognitiveAction.WAIT for x in gate.decisions) == 2
    assert sum(x.action is Vt08CognitiveAction.ABSTAIN for x in gate.decisions) == 1
    admitted = {
        (trace.source_event_id, trace.market)
        for trace in gate.decisions
        if trace.action is Vt08CognitiveAction.EXECUTE
    }
    assert admitted == {
        (pos.source_event_id, pos.market) for pos in gate.positions
    }
    assert all(
        decision.decision_fingerprint
        and decision.memory_fingerprint
        and decision.metacognitive_state
        for decision in gate.decisions
    )
