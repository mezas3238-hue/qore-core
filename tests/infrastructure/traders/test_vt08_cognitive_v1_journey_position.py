from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt08_cognitive_journey_intelligence import (
    Vt08JourneyState,
    assess_journey,
)
from qore.infrastructure.traders.vt08_cognitive_orchestrator import (
    evaluate_in_trade_cognition,
)
from qore.infrastructure.traders.vt08_cognitive_position_intelligence import (
    RESEARCH_UNCALIBRATED_POSITION_POLICY,
    Vt08PositionDecision,
    Vt08PositionPolicy,
    Vt08PositionSnapshot,
    improves_stop,
)
from qore.infrastructure.traders.vt08_cognitive_situation_model import (
    Vt08ForexSituationModel,
)
from qore.infrastructure.traders.vt08_cognitive_v1_contracts import (
    Vt08PositionAction,
)


def _situation(**overrides: object) -> Vt08ForexSituationModel:
    payload: dict[str, object] = {
        "as_of": datetime(2026, 9, 23, 13, 15, tzinfo=UTC),
        "market": "GBPUSD",
        "anchor_hour_ny": 9,
        "side": "short",
        "ltf_profile": "m15-standard",
        "methodology_valid": True,
        "source_identity_complete": True,
        "h4_lifecycle_valid": True,
        "bias_state": "RESOLVED",
        "scenario_state": "C2",
        "poi_state": "CONFIRMED",
        "protected_swing_state": "CONFIRMED",
        "cisd_state": "CONFIRMED",
        "displacement_state": "CONTINUING",
        "entry_state": "FILLED",
        "entry_freshness_state": "CURRENT",
        "liquidity_state": "DELIVERING",
        "range_state": "KNOWN",
        "volatility_state": "KNOWN",
        "journey_stage": "IN_TRADE",
        "structural_destination_state": "APPROACHING",
        "exhaustion_state": "NOT_OBSERVED",
        "risk_geometry_state": "VALID",
        "position_state": "OPEN",
        "supporting_evidence": ("JOURNEY:DELIVERY_PRESENT",),
    }
    payload.update(overrides)
    return Vt08ForexSituationModel(**payload)  # type: ignore[arg-type]


def _position(**overrides: object) -> Vt08PositionSnapshot:
    payload: dict[str, object] = {
        "as_of": datetime(2026, 9, 23, 13, 15, tzinfo=UTC),
        "side": "short",
        "entry_price": Decimal("1.3400"),
        "current_price": Decimal("1.3320"),
        "initial_stop": Decimal("1.3460"),
        "current_stop": Decimal("1.3460"),
        "bound_destination": Decimal("1.3250"),
        "protection_candidate": None,
        "protection_candidate_confirmed": False,
    }
    payload.update(overrides)
    return Vt08PositionSnapshot(**payload)  # type: ignore[arg-type]


def test_advancing_journey_is_resolved_causally() -> None:
    assessment = assess_journey(_situation())
    assert assessment.journey_state is Vt08JourneyState.ADVANCING
    assert assessment.execution_authorized is False
    assert len(assessment.fingerprint()) == 64


def test_h4_lifecycle_expiry_invalidates_journey_and_recommends_exit() -> None:
    evaluation = evaluate_in_trade_cognition(
        situation=_situation(h4_lifecycle_valid=False),
        position=_position(),
    )
    assert evaluation.journey.journey_state is Vt08JourneyState.INVALIDATED
    assert evaluation.position_decision.action is Vt08PositionAction.EXIT
    assert evaluation.position_decision.execution_authorized is False


def test_bound_destination_reached_recommends_exit_without_order_authority() -> None:
    evaluation = evaluate_in_trade_cognition(
        situation=_situation(structural_destination_state="REACHED"),
        position=_position(current_price=Decimal("1.3250")),
    )
    assert evaluation.journey.journey_state is Vt08JourneyState.DESTINATION_REACHED
    assert evaluation.position_decision.action is Vt08PositionAction.EXIT
    assert evaluation.position_decision.capital_authority is False


def test_default_policy_does_not_activate_unvalidated_protection() -> None:
    evaluation = evaluate_in_trade_cognition(
        situation=_situation(),
        position=_position(
            protection_candidate=Decimal("1.3360"),
            protection_candidate_confirmed=True,
        ),
        policy=RESEARCH_UNCALIBRATED_POSITION_POLICY,
    )
    assert evaluation.position_decision.action is Vt08PositionAction.HOLD
    assert "POSITION:HOLD_PROTECTION_NOT_VT08_CALIBRATED" in (
        evaluation.position_decision.reason_codes
    )


