"""Synthetic event-driven proof of VT08 5M cognitive admission and tracing.

No price-path economic replay and no historical source-entry authority is claimed.
"""
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.trader_lab.vt08_cognitive_5m_consumed_gate_v1 import (
    Vt08FiveMarketCognitiveGate,
    Vt08ResearchFillEvidence,
    Vt08ResearchTerminalEvidence,
)
from qore.infrastructure.traders.vt08_cognitive_5m_research_scope import (
    CAUSAL_FIELDS,
    Vt08FiveMarketResearchSituation,
)
from qore.infrastructure.traders.vt08_cognitive_position_intelligence import (
    Vt08PositionPolicy,
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


def _ack(
    gate: Vt08FiveMarketCognitiveGate,
    *,
    source: str = "synthetic-source-01",
    market: str = "EURJPY",
    when: datetime = T0,
) -> None:
    """Synthetic OHLC research fill: never a real order or fill proof."""
    trace = gate.record_fill(
        Vt08ResearchFillEvidence(
            source_event_id=source,
            market=market,
            side="long",
            source_cycle_id="synthetic-h4-cycle-09",
            fill_id=f"fixture-fill-{source}",
            filled_at=when,
            entry_price=Decimal("100"),
            evidence_sha256="a" * 64,
        )
    )
    assert trace.source_event_id == source
    assert trace.research_only and not trace.broker_order_authorized


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
    with pytest.raises(ValueError, match="without recorded fill"):
        gate.evaluate_position(filled, pos)
    _ack(gate)
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
        _ack(gate, market="USDCAD")
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
    assert left.fills == right.fills
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
    _ack(gate)
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
    _ack(gate)
    with pytest.raises(ValueError, match="must follow recorded fill"):
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
    _ack(gate)
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
    _ack(gate)
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

    for market in ("EURJPY", "NZDUSD", "CADJPY", "USDCAD"):
        _ack(
            gate,
            source=f"synthetic-{market}",
            market=market,
            when=confirmed_at,
        )
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
    assert len(gate.fills) == 4
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


def test_dst_fallback_repeated_new_york_hour_uses_distinct_absolute_clock() -> None:
    """01:30 repeats on DST fallback; comparisons must use aware instants."""
    before_fold = datetime(2026, 11, 1, 5, 30, tzinfo=UTC)
    after_fold = datetime(2026, 11, 1, 6, 30, tzinfo=UTC)
    cycle_end = datetime(2026, 11, 1, 7, 0, tzinfo=UTC)
    ny = ZoneInfo("America/New_York")
    assert before_fold.astimezone(ny).hour == after_fold.astimezone(ny).hour == 1
    assert before_fold.astimezone(ny).fold == 0
    assert after_fold.astimezone(ny).fold == 1
    gate = Vt08FiveMarketCognitiveGate()
    wait = gate.evaluate(
        _snapshot(
            source="synthetic-dst-event",
            when=before_fold,
            anchor_hour_ny=1,
            source_cycle_id="synthetic-dst-cycle",
            cycle_expires_at=cycle_end,
            cisd_state="PENDING",
        )
    )
    execute = gate.evaluate(
        _snapshot(
            source="synthetic-dst-event",
            when=after_fold,
            anchor_hour_ny=1,
            source_cycle_id="synthetic-dst-cycle",
            cycle_expires_at=cycle_end,
        )
    )
    assert wait.action is Vt08CognitiveAction.WAIT
    assert execute.action is Vt08CognitiveAction.EXECUTE
    assert len(gate.decisions) == 2


def test_fill_is_not_implicitly_created_by_execute_and_does_not_multiply() -> None:
    gate = Vt08FiveMarketCognitiveGate()
    gate.evaluate(_snapshot())
    assert gate.fills == ()
    _ack(gate)
    with pytest.raises(ValueError, match="duplicate fill"):
        _ack(gate)
    assert len(gate.fills) == 1
    assert len(gate.positions) == 0


@pytest.mark.parametrize(
    ("changed", "expected"),
    (
        ({"market": "CADJPY"}, "contradicts source identity"),
        ({"side": "short"}, "contradicts source identity"),
        ({"source_cycle_id": "later-cycle"}, "contradicts source identity"),
        ({"filled_at": T0 - timedelta(minutes=1)}, "cannot precede"),
        ({"filled_at": T0 + timedelta(hours=4)}, "after H4 expiry"),
    ),
)
def test_fill_cannot_migrate_source_identity_or_time(
    changed: dict[str, object], expected: str
) -> None:
    gate = Vt08FiveMarketCognitiveGate()
    gate.evaluate(_snapshot())
    inputs: dict[str, object] = {
        "source_event_id": "synthetic-source-01",
        "market": "EURJPY",
        "side": "long",
        "source_cycle_id": "synthetic-h4-cycle-09",
        "fill_id": "bad-fixture-fill",
        "filled_at": T0,
        "entry_price": Decimal("100"),
        "evidence_sha256": "b" * 64,
    }
    inputs.update(changed)
    with pytest.raises(ValueError, match=expected):
        gate.record_fill(Vt08ResearchFillEvidence(**inputs))  # type: ignore[arg-type]
    assert gate.fills == ()


def test_fill_without_execute_and_fill_with_wrong_price_are_rejected() -> None:
    gate = Vt08FiveMarketCognitiveGate()
    not_admitted = Vt08ResearchFillEvidence(
        source_event_id="synthetic-source-01",
        market="EURJPY",
        side="long",
        source_cycle_id="synthetic-h4-cycle-09",
        fill_id="sample",
        filled_at=T0,
        entry_price=Decimal("100"),
        evidence_sha256="e" * 64,
    )
    with pytest.raises(ValueError, match="without cognitive EXECUTE"):
        gate.record_fill(not_admitted)
    gate.evaluate(_snapshot())
    _ack(gate)
    later = T0 + timedelta(minutes=3)
    with pytest.raises(ValueError, match="differs from recorded fill"):
        gate.evaluate_position(
            _snapshot(
                when=later,
                entry_state="FILLED",
                position_state="OPEN",
            ),
            Vt08PositionSnapshot(
                as_of=later,
                side="long",
                entry_price=Decimal("101"),
                current_price=Decimal("102"),
                initial_stop=Decimal("99"),
                current_stop=Decimal("99"),
                bound_destination=Decimal("103"),
            ),
        )


def test_fill_evidence_never_confers_broker_authority_or_weak_digest() -> None:
    e = {
        "source_event_id": "x",
        "market": "EURJPY",
        "side": "long",
        "source_cycle_id": "cycle",
        "fill_id": "fill",
        "filled_at": T0,
        "entry_price": Decimal("100"),
        "evidence_sha256": "a" * 64,
    }
    with pytest.raises(ValueError, match="research-only"):
        Vt08ResearchFillEvidence(**e, broker_order_authorized=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="SHA256"):
        Vt08ResearchFillEvidence(
            **{**e, "evidence_sha256": "false"}
        )
    with pytest.raises(ValueError, match="positive finite"):
        Vt08ResearchFillEvidence(
            **{**e, "entry_price": Decimal("NaN")}
        )


def _terminal(
    *, source: str = "synthetic-source-01",
    fill_id: str = "fixture-fill-synthetic-source-01",
    when: datetime = T0 + timedelta(minutes=9),
    market: str = "EURJPY",
    fill_digest: str = "a" * 64,
) -> Vt08ResearchTerminalEvidence:
    return Vt08ResearchTerminalEvidence(
        source_event_id=source,
        market=market,
        fill_id=fill_id,
        fill_evidence_sha256=fill_digest,
        closed_at=when,
        exit_price=Decimal("101"),
        terminal_reason="EXTERNAL_CLOSE",
        evidence_sha256="c" * 64,
    )


def test_cognitive_position_trace_attaches_physical_fill_and_risk_terms() -> None:
    gate = Vt08FiveMarketCognitiveGate()
    gate.evaluate(_snapshot())
    _ack(gate)
    later = T0 + timedelta(minutes=3)
    state = gate.evaluate_position(
        _snapshot(when=later, entry_state="FILLED", position_state="OPEN"),
        _position(later),
    )
    assert state.fill_id == "fixture-fill-synthetic-source-01"
    assert state.fill_evidence_sha256 == "a" * 64
    assert state.original_initial_stop == Decimal("99")
    assert state.original_bound_destination == Decimal("103")
    assert state.observed_current_stop == Decimal("99")
    assert state.research_only and not state.broker_order_authorized


@pytest.mark.parametrize(("changed", "value"), [
    ("initial_stop", Decimal("98.5")),
    ("bound_destination", Decimal("105")),
])
def test_cognitive_position_rejects_initial_risk_and_target_mutation(
    changed: str, value: Decimal,
) -> None:
    gate = Vt08FiveMarketCognitiveGate()
    gate.evaluate(_snapshot())
    _ack(gate)
    t1 = T0 + timedelta(minutes=3)
    t2 = T0 + timedelta(minutes=6)
    gate.evaluate_position(
        _snapshot(when=t1, entry_state="FILLED", position_state="OPEN"),
        _position(t1),
    )
    altered = replace(_position(t2), **{changed: value})
    with pytest.raises(ValueError, match="initial SL and destination cannot drift"):
        gate.evaluate_position(
            _snapshot(when=t2, entry_state="FILLED", position_state="OPEN"),
            altered,
        )
    assert len(gate.positions) == 1
    valid = gate.evaluate_position(
        _snapshot(when=t2, entry_state="FILLED", position_state="OPEN"),
        _position(t2),
    )
    assert valid.original_initial_stop == Decimal("99")


@pytest.mark.parametrize("side", ["long", "short"])
def test_cognitive_position_rejects_widening_stops_between_snapshots(
    side: str,
) -> None:
    gate = Vt08FiveMarketCognitiveGate()
    gate.evaluate(_snapshot(side=side))
    if side == "long":
        _ack(gate)
    else:
        gate.record_fill(Vt08ResearchFillEvidence(
            source_event_id="synthetic-source-01",
            market="EURJPY",
            side="short",
            source_cycle_id="synthetic-h4-cycle-09",
            fill_id="short-fill",
            filled_at=T0,
            entry_price=Decimal("100"),
            evidence_sha256="a" * 64,
        ))
    t1, t2 = T0 + timedelta(minutes=3), T0 + timedelta(minutes=6)
    if side == "long":
        first = replace(_position(t1), current_stop=Decimal("99.7"))
        widen = replace(_position(t2), current_stop=Decimal("99.2"))
        safe = replace(_position(t2), current_stop=Decimal("99.8"))
    else:
        first = Vt08PositionSnapshot(
            as_of=t1, side="short",
            entry_price=Decimal("100"), current_price=Decimal("99"),
            initial_stop=Decimal("101"), current_stop=Decimal("100.3"),
            bound_destination=Decimal("97"),
        )
        widen = replace(first, as_of=t2, current_stop=Decimal("100.8"))
        safe = replace(first, as_of=t2, current_stop=Decimal("100.2"))
    gate.evaluate_position(
        _snapshot(when=t1, side=side, entry_state="FILLED", position_state="OPEN"),
        first,
    )
    with pytest.raises(ValueError, match="observed stop cannot widen"):
        gate.evaluate_position(
            _snapshot(when=t2, side=side, entry_state="FILLED", position_state="OPEN"),
            widen,
        )
    accepted = gate.evaluate_position(
        _snapshot(when=t2, side=side, entry_state="FILLED", position_state="OPEN"),
        safe,
    )
    assert accepted.observed_current_stop == safe.current_stop
    assert len(gate.positions) == 2


def test_terminal_external_evidence_blocks_all_future_position_cognition() -> None:
    gate = Vt08FiveMarketCognitiveGate()
    gate.evaluate(_snapshot())
    _ack(gate)
    t1 = T0 + timedelta(minutes=3)
    t2 = T0 + timedelta(minutes=9)
    p = gate.evaluate_position(
        _snapshot(when=t1, entry_state="FILLED", position_state="OPEN"),
        _position(t1),
    )
    assert gate.terminals == ()
    result = gate.record_terminal(_terminal(when=t2))
    assert result.fill_id == p.fill_id
    assert result.related_fill_evidence_sha256 == p.fill_evidence_sha256
    assert result.last_position_fingerprint == p.position_fingerprint
    assert result.research_only and not result.broker_order_authorized
    assert len(gate.terminals) == 1
    with pytest.raises(ValueError, match="already terminal"):
        gate.record_terminal(_terminal(when=t2 + timedelta(minutes=3)))
    with pytest.raises(ValueError, match="terminal-closed position"):
        gate.evaluate_position(
            _snapshot(
                when=t2 + timedelta(minutes=3),
                entry_state="FILLED",
                position_state="OPEN",
            ),
            _position(t2 + timedelta(minutes=3)),
        )
    assert len(gate.positions) == 1


@pytest.mark.parametrize(("changed", "expected"), [
    ({"fill_id": "another-fill"}, "contradicts fill lineage"),
    ({"market": "CADJPY"}, "contradicts fill lineage"),
    ({"fill_digest": "d" * 64}, "contradicts fill lineage"),
    ({"when": T0}, "must follow original fill"),
])
def test_terminal_evidence_wrong_lineage_or_clock_cannot_mutate_state(
    changed: dict[str, object], expected: str,
) -> None:
    gate = Vt08FiveMarketCognitiveGate()
    gate.evaluate(_snapshot())
    _ack(gate)
    data: dict[str, object] = {
        "source": "synthetic-source-01",
        "market": "EURJPY",
        "fill_id": "fixture-fill-synthetic-source-01",
        "fill_digest": "a" * 64,
        "when": T0 + timedelta(minutes=9),
    }
    data.update(changed)
    with pytest.raises(ValueError, match=expected):
        gate.record_terminal(_terminal(**data))  # type: ignore[arg-type]
    assert gate.terminals == ()
    assert gate.record_terminal(_terminal()).terminal_reason == "EXTERNAL_CLOSE"


def test_terminal_requires_external_fill_and_explicit_research_authority() -> None:
    gate = Vt08FiveMarketCognitiveGate()
    with pytest.raises(ValueError, match="requires registered research fill"):
        gate.record_terminal(_terminal())
    with pytest.raises(ValueError, match="SHA256"):
        replace(_terminal(), evidence_sha256="not-a-sha")
    with pytest.raises(ValueError, match="research-only"):
        replace(_terminal(), broker_order_authorized=True)
    with pytest.raises(ValueError, match="positive finite"):
        replace(_terminal(), exit_price=Decimal("NaN"))
    with pytest.raises(ValueError, match="terminal reason"):
        replace(_terminal(), terminal_reason="PROFIT")


def test_cognitive_exit_advice_is_not_external_terminal_settlement() -> None:
    gate = Vt08FiveMarketCognitiveGate()
    gate.evaluate(_snapshot())
    _ack(gate)
    at = T0 + timedelta(hours=4)
    proposed = gate.evaluate_position(
        _snapshot(
            when=at, entry_state="FILLED", position_state="OPEN",
            h4_lifecycle_valid=False,
        ),
        _position(at),
    )
    assert proposed.action is Vt08PositionAction.EXIT
    assert gate.terminals == ()
    trace = gate.record_terminal(_terminal(
        when=at + timedelta(minutes=3),
    ))
    assert trace.last_position_fingerprint == proposed.position_fingerprint
    assert len(gate.terminals) == 1


def test_terminal_global_clock_never_regresses_after_another_market_event() -> None:
    gate = Vt08FiveMarketCognitiveGate()
    gate.evaluate(_snapshot())
    _ack(gate)
    later = T0 + timedelta(minutes=12)
    gate.evaluate(_snapshot(source="second-source", market="CADJPY", when=later))
    with pytest.raises(ValueError, match="terminal replay clock"):
        gate.record_terminal(_terminal(when=T0 + timedelta(minutes=9)))
    assert gate.terminals == ()


def test_dst_fall_back_wall_clock_decreases_while_actual_replay_clock_advances() -> None:
    ny = ZoneInfo("America/New_York")
    early = datetime(2026, 11, 1, 1, 45, tzinfo=ny, fold=0)
    later = datetime(2026, 11, 1, 1, 15, tzinfo=ny, fold=1)
    assert early.astimezone(UTC) < later.astimezone(UTC)
    assert early.hour == later.hour == 1
    expiry = datetime(2026, 11, 1, 3, 0, tzinfo=ny)
    gate = Vt08FiveMarketCognitiveGate()
    pending = gate.evaluate(_snapshot(
        source="fall-fold",
        when=early,
        anchor_hour_ny=1,
        source_cycle_id="fall-cycle",
        cycle_expires_at=expiry,
        cisd_state="PENDING",
    ))
    confirmed = gate.evaluate(_snapshot(
        source="fall-fold",
        when=later,
        anchor_hour_ny=1,
        source_cycle_id="fall-cycle",
        cycle_expires_at=expiry,
    ))
    assert pending.action is Vt08CognitiveAction.WAIT
    assert confirmed.action is Vt08CognitiveAction.EXECUTE
    assert gate.fills == ()
    # A callback ordered backwards in *absolute* time cannot pass even
    # when its NY wall-clock string looks later.
    with pytest.raises(ValueError, match="global replay clock"):
        gate.evaluate(_snapshot(
            source="backwards-fold",
            when=early,
            anchor_hour_ny=1,
            source_cycle_id="independent-cycle",
            cycle_expires_at=expiry,
        ))


def test_dst_fold_latest_m15_and_feature_cutoff_require_absolute_source_time() -> None:
    ny = ZoneInfo("America/New_York")
    early = datetime(2026, 11, 1, 1, 45, tzinfo=ny, fold=0)
    later = datetime(2026, 11, 1, 1, 15, tzinfo=ny, fold=1)
    expiry = datetime(2026, 11, 1, 3, 0, tzinfo=ny)
    with pytest.raises(ValueError, match="consume future bars"):
        _snapshot(
            when=early, anchor_hour_ny=1, cycle_expires_at=expiry,
            latest_available_bar_close=later,
            feature_cutoffs=tuple((k, early) for k in CAUSAL_FIELDS),
        )
    with pytest.raises(ValueError, match="cutoff consumes future"):
        _snapshot(
            when=early, anchor_hour_ny=1, cycle_expires_at=expiry,
            latest_available_bar_close=early,
            feature_cutoffs=tuple((k, later) for k in CAUSAL_FIELDS),
        )


def test_replay_position_accepts_same_instant_in_ny_and_utc_after_dst() -> None:
    ny = ZoneInfo("America/New_York")
    at = datetime(2026, 11, 1, 1, 15, tzinfo=ny, fold=1)
    expiry = datetime(2026, 11, 1, 3, 0, tzinfo=ny)
    earlier = datetime(2026, 11, 1, 1, 5, tzinfo=ny, fold=1)
    gate = Vt08FiveMarketCognitiveGate()
    gate.evaluate(_snapshot(
        when=earlier, anchor_hour_ny=1, source_cycle_id="fold-pos",
        cycle_expires_at=expiry,
    ))
    gate.record_fill(Vt08ResearchFillEvidence(
        source_event_id="synthetic-source-01",
        market="EURJPY", side="long", source_cycle_id="fold-pos",
        fill_id="dst-fill", filled_at=earlier,
        entry_price=Decimal("100"), evidence_sha256="a" * 64,
    ))
    result = gate.evaluate_position(
        _snapshot(
            when=at, anchor_hour_ny=1, source_cycle_id="fold-pos",
            cycle_expires_at=expiry, entry_state="FILLED",
            position_state="OPEN",
        ),
        _position(at.astimezone(UTC)),
    )
    assert result.fill_id == "dst-fill"
    assert result.action is Vt08PositionAction.HOLD


@pytest.mark.parametrize("field", (
    "methodology_valid", "source_identity_complete", "h4_lifecycle_valid",
))
def test_string_false_cannot_become_truthy_cognitive_source_authority(field: str) -> None:
    with pytest.raises(ValueError, match="must be exact bool"):
        _snapshot(**{field: "false"})


@pytest.mark.parametrize(("field", "raw", "match"), (
    ("anchor_hour_ny", True, "anchor outside"),
    ("research_only", "true", "authority flags must be exact bool"),
    ("operational_authority", "false", "authority flags must be exact bool"),
    ("current_overlap_rate", 0.3, "finite Decimal"),
    ("displacement_strength", float("nan"), "finite Decimal"),
))
def test_malformed_source_snapshot_types_rejected_before_reasoning(
    field: str, raw: object, match: str,
) -> None:
    gate = Vt08FiveMarketCognitiveGate()
    with pytest.raises(ValueError, match=match):
        gate.evaluate(_snapshot(**{field: raw}))
    assert gate.decisions == () and gate.positions == ()


def test_position_policy_and_candidate_boolean_values_must_be_exact() -> None:
    with pytest.raises(ValueError, match="exact bool"):
        Vt08PositionPolicy(
            allow_confirmed_structural_protection="false",  # type: ignore[arg-type]
            allow_reduce_on_causal_exhaustion=False,
        )
    with pytest.raises(ValueError, match="exact bool"):
        replace(_position(T0), protection_candidate_confirmed="false")
    with pytest.raises(ValueError, match="positive finite Decimal"):
        replace(_position(T0), current_price=100.2)
    with pytest.raises(ValueError, match="positive finite Decimal"):
        replace(_position(T0), protection_candidate=100.1)


def test_fill_and_terminal_input_price_types_and_authority_must_be_exact() -> None:
    fill = Vt08ResearchFillEvidence(
        source_event_id="synthetic-source-01", market="EURJPY",
        side="long", source_cycle_id="synthetic-h4-cycle-09",
        fill_id="safe-fill", filled_at=T0,
        entry_price=Decimal("100"), evidence_sha256="a" * 64,
    )
    with pytest.raises(ValueError, match="positive finite Decimal"):
        replace(fill, entry_price=100.1)
    with pytest.raises(ValueError, match="authority flags must be exact bool"):
        replace(fill, research_only="true")
    terminal = _terminal()
    with pytest.raises(ValueError, match="positive finite Decimal"):
        replace(terminal, exit_price=100.1)
    with pytest.raises(ValueError, match="authority flags must be exact bool"):
        replace(terminal, broker_order_authorized="false")
