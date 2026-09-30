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
from qore.infrastructure.traders.vt31_shared_threat_consumer_v3_research import (
    FROZEN_STI8_RESPONSE_V3,
    decide_vt31_threat_response_v3,
)

T0 = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)


def _obs(
    minute: int,
    *,
    signed_close: int,
    efficiency: int,
    overlap: int,
) -> SharedPositionCausalObservation:
    return SharedPositionCausalObservation(
        observation_id=f"obs-{minute}",
        trade_id="trade-001",
        asset="NAS100",
        as_of=T0 + timedelta(minutes=minute),
        evidence_cutoff_at=T0 + timedelta(minutes=minute),
        minutes_since_fill=minute,
        signed_close_r_bps=signed_close,
        signed_body_r_bps=signed_close,
        efficiency_bps=efficiency,
        overlap_bps=overlap,
        continuation_support_bps=3_000,
        failure_hazard_bps=7_000,
        world_support_bps=3_000,
        world_fragility_bps=7_000,
        peer_confirmation_bps=3_000,
        peer_transition_adverse_bps=7_000,
        breadth_bps=5_000,
        systemic_stress_bps=6_000,
        uncertainty_bps=2_000,
        data_integrity_bps=10_000,
        provenance_refs=("source:test",),
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


def test_v3_policy_is_non_productive_and_fingerprinted() -> None:
    assert FROZEN_STI8_RESPONSE_V3.productive_authority is False
    assert len(FROZEN_STI8_RESPONSE_V3.fingerprint()) == 64


def test_v3_requires_prior_causal_state() -> None:
    current = _obs(1, signed_close=-5_000, efficiency=-4_000, overlap=8_000)
    assessment = _assessment(failure=8_000, continuation=2_000)
    decision = decide_vt31_threat_response_v3(
        previous_observation=None,
        previous_assessment=None,
        observation=current,
        assessment=assessment,
        shared_intelligence_ref="shared:test",
    )
    assert decision.action is Vt31ThreatConsumerAction.HOLD


def test_v3_exits_only_on_joint_deterioration_trajectory() -> None:
    previous = _obs(1, signed_close=-2_000, efficiency=-1_000, overlap=6_000)
    current = _obs(2, signed_close=-5_000, efficiency=-4_000, overlap=8_000)
    previous_assessment = _assessment(failure=6_000, continuation=4_000)
    current_assessment = _assessment(failure=8_000, continuation=2_000)
    decision = decide_vt31_threat_response_v3(
        previous_observation=previous,
        previous_assessment=previous_assessment,
        observation=current,
        assessment=current_assessment,
        shared_intelligence_ref="shared:test",
    )
    assert decision.action is Vt31ThreatConsumerAction.EXIT_NEXT_M1_OPEN
    assert decision.reason_codes == (
        "V3_JOINT_LOCAL_AND_HAZARD_DETERIORATION",
    )


def test_v3_holds_when_hazard_margin_is_not_worsening() -> None:
    previous = _obs(1, signed_close=-2_000, efficiency=-1_000, overlap=6_000)
    current = _obs(2, signed_close=-5_000, efficiency=-4_000, overlap=8_000)
    previous_assessment = _assessment(failure=8_000, continuation=2_000)
    current_assessment = _assessment(failure=8_000, continuation=2_000)
    decision = decide_vt31_threat_response_v3(
        previous_observation=previous,
        previous_assessment=previous_assessment,
        observation=current,
        assessment=current_assessment,
        shared_intelligence_ref="shared:test",
    )
    assert decision.action is Vt31ThreatConsumerAction.HOLD


def test_v3_rejects_noncausal_previous_state() -> None:
    current = _obs(2, signed_close=-5_000, efficiency=-4_000, overlap=8_000)
    assessment = _assessment(failure=8_000, continuation=2_000)
    with pytest.raises(ValueError, match="strictly precede"):
        decide_vt31_threat_response_v3(
            previous_observation=replace(current, observation_id="same-time"),
            previous_assessment=assessment,
            observation=current,
            assessment=assessment,
            shared_intelligence_ref="shared:test",
        )
