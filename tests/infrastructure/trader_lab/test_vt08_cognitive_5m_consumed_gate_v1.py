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
    Vt08FiveMarketResearchSituation,
)
from qore.infrastructure.traders.vt08_cognitive_position_intelligence import (
    Vt08PositionSnapshot,
)
from qore.infrastructure.traders.vt08_cognitive_v1_contracts import (
    Vt08CognitiveAction,
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
    with pytest.raises(ValueError, match="cannot migrate"):
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
