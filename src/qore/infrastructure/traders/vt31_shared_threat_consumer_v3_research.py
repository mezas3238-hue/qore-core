"""Trader-owned STI-8 economic response V3 research policy.

V3 changes the response hypothesis, not Shared threat intelligence. A material
V2 response is acted on only when source-time local failure and
failure-hazard-over-continuation both worsen versus the immediately preceding
causal observation. This is a trajectory-sign hypothesis, not a numeric
threshold rescue.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from qore.infrastructure.core_stack_v2.shared_continuation_positive_tail_intelligence import (
    SharedPositionCausalObservation,
)
from qore.infrastructure.core_stack_v2.shared_position_threat_intelligence import (
    SharedPositionThreatEngineAssessment,
)
from qore.infrastructure.traders.vt31_shared_threat_consumer_research import (
    Vt31ThreatConsumerAction,
    Vt31ThreatConsumerDecision,
)
from qore.infrastructure.traders.vt31_shared_threat_consumer_v2_research import (
    decide_vt31_threat_response_v2,
    local_thesis_state,
)


@dataclass(frozen=True, slots=True)
class Vt31ThreatConsumerV3Policy:
    policy_id: str
    require_parent_v2_actionable: bool = True
    require_positive_local_failure_margin: bool = True
    require_positive_hazard_margin: bool = True
    require_local_failure_margin_worsening: bool = True
    require_hazard_margin_worsening: bool = True
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("V3 policy_id must be non-empty")
        if not all(
            (
                self.require_parent_v2_actionable,
                self.require_positive_local_failure_margin,
                self.require_positive_hazard_margin,
                self.require_local_failure_margin_worsening,
                self.require_hazard_margin_worsening,
            )
        ):
            raise ValueError("V3 frozen joint-deterioration law cannot be weakened")
        if self.productive_authority:
            raise ValueError("V3 research consumer cannot authorize production")

    def fingerprint(self) -> str:
        raw = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(raw.encode()).hexdigest()


FROZEN_STI8_RESPONSE_V3 = Vt31ThreatConsumerV3Policy(
    policy_id="VT31_STI8_JOINT_DETERIORATION_TRAJECTORY_RESPONSE_V3"
)


def _margins(
    observation: SharedPositionCausalObservation,
    assessment: SharedPositionThreatEngineAssessment,
) -> tuple[int, int]:
    resilience, failure = local_thesis_state(observation)
    local_margin = failure - resilience
    hazard_margin = (
        assessment.failure_hazard_bps - assessment.continuation_support_bps
    )
    return local_margin, hazard_margin


def decide_vt31_threat_response_v3(
    *,
    previous_observation: SharedPositionCausalObservation | None,
    previous_assessment: SharedPositionThreatEngineAssessment | None,
    observation: SharedPositionCausalObservation,
    assessment: SharedPositionThreatEngineAssessment,
    shared_intelligence_ref: str,
    policy: Vt31ThreatConsumerV3Policy = FROZEN_STI8_RESPONSE_V3,
) -> Vt31ThreatConsumerDecision:
    if not shared_intelligence_ref.strip():
        raise ValueError("V3 treatment requires Shared intelligence provenance")
    if (previous_observation is None) != (previous_assessment is None):
        raise ValueError("previous observation and assessment must be paired")

    parent = decide_vt31_threat_response_v2(
        observation=observation,
        assessment=assessment,
        shared_intelligence_ref=shared_intelligence_ref,
    )
    if parent.action is not Vt31ThreatConsumerAction.EXIT_NEXT_M1_OPEN:
        return Vt31ThreatConsumerDecision(
            decision_time=observation.as_of,
            action=Vt31ThreatConsumerAction.HOLD,
            shared_intelligence_ref=shared_intelligence_ref,
            observed_threat_level=assessment.threat_level,
            reason_codes=("V3_PARENT_V2_NOT_ACTIONABLE",),
        )

    if previous_observation is None or previous_assessment is None:
        return Vt31ThreatConsumerDecision(
            decision_time=observation.as_of,
            action=Vt31ThreatConsumerAction.HOLD,
            shared_intelligence_ref=shared_intelligence_ref,
            observed_threat_level=assessment.threat_level,
            reason_codes=("V3_PRIOR_CAUSAL_STATE_REQUIRED",),
        )
    if previous_observation.as_of >= observation.as_of:
        raise ValueError("V3 previous causal state must strictly precede current")

    current_local, current_hazard = _margins(observation, assessment)
    previous_local, previous_hazard = _margins(
        previous_observation,
        previous_assessment,
    )
    actionable = (
        current_local > 0
        and current_hazard > 0
        and current_local > previous_local
        and current_hazard > previous_hazard
    )
    reason = (
        "V3_JOINT_LOCAL_AND_HAZARD_DETERIORATION"
        if actionable
        else "V3_TRAJECTORY_COUNTERSIGNATURE_NOT_CONFIRMED"
    )
    return Vt31ThreatConsumerDecision(
        decision_time=observation.as_of,
        action=(
            Vt31ThreatConsumerAction.EXIT_NEXT_M1_OPEN
            if actionable
            else Vt31ThreatConsumerAction.HOLD
        ),
        shared_intelligence_ref=shared_intelligence_ref,
        observed_threat_level=assessment.threat_level,
        reason_codes=(reason,),
    )
