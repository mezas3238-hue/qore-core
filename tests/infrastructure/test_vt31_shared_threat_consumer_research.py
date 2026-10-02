from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.core_stack_v2.shared_position_threat_intelligence import (
    SharedPositionThreatEngineAssessment,
    SharedPositionThreatScope,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedPositionThreatLevel,
    SharedSupportState,
)
from qore.infrastructure.traders.vt31_shared_threat_consumer_research import (
    FROZEN_STI8_ECONOMIC_POLICY_V1,
    Vt31ThreatConsumerAction,
    decide_vt31_threat_response,
)

T0 = datetime(2026, 9, 30, 3, 35, tzinfo=UTC)


def _assessment(
    level: SharedPositionThreatLevel,
) -> SharedPositionThreatEngineAssessment:
    return SharedPositionThreatEngineAssessment(
        threat_level=level,
        threat_scope=SharedPositionThreatScope.CROSS_ASSET_THREAT,
        threat_score_bps=7_500,
        continuation_support_bps=3_000,
        failure_hazard_bps=8_000,
        relationship_break_bps=7_000,
        systemic_stress_bps=6_500,
        uncertainty_bps=2_500,
        continuation_support=SharedSupportState.LOW,
        failure_hazard=SharedSupportState.STRONG,
        reason_codes=("TEST_CAUSAL_THREAT",),
    )


def test_control_arm_uses_same_consumer_but_holds_without_shared() -> None:
    decision = decide_vt31_threat_response(
        decision_time=T0,
        shared_assessment=None,
        shared_intelligence_ref=None,
    )

    assert decision.action is Vt31ThreatConsumerAction.HOLD
    assert decision.trader_owns_decision is True
    assert decision.shared_exit_authority is False
    assert decision.future_outcome_used is False


@pytest.mark.parametrize(
    "level",
    (
        SharedPositionThreatLevel.ELEVATED,
        SharedPositionThreatLevel.HIGH,
        SharedPositionThreatLevel.CRITICAL,
    ),
)
def test_material_threat_is_trader_owned_next_open_exit(
    level: SharedPositionThreatLevel,
) -> None:
    decision = decide_vt31_threat_response(
        decision_time=T0,
        shared_assessment=_assessment(level),
        shared_intelligence_ref=f"sti8:{level.value}",
    )

    assert decision.action is Vt31ThreatConsumerAction.EXIT_NEXT_M1_OPEN
    assert decision.observed_threat_level is level
    assert decision.trader_owns_decision is True
    assert decision.shared_exit_authority is False
    assert decision.shared_stop_authority is False
    assert decision.shared_target_authority is False


@pytest.mark.parametrize(
    "level",
    (
        SharedPositionThreatLevel.NONE,
        SharedPositionThreatLevel.LOW,
        SharedPositionThreatLevel.MODERATE,
        SharedPositionThreatLevel.INSUFFICIENT,
    ),
)
def test_nonmaterial_threat_holds(
    level: SharedPositionThreatLevel,
) -> None:
    decision = decide_vt31_threat_response(
        decision_time=T0,
        shared_assessment=_assessment(level),
        shared_intelligence_ref=f"sti8:{level.value}",
    )

    assert decision.action is Vt31ThreatConsumerAction.HOLD


def test_treatment_requires_provenance_reference() -> None:
    with pytest.raises(ValueError, match="requires Shared intelligence ref"):
        decide_vt31_threat_response(
            decision_time=T0,
            shared_assessment=_assessment(SharedPositionThreatLevel.HIGH),
            shared_intelligence_ref=None,
        )


def test_policy_preserves_initial_geometry_and_forbids_shared_authority() -> None:
    p = FROZEN_STI8_ECONOMIC_POLICY_V1
    assert p.same_initial_entry_stop_target_required is True
    assert p.decision_effective_next_m1_open is True
    assert p.sizing_mutation_allowed is False
    assert p.stop_mutation_allowed is False
    assert p.target_mutation_allowed is False
    assert p.productive_authority is False
