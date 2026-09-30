"""Trader-owned STI-8 economic response V2.

V2 does not change Shared threat intelligence. It changes the Trader research
hypothesis: material Shared threat becomes actionable only when local thesis
evidence also deteriorates, with response conditional on threat scope.
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
    SharedPositionThreatScope,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedPositionThreatLevel,
)
from qore.infrastructure.traders.vt31_shared_threat_consumer_research import (
    Vt31ThreatConsumerAction,
    Vt31ThreatConsumerDecision,
)


@dataclass(frozen=True, slots=True)
class Vt31ThreatConsumerV2Policy:
    policy_id: str
    material_levels: tuple[SharedPositionThreatLevel, ...]
    productive_authority: bool = False

    def __post_init__(self) -> None:
        expected = tuple(
            sorted(
                (
                    SharedPositionThreatLevel.ELEVATED,
                    SharedPositionThreatLevel.HIGH,
                    SharedPositionThreatLevel.CRITICAL,
                ),
                key=lambda item: item.value,
            )
        )
        if not self.policy_id.strip() or self.material_levels != expected:
            raise ValueError("V2 must retain the exact frozen STI-8 material set")
        if self.productive_authority:
            raise ValueError("V2 research consumer cannot authorize production")

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["material_levels"] = tuple(
            item.value for item in self.material_levels
        )
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


FROZEN_STI8_RESPONSE_V2 = Vt31ThreatConsumerV2Policy(
    policy_id="VT31_STI8_LOCAL_RESILIENCE_SCOPE_RESPONSE_V2",
    material_levels=tuple(
        sorted(
            (
                SharedPositionThreatLevel.ELEVATED,
                SharedPositionThreatLevel.HIGH,
                SharedPositionThreatLevel.CRITICAL,
            ),
            key=lambda item: item.value,
        )
    ),
)


def local_thesis_state(
    observation: SharedPositionCausalObservation,
) -> tuple[int, int]:
    """Return source-time local resilience and local failure scores."""

    resilience = (
        max(0, observation.signed_close_r_bps)
        + max(0, observation.efficiency_bps)
    ) // 2
    failure = (
        max(0, -observation.signed_close_r_bps)
        + max(0, -observation.efficiency_bps)
        + observation.overlap_bps
    ) // 3
    return resilience, failure


def decide_vt31_threat_response_v2(
    *,
    observation: SharedPositionCausalObservation,
    assessment: SharedPositionThreatEngineAssessment,
    shared_intelligence_ref: str,
    policy: Vt31ThreatConsumerV2Policy = FROZEN_STI8_RESPONSE_V2,
) -> Vt31ThreatConsumerDecision:
    if not shared_intelligence_ref.strip():
        raise ValueError("V2 treatment requires Shared intelligence provenance")

    level = assessment.threat_level
    if level not in policy.material_levels:
        action = Vt31ThreatConsumerAction.HOLD
        reason = "STI8_NOT_MATERIAL_TRADER_HOLD"
    else:
        resilience, failure = local_thesis_state(observation)
        failure_dominates_continuation = (
            assessment.failure_hazard_bps
            >= assessment.continuation_support_bps
        )

        if assessment.threat_scope is SharedPositionThreatScope.LOCAL_ASSET_THREAT:
            actionable = failure >= resilience
            reason = (
                "LOCAL_THREAT_WITH_LOCAL_FAILURE"
                if actionable
                else "LOCAL_THREAT_BUT_LOCAL_RESILIENCE"
            )
        elif (
            assessment.threat_scope
            is SharedPositionThreatScope.CROSS_ASSET_THREAT
        ):
            actionable = (
                failure > resilience
                and failure_dominates_continuation
            )
            reason = (
                "CROSS_ASSET_THREAT_CONFIRMED_BY_LOCAL_FAILURE"
                if actionable
                else "CROSS_ASSET_THREAT_VETOED_BY_LOCAL_RESILIENCE"
            )
        else:
            actionable = (
                failure > resilience
                or (
                    level is SharedPositionThreatLevel.CRITICAL
                    and failure_dominates_continuation
                )
            )
            reason = (
                "SYSTEMIC_THREAT_CONFIRMED"
                if actionable
                else "SYSTEMIC_THREAT_VETOED_BY_LOCAL_RESILIENCE"
            )

        action = (
            Vt31ThreatConsumerAction.EXIT_NEXT_M1_OPEN
            if actionable
            else Vt31ThreatConsumerAction.HOLD
        )

    return Vt31ThreatConsumerDecision(
        decision_time=observation.as_of,
        action=action,
        shared_intelligence_ref=shared_intelligence_ref,
        observed_threat_level=level,
        reason_codes=(reason,),
    )
