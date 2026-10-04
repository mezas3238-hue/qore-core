"""Trader-owned STI-8 economic response V4 research policy.

V4 preserves the frozen V3 signal at T-1, then waits for one additional causal
source observation at T. Recovery of either local-failure margin or
failure-hazard-over-continuation vetoes the intervention. No threshold is
retuned and Shared receives no exit authority.
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
    require_parent_v3_actionable_at_t_minus_1: bool = True
    require_next_causal_observation: bool = True
    veto_if_local_margin_nonpositive: bool = True
    veto_if_hazard_margin_nonpositive: bool = True
    same_initial_entry_stop_target_required: bool = True
    sizing_mutation_allowed: bool = False
    stop_mutation_allowed: bool = False
    target_mutation_allowed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("V4 policy_id must be non-empty")
        if not all(
            (
                self.require_parent_v3_actionable_at_t_minus_1,
                self.require_next_causal_observation,
                self.veto_if_local_margin_nonpositive,
                self.veto_if_hazard_margin_nonpositive,
                self.same_initial_entry_stop_target_required,
            )
        ):
            raise ValueError("V4 frozen one-step recovery-veto law cannot be weakened")
        if (
            self.sizing_mutation_allowed
            or self.stop_mutation_allowed
            or self.target_mutation_allowed
            or self.productive_authority
        ):
            raise ValueError("V4 research consumer cannot mutate sovereign geometry")

    def fingerprint(self) -> str:
        raw = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
        )
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
    """Apply the preregistered one-step recovery veto without outcome access."""

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
            reason_codes=("V4_PARENT_V3_STATE_REQUIRED",),
        )
    if previous_observation.as_of >= observation.as_of:
        raise ValueError("V4 next causal observation must follow T-1 strictly")

    parent = decide_vt31_threat_response_v3(
        previous_observation=prior_observation,
        previous_assessment=prior_assessment,
        observation=previous_observation,
        assessment=previous_assessment,
        shared_intelligence_ref=shared_intelligence_ref,
    )
    if parent.action is not Vt31ThreatConsumerAction.EXIT_NEXT_M1_OPEN:
        return Vt31ThreatConsumerDecision(
            decision_time=observation.as_of,
            action=Vt31ThreatConsumerAction.HOLD,
            shared_intelligence_ref=shared_intelligence_ref,
            observed_threat_level=assessment.threat_level,
            reason_codes=("V4_PARENT_V3_NOT_ACTIONABLE_AT_T_MINUS_1",),
        )

    local_margin, hazard_margin = _margins(observation, assessment)
    recovered = local_margin <= 0 or hazard_margin <= 0
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
