from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

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

T0 = datetime(2026, 9, 30, 16, 0, tzinfo=UTC)


def _obs(minute: int, *, close: int, efficiency: int) -> SharedPositionCausalObservation:
    return SharedPositionCausalObservation(
        observation_id=f"v4-{minute}",
        position_id="p-1",
        asset="NAS100",
        as_of=T0 + timedelta(minutes=minute),
        evidence_cutoff_at=T0 + timedelta(minutes=minute),
        minutes_since_fill=minute,
        progress_bps=2_000,
        signed_close_r_bps=close,
        efficiency_bps=efficiency,
        overlap_bps=8_000,
        signed_body_r_bps=-3_000,
        peer_confirmation_bps=2_000,
        breadth_bps=3_000,
        peer_transition_adverse_bps=8_000,
        world_support_bps=2_500,
        world_fragility_bps=8_500,
        data_integrity_bps=10_000,
        provenance_refs=("v4:test",),
    )


def _assessment(observation: SharedPositionCausalObservation) -> SharedPositionThreatEngineAssessment:
    return SharedPositionThreatEngineAssessment(
        threat_level=SharedPositionThreatLevel.HIGH,
        threat_scope=SharedPositionThreatScope.CROSS_ASSET_THREAT,
        threat_score_bps=8_000,
        continuation_support_bps=2_000,
        failure_hazard_bps=8_000,
        relationship_break_bps=8_000,
        systemic_stress_bps=8_000,
        uncertainty_bps=2_000,
        continuation_support=SharedSupportState.VERY_LOW,
        failure_hazard=SharedSupportState.STRONG,
        reason_codes=("HIGH_SOURCE_THREAT",),
    )


def test_v4_vetoes_when_next_causal_state_recovers() -> None:
    prior = _obs(1, close=-500, efficiency=-1_000)
    previous = _obs(2, close=-3_000, efficiency=-4_000)
    current = _obs(3, close=5_000, efficiency=5_000)
    decision = decide_vt31_threat_response_v4(
        prior_observation=prior,
        prior_assessment=_assessment(prior),
        previous_observation=previous,
        previous_assessment=_assessment(previous),
        observation=current,
        assessment=replace(
            _assessment(current),
            continuation_support_bps=8_000,
            failure_hazard_bps=2_000,
        ),
        shared_intelligence_ref="sti8:v4:test",
    )
    assert decision.action is Vt31ThreatConsumerAction.HOLD
    assert decision.reason_codes == ("V4_ONE_STEP_RECOVERY_VETO",)


def test_v4_acts_only_after_nonrecovery_confirmation() -> None:
    prior = _obs(1, close=-500, efficiency=-1_000)
    previous = _obs(2, close=-3_000, efficiency=-4_000)
    current = _obs(3, close=-4_000, efficiency=-5_000)
    decision = decide_vt31_threat_response_v4(
        prior_observation=prior,
        prior_assessment=_assessment(prior),
        previous_observation=previous,
        previous_assessment=_assessment(previous),
        observation=current,
        assessment=_assessment(current),
        shared_intelligence_ref="sti8:v4:test",
    )
    assert decision.action is Vt31ThreatConsumerAction.EXIT_NEXT_M1_OPEN
    assert decision.reason_codes == ("V4_ONE_STEP_NONRECOVERY_CONFIRMED",)


def test_v4_has_no_numeric_rescue_or_productive_authority() -> None:
    assert FROZEN_STI8_RESPONSE_V4.numeric_rescue_threshold_bps is None
    assert FROZEN_STI8_RESPONSE_V4.productive_authority is False
