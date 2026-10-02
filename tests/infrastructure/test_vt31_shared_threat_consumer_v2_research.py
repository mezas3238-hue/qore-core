from __future__ import annotations

from datetime import UTC, datetime

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
from qore.infrastructure.traders.vt31_shared_threat_consumer_v2_research import (
    FROZEN_STI8_RESPONSE_V2,
    decide_vt31_threat_response_v2,
    local_thesis_state,
)

T0 = datetime(2026, 9, 30, 4, 10, tzinfo=UTC)


def _observation(*, close: int, efficiency: int, overlap: int) -> SharedPositionCausalObservation:
    return SharedPositionCausalObservation(
        observation_id="v2-test",
        position_id="p1",
        asset="NAS100",
        as_of=T0,
        evidence_cutoff_at=T0,
        minutes_since_fill=5,
        progress_bps=max(0, close),
        signed_close_r_bps=close,
        efficiency_bps=efficiency,
        overlap_bps=overlap,
        signed_body_r_bps=close,
        peer_confirmation_bps=5_000,
        breadth_bps=5_000,
        peer_transition_adverse_bps=7_000,
        world_support_bps=4_000,
        world_fragility_bps=7_000,
        data_integrity_bps=10_000,
        provenance_refs=("source-only-v2",),
    )


def _assessment(
    *,
    scope: SharedPositionThreatScope,
    level: SharedPositionThreatLevel = SharedPositionThreatLevel.HIGH,
    continuation: int = 3_000,
    failure: int = 7_000,
) -> SharedPositionThreatEngineAssessment:
    return SharedPositionThreatEngineAssessment(
        threat_level=level,
        threat_scope=scope,
        threat_score_bps=7_500,
        continuation_support_bps=continuation,
        failure_hazard_bps=failure,
        relationship_break_bps=7_000,
        systemic_stress_bps=6_500,
        uncertainty_bps=2_000,
        continuation_support=SharedSupportState.LOW,
        failure_hazard=SharedSupportState.ELEVATED,
        reason_codes=("SOURCE_THREAT",),
    )


def test_local_resilience_is_source_only_and_relative() -> None:
    resilient = _observation(close=4_000, efficiency=3_000, overlap=2_000)
    weak = _observation(close=-3_000, efficiency=-2_000, overlap=8_000)

    resilient_state = local_thesis_state(resilient)
    weak_state = local_thesis_state(weak)

    assert resilient_state[0] > resilient_state[1]
    assert weak_state[1] > weak_state[0]


def test_cross_asset_threat_is_vetoed_by_local_resilience() -> None:
    decision = decide_vt31_threat_response_v2(
        observation=_observation(close=4_000, efficiency=3_000, overlap=2_000),
        assessment=_assessment(scope=SharedPositionThreatScope.CROSS_ASSET_THREAT),
        shared_intelligence_ref="sti8:v2:test",
    )
    assert decision.action is Vt31ThreatConsumerAction.HOLD
    assert decision.shared_exit_authority is False


def test_cross_asset_threat_exits_only_with_local_failure_confirmation() -> None:
    decision = decide_vt31_threat_response_v2(
        observation=_observation(close=-3_000, efficiency=-2_000, overlap=8_000),
        assessment=_assessment(scope=SharedPositionThreatScope.CROSS_ASSET_THREAT),
        shared_intelligence_ref="sti8:v2:test",
    )
    assert decision.action is Vt31ThreatConsumerAction.EXIT_NEXT_M1_OPEN
    assert decision.trader_owns_decision is True


def test_local_threat_requires_local_failure() -> None:
    hold = decide_vt31_threat_response_v2(
        observation=_observation(close=4_000, efficiency=3_000, overlap=2_000),
        assessment=_assessment(scope=SharedPositionThreatScope.LOCAL_ASSET_THREAT),
        shared_intelligence_ref="sti8:v2:local",
    )
    exit_ = decide_vt31_threat_response_v2(
        observation=_observation(close=-3_000, efficiency=-2_000, overlap=8_000),
        assessment=_assessment(scope=SharedPositionThreatScope.LOCAL_ASSET_THREAT),
        shared_intelligence_ref="sti8:v2:local",
    )
    assert hold.action is Vt31ThreatConsumerAction.HOLD
    assert exit_.action is Vt31ThreatConsumerAction.EXIT_NEXT_M1_OPEN


def test_nonmaterial_threat_never_acts() -> None:
    decision = decide_vt31_threat_response_v2(
        observation=_observation(close=-5_000, efficiency=-5_000, overlap=9_000),
        assessment=_assessment(
            scope=SharedPositionThreatScope.LOCAL_ASSET_THREAT,
            level=SharedPositionThreatLevel.MODERATE,
        ),
        shared_intelligence_ref="sti8:v2:moderate",
    )
    assert decision.action is Vt31ThreatConsumerAction.HOLD


def test_v2_retains_frozen_v1_material_threat_set() -> None:
    assert tuple(level.value for level in FROZEN_STI8_RESPONSE_V2.material_levels) == (
        "CRITICAL",
        "ELEVATED",
        "HIGH",
    )
    assert len(FROZEN_STI8_RESPONSE_V2.fingerprint()) == 64
    assert FROZEN_STI8_RESPONSE_V2.productive_authority is False
