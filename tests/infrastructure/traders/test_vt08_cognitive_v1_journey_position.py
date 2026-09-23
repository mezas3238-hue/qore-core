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
