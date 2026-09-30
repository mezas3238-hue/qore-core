"""Trader-owned STI-8 economic response V4 research policy.

V4 is a one-step recovery veto over V3. It does not change Shared threat
intelligence. A V3-actionable state at t-1 becomes actionable at t only if the
next causal observation does not recover either local-failure or
failure-hazard-over-continuation back to non-positive territory.
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
from qore.infrastructure.traders.vt31_shared_threat_consumer_v3_research import (
    _margins,
    decide_vt31_threat_response_v3,
)


@dataclass(frozen=True, slots=True)
class Vt31ThreatConsumerV4Policy:
    policy_id: str
    require_parent_v3_actionable_previous_step: bool = True
    veto_on_local_margin_recovery_to_nonpositive: bool = True
    veto_on_hazard_margin_recovery_to_nonpositive: bool = True
    numeric_rescue_threshold_bps: int | None = None
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("V4 policy_id must be non-empty")
        if not all(
            (
                self.require_parent_v3_actionable_previous_step,
                self.veto_on_local_margin_recovery_to_nonpositive,
                self.veto_on_hazard_margin_recovery_to_nonpositive,
            )
        ):
            raise ValueError("V4 frozen recovery-veto law cannot be weakened")
        if self.numeric_rescue_threshold_bps is not None:
            raise ValueError("V4 forbids numeric rescue threshold")
        if self.productive_authority:
            raise ValueError("V4 research consumer cannot authorize production")

    def fingerprint(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


FROZEN_STI8_RESPONSE_V4 = Vt31ThreatConsumerV4Policy(
    policy_id="VT31_STI8_ONE_STEP_RECOVERY_VETO_RESPONSE_V4"
)


def decide_vt31_threat_response_v4(
    *,
    prior_observation: SharedPositionCausalObservation | None,
    prior_assessment: SharedPositionThreatEngineAssessment | None,
    previous_observation: SharedPositionCausalObservation | None,
    previous_assessment: SharedPositionThreatEngineAssessment | None,
    observation: SharedPositionCausalObservation,
    assessment: SharedPositionThreatEngineAssessment,
    shared_intelligence_ref: str,
    policy: Vt31ThreatConsumerV4Policy = FROZEN_STI8_RESPONSE_V4,
) -> Vt31ThreatConsumerDecision:
    if not shared_intelligence_ref.strip():
        raise ValueError("V4 treatment requires Shared intelligence provenance")
    if (prior_observation is None) != (prior_assessment is None):
        raise ValueError("prior observation and assessment must be paired")
    if (previous_observation is None) != (previous_assessment is None):
        raise ValueError("previous observation and assessment must be paired")
    if previous_observation is None or previous_assessment is None:
        return Vt31ThreatConsumerDecision(
            decision_time=observation.as_of,
            action=Vt31ThreatConsumerAction.HOLD,
            shared_intelligence_ref=shared_intelligence_ref,
            observed_threat_level=assessment.threat_level,
            reason_codes=("V4_PREVIOUS_CAUSAL_STATE_REQUIRED",),
        )

    previous_v3 = decide_vt31_threat_response_v3(
        previous_observation=prior_observation,
        previous_assessment=prior_assessment,
        observation=previous_observation,
        assessment=previous_assessment,
        shared_intelligence_ref=shared_intelligence_ref,
    )
    if previous_v3.action is not Vt31ThreatConsumerAction.EXIT_NEXT_M1_OPEN:
        return Vt31ThreatConsumerDecision(
            decision_time=observation.as_of,
            action=Vt31ThreatConsumerAction.HOLD,
            shared_intelligence_ref=shared_intelligence_ref,
            observed_threat_level=assessment.threat_level,
            reason_codes=("V4_PARENT_V3_PREVIOUS_STEP_NOT_ACTIONABLE",),
        )
    if previous_observation.as_of >= observation.as_of:
        raise ValueError("V4 confirmation state must strictly follow V3 state")

    current_local, current_hazard = _margins(observation, assessment)
    recovered = current_local <= 0 or current_hazard <= 0
    return Vt31ThreatConsumerDecision(
        decision_time=observation.as_of,
        action=(
            Vt31ThreatConsumerAction.HOLD
            if recovered
            else Vt31ThreatConsumerAction.EXIT_NEXT_M1_OPEN
        ),
        shared_intelligence_ref=shared_intelligence_ref,
        observed_threat_level=assessment.threat_level,
        reason_codes=(
            ("V4_ONE_STEP_RECOVERY_VETO",)
            if recovered
            else ("V4_ONE_STEP_NONRECOVERY_CONFIRMED",)
        ),
    )
