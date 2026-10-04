from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_continuation_positive_tail_intelligence import (
    SharedPositionCausalObservation,
)
from qore.infrastructure.core_stack_v2.shared_position_threat_intelligence import (
    SharedPositionThreatEngineAssessment,
    SharedPositionThreatScope,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedPositionThreatLevel,
    SharedSupportState,
)
from qore.infrastructure.traders.vt31_shared_threat_consumer_research import (
    Vt31ThreatConsumerAction,
)
from qore.infrastructure.traders.vt31_shared_threat_consumer_v4_research import (
    FROZEN_STI8_RESPONSE_V4,
    decide_vt31_threat_response_v4,
)

T0 = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def _obs(
    minute: int,
    *,
    signed_close: int,
    efficiency: int,
    overlap: int,
) -> SharedPositionCausalObservation:
    return SharedPositionCausalObservation(
        observation_id=f"v4-obs-{minute}",
        position_id="trade-v4-001",
        asset="NAS100",
        as_of=T0 + timedelta(minutes=minute),
        evidence_cutoff_at=T0 + timedelta(minutes=minute),
        minutes_since_fill=minute,
        progress_bps=max(0, signed_close),
        signed_close_r_bps=signed_close,
        efficiency_bps=efficiency,
        overlap_bps=overlap,
        signed_body_r_bps=signed_close,
        peer_confirmation_bps=3_000,
        breadth_bps=5_000,
        peer_transition_adverse_bps=7_000,
        world_support_bps=3_000,
        world_fragility_bps=7_000,
        data_integrity_bps=10_000,
        provenance_refs=("source:v4-test",),
    )


def _assessment(
    *,
    failure: int,
    continuation: int,
) -> SharedPositionThreatEngineAssessment:
    return SharedPositionThreatEngineAssessment(
        threat_level=SharedPositionThreatLevel.HIGH,
        threat_scope=SharedPositionThreatScope.CROSS_ASSET_THREAT,
        threat_score_bps=8_000,
        continuation_support_bps=continuation,
        failure_hazard_bps=failure,
        relationship_break_bps=7_000,
        systemic_stress_bps=6_000,
        uncertainty_bps=2_000,
        continuation_support=SharedSupportState.MODERATE,
        failure_hazard=SharedSupportState.STRONG,
        reason_codes=("HIGH_SOURCE_THREAT",),
    )


def _v3_actionable_prefix() -> tuple[
    SharedPositionCausalObservation,
    SharedPositionThreatEngineAssessment,
    SharedPositionCausalObservation,
    SharedPositionThreatEngineAssessment,
]:
    prior = _obs(1, signed_close=-2_000, efficiency=-1_000, overlap=6_000)
    previous = _obs(2, signed_close=-5_000, efficiency=-4_000, overlap=8_000)
    prior_assessment = _assessment(failure=6_000, continuation=4_000)
    previous_assessment = _assessment(failure=8_000, continuation=2_000)
    return prior, prior_assessment, previous, previous_assessment


def test_v4_policy_preserves_frozen_recovery_veto_and_no_authority() -> None:
    policy = FROZEN_STI8_RESPONSE_V4

    assert policy.require_parent_v3_actionable_at_t_minus_1 is True
    assert policy.require_next_causal_observation is True
    assert policy.veto_if_local_margin_nonpositive is True
    assert policy.veto_if_hazard_margin_nonpositive is True
    assert policy.same_initial_entry_stop_target_required is True
    assert policy.sizing_mutation_allowed is False
    assert policy.stop_mutation_allowed is False
    assert policy.target_mutation_allowed is False
    assert policy.productive_authority is False
    assert len(policy.fingerprint()) == 64


def test_v4_confirms_nonrecovery_one_observation_later() -> None:
    prior, prior_a, previous, previous_a = _v3_actionable_prefix()
    current = _obs(3, signed_close=-4_500, efficiency=-3_500, overlap=7_500)
    current_a = _assessment(failure=7_500, continuation=2_500)

    decision = decide_vt31_threat_response_v4(
        prior_observation=prior,
        prior_assessment=prior_a,
        previous_observation=previous,
        previous_assessment=previous_a,
        observation=current,
        assessment=current_a,
        shared_intelligence_ref="sti8:v4:test",
    )

    assert decision.action is Vt31ThreatConsumerAction.EXIT_NEXT_M1_OPEN
    assert decision.reason_codes == ("V4_ONE_STEP_NONRECOVERY_CONFIRMED",)
    assert decision.trader_owns_decision is True
    assert decision.shared_exit_authority is False
    assert decision.future_outcome_used is False


def test_v4_vetoes_when_local_margin_recovers() -> None:
    prior, prior_a, previous, previous_a = _v3_actionable_prefix()
    current = _obs(3, signed_close=7_000, efficiency=7_000, overlap=1_000)
    current_a = _assessment(failure=7_500, continuation=2_500)

    decision = decide_vt31_threat_response_v4(
        prior_observation=prior,
        prior_assessment=prior_a,
        previous_observation=previous,
        previous_assessment=previous_a,
        observation=current,
        assessment=current_a,
        shared_intelligence_ref="sti8:v4:test",
    )

    assert decision.action is Vt31ThreatConsumerAction.HOLD
    assert decision.reason_codes == ("V4_ONE_STEP_RECOVERY_VETO",)


def test_v4_vetoes_when_hazard_margin_recovers() -> None:
    prior, prior_a, previous, previous_a = _v3_actionable_prefix()
    current = _obs(3, signed_close=-4_500, efficiency=-3_500, overlap=7_500)
    current_a = _assessment(failure=3_000, continuation=5_000)

    decision = decide_vt31_threat_response_v4(
        prior_observation=prior,
        prior_assessment=prior_a,
        previous_observation=previous,
        previous_assessment=previous_a,
        observation=current,
        assessment=current_a,
        shared_intelligence_ref="sti8:v4:test",
    )

    assert decision.action is Vt31ThreatConsumerAction.HOLD
    assert decision.reason_codes == ("V4_ONE_STEP_RECOVERY_VETO",)


def test_v4_holds_if_parent_v3_was_not_actionable() -> None:
    prior, prior_a, previous, previous_a = _v3_actionable_prefix()
    previous_a = _assessment(failure=6_000, continuation=4_000)
    current = _obs(3, signed_close=-4_500, efficiency=-3_500, overlap=7_500)
    current_a = _assessment(failure=7_500, continuation=2_500)

    decision = decide_vt31_threat_response_v4(
        prior_observation=prior,
        prior_assessment=prior_a,
        previous_observation=previous,
        previous_assessment=previous_a,
        observation=current,
        assessment=current_a,
        shared_intelligence_ref="sti8:v4:test",
    )

    assert decision.action is Vt31ThreatConsumerAction.HOLD
    assert decision.reason_codes == (
        "V4_PARENT_V3_NOT_ACTIONABLE_AT_T_MINUS_1",
    )


def test_v4_rejects_noncausal_next_observation() -> None:
    prior, prior_a, previous, previous_a = _v3_actionable_prefix()
    current = replace(previous, observation_id="v4-same-time")
    current_a = _assessment(failure=7_500, continuation=2_500)

    with pytest.raises(ValueError, match="must follow T-1 strictly"):
        decide_vt31_threat_response_v4(
            prior_observation=prior,
            prior_assessment=prior_a,
            previous_observation=previous,
            previous_assessment=previous_a,
            observation=current,
            assessment=current_a,
            shared_intelligence_ref="sti8:v4:test",
        )