def test_explicit_research_policy_can_exercise_protection_mechanics() -> None:
    policy = Vt08PositionPolicy(
        allow_confirmed_structural_protection=True,
        allow_reduce_on_causal_exhaustion=False,
    )
    evaluation = evaluate_in_trade_cognition(
        situation=_situation(),
        position=_position(
            protection_candidate=Decimal("1.3360"),
            protection_candidate_confirmed=True,
        ),
        policy=policy,
    )
    assert evaluation.position_decision.action is Vt08PositionAction.PROTECT
    assert evaluation.position_decision.next_stop == Decimal("1.3360")
    assert evaluation.position_decision.quantity_change_authorized is False


def test_exhaustion_reduction_is_disabled_until_vt08_calibration() -> None:
    evaluation = evaluate_in_trade_cognition(
        situation=_situation(exhaustion_state="CONFIRMED"),
        position=_position(),
    )
    assert evaluation.journey.journey_state is Vt08JourneyState.EXHAUSTION_RISK
    assert evaluation.position_decision.action is Vt08PositionAction.HOLD

    research_policy = Vt08PositionPolicy(
        allow_confirmed_structural_protection=False,
        allow_reduce_on_causal_exhaustion=True,
    )
    research_evaluation = evaluate_in_trade_cognition(
        situation=_situation(exhaustion_state="CONFIRMED"),
        position=_position(),
        policy=research_policy,
    )
    assert research_evaluation.position_decision.action is Vt08PositionAction.REDUCE
    assert research_evaluation.position_decision.execution_authorized is False


def test_stop_can_improve_but_cannot_widen() -> None:
    assert improves_stop(
        side="short",
        current_stop=Decimal("1.3460"),
        current_price=Decimal("1.3320"),
        candidate_stop=Decimal("1.3360"),
    )
    assert not improves_stop(
        side="short",
        current_stop=Decimal("1.3460"),
        current_price=Decimal("1.3320"),
        candidate_stop=Decimal("1.3500"),
    )
    with pytest.raises(ValueError, match="widened"):
        _position(current_stop=Decimal("1.3500"))


def test_long_stop_widening_fails_closed() -> None:
    with pytest.raises(ValueError, match="widened"):
        Vt08PositionSnapshot(
            as_of=datetime(2026, 9, 23, 13, 15, tzinfo=UTC),
            side="long",
            entry_price=Decimal("1.3400"),
            current_price=Decimal("1.3480"),
            initial_stop=Decimal("1.3340"),
            current_stop=Decimal("1.3300"),
            bound_destination=Decimal("1.3550"),
        )


def test_in_trade_side_mismatch_fails_closed() -> None:
    with pytest.raises(ValueError, match="side mismatch"):
        evaluate_in_trade_cognition(
            situation=_situation(side="long"),
            position=_position(side="short"),
        )


@pytest.mark.parametrize(
    ("overrides", "expected"),
    (
        ({"position_state": "FLAT"}, Vt08JourneyState.PRE_ENTRY),
        ({"h4_lifecycle_valid": False}, Vt08JourneyState.INVALIDATED),
        (
            {"material_contradictions": ("SOURCE:INVALIDATED",)},
            Vt08JourneyState.INVALIDATED,
        ),
        (
            {"structural_destination_state": "REACHED"},
            Vt08JourneyState.DESTINATION_REACHED,
        ),
        ({"exhaustion_state": "CONFIRMED"}, Vt08JourneyState.EXHAUSTION_RISK),
        ({"journey_stage": "STALLED"}, Vt08JourneyState.STALLED),
        ({"displacement_state": "WEAKENING"}, Vt08JourneyState.STALLED),
        (
            {
                "displacement_state": "UNKNOWN",
                "structural_destination_state": "UNKNOWN",
            },
            Vt08JourneyState.UNKNOWN,
        ),
        ({}, Vt08JourneyState.ADVANCING),
    ),
)
def test_journey_every_defined_state_and_causal_priority(
    overrides: dict[str, object], expected: Vt08JourneyState
) -> None:
    output = assess_journey(_situation(**overrides))
    assert output.journey_state is expected
    assert output.execution_authorized is False
    assert len(output.fingerprint()) == 64


def test_position_policy_holds_when_optional_exit_rules_explicitly_disabled() -> None:
    from qore.infrastructure.traders.vt08_cognitive_position_intelligence import (
        decide_position,
    )

    policy = Vt08PositionPolicy(
        allow_confirmed_structural_protection=False,
        allow_reduce_on_causal_exhaustion=False,
        exit_on_h4_lifecycle_end=False,
        exit_on_material_thesis_invalidation=False,
        exit_on_bound_destination_reached=False,
    )
    journey = assess_journey(_situation(h4_lifecycle_valid=False))
    advice = decide_position(position=_position(), journey=journey, policy=policy)
    assert advice.action is Vt08PositionAction.HOLD
    assert advice.execution_authorized is False


def test_position_snapshot_rejects_invalid_stop_and_price_semantics() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _position(as_of=datetime(2026, 9, 23, 13, 15))
    with pytest.raises(ValueError, match="positive finite"):
        _position(current_price=Decimal("NaN"))
    with pytest.raises(ValueError, match="positive finite"):
        _position(protection_candidate=Decimal("Infinity"))
    with pytest.raises(ValueError, match="short initial geometry invalid"):
        _position(bound_destination=Decimal("1.3500"))
    with pytest.raises(ValueError, match="above current price"):
        _position(current_stop=Decimal("1.3310"))
    with pytest.raises(ValueError, match="short current stop widened"):
        _position(current_stop=Decimal("1.3480"))


def test_position_decision_cannot_be_promoted_to_broker_or_capital_authority() -> None:
    for change in (
        {"execution_authorized": True},
        {"quantity_change_authorized": True},
        {"capital_authority": True},
    ):
        with pytest.raises(ValueError, match="research/shadow only"):
            Vt08PositionDecision(
                action=Vt08PositionAction.HOLD,
                next_stop=None,
                reason_codes=("POSITION:SAFE_HOLD",),
                policy_calibrated=False,
                journey_fingerprint="synthetic",
                **change,
            )


def test_long_and_short_protection_candidates_must_improve_not_widen_stops() -> None:
    assert improves_stop(
        side="long",
        current_stop=Decimal("1.320"),
        current_price=Decimal("1.350"),
        candidate_stop=Decimal("1.330"),
    )
    assert not improves_stop(
        side="long",
        current_stop=Decimal("1.320"),
        current_price=Decimal("1.350"),
        candidate_stop=Decimal("1.315"),
    )
    with pytest.raises(ValueError, match="side must be"):
        improves_stop(
            side="neither",
            current_stop=Decimal("1.320"),
            current_price=Decimal("1.350"),
            candidate_stop=Decimal("1.330"),
        )


def test_material_thesis_invalidation_exits_even_when_h4_still_valid() -> None:
    assessment = evaluate_in_trade_cognition(
        situation=_situation(
            h4_lifecycle_valid=True,
            material_contradictions=("SOURCE:PROTECTED_SWING_BROKEN",),
        ),
        position=_position(),
    )
    assert assessment.journey.journey_state is Vt08JourneyState.INVALIDATED
    assert assessment.position_decision.action is Vt08PositionAction.EXIT
    assert "POSITION:EXIT_CAUSAL_THESIS_INVALIDATED" in (
        assessment.position_decision.reason_codes
    )
    assert assessment.position_decision.execution_authorized is False


def test_long_position_never_accepts_stop_past_current_or_invalid_geometry() -> None:
    payload = {
        "as_of": datetime(2026, 9, 23, 13, 15, tzinfo=UTC),
        "side": "long",
        "entry_price": Decimal("1.3400"),
        "current_price": Decimal("1.3480"),
        "initial_stop": Decimal("1.3340"),
        "current_stop": Decimal("1.3340"),
        "bound_destination": Decimal("1.3550"),
    }
    with pytest.raises(ValueError, match="long initial geometry invalid"):
        Vt08PositionSnapshot(**{**payload, "bound_destination": Decimal("1.3300")})
    with pytest.raises(ValueError, match="below current price"):
        Vt08PositionSnapshot(**{**payload, "current_stop": Decimal("1.3500")})
    with pytest.raises(ValueError, match="widened"):
        Vt08PositionSnapshot(**{**payload, "current_stop": Decimal("1.3330")})
