"""Research-only VT31 consumer for Shared position-threat cognition.

Shared produces evidence. This module belongs to the Trader domain and owns the
research decision that consumes that evidence. It never grants Shared exit,
stop, target, Risk, sizing, capital or execution authority.

The first preregistered policy is deliberately simple and monotone: the same
material threat set already used by frozen STI-8 signal evaluation
(ELEVATED/HIGH/CRITICAL) causes the Trader research consumer to schedule an
EXIT at the next M1 open. All other states HOLD. Control and treatment use the
same consumer code; the control arm receives no proactive Shared assessment.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_position_threat_intelligence import (
    SharedPositionThreatEngineAssessment,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedPositionThreatLevel,
)


class Vt31ThreatConsumerAction(StrEnum):
    HOLD = "HOLD"
    EXIT_NEXT_M1_OPEN = "EXIT_NEXT_M1_OPEN"


@dataclass(frozen=True, slots=True)
class Vt31ThreatConsumerPolicy:
    policy_id: str
    exit_on_levels: tuple[SharedPositionThreatLevel, ...]
    decision_effective_next_m1_open: bool = True
    same_initial_entry_stop_target_required: bool = True
    sizing_mutation_allowed: bool = False
    stop_mutation_allowed: bool = False
    target_mutation_allowed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("threat consumer policy_id must be non-empty")
        canonical = tuple(
            sorted(set(self.exit_on_levels), key=lambda item: item.value)
        )
        if self.exit_on_levels != canonical:
            raise ValueError("exit_on_levels must be unique and canonical")
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
        if self.exit_on_levels != expected:
            raise ValueError(
                "STI-8 V1 economic policy must reuse the frozen material-threat set"
            )
        if not self.decision_effective_next_m1_open:
            raise ValueError("threat response must be effective only after decision close")
        if not self.same_initial_entry_stop_target_required:
            raise ValueError("economic comparison requires identical initial geometry")
        if (
            self.sizing_mutation_allowed
            or self.stop_mutation_allowed
            or self.target_mutation_allowed
            or self.productive_authority
        ):
            raise ValueError("research threat consumer cannot mutate sovereign geometry")

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["exit_on_levels"] = tuple(item.value for item in self.exit_on_levels)
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class Vt31ThreatConsumerDecision:
    decision_time: datetime
    action: Vt31ThreatConsumerAction
    shared_intelligence_ref: str | None
    observed_threat_level: SharedPositionThreatLevel | None
    reason_codes: tuple[str, ...]
    trader_owns_decision: bool = True
    shared_exit_authority: bool = False
    shared_stop_authority: bool = False
    shared_target_authority: bool = False
    future_outcome_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if (
            self.decision_time.tzinfo is None
            or self.decision_time.utcoffset() is None
        ):
            raise ValueError("threat consumer decision_time must be timezone-aware")
        if not self.reason_codes:
            raise ValueError("threat consumer decision requires reason codes")
        if (
            not self.trader_owns_decision
            or self.shared_exit_authority
            or self.shared_stop_authority
            or self.shared_target_authority
            or self.future_outcome_used
            or self.productive_authority
        ):
            raise ValueError("threat consumer sovereignty invariant violated")


FROZEN_STI8_ECONOMIC_POLICY_V1 = Vt31ThreatConsumerPolicy(
    policy_id="VT31_STI8_MATERIAL_THREAT_EXIT_NEXT_M1_OPEN_V1",
    exit_on_levels=tuple(
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


def decide_vt31_threat_response(
    *,
    decision_time: datetime,
    policy: Vt31ThreatConsumerPolicy = FROZEN_STI8_ECONOMIC_POLICY_V1,
    shared_assessment: SharedPositionThreatEngineAssessment | None,
    shared_intelligence_ref: str | None,
) -> Vt31ThreatConsumerDecision:
    """Return Trader-owned HOLD/EXIT research decision without outcome access."""

    if shared_assessment is None:
        if shared_intelligence_ref is not None:
            raise ValueError("control arm cannot provide Shared intelligence ref")
        return Vt31ThreatConsumerDecision(
            decision_time=decision_time,
            action=Vt31ThreatConsumerAction.HOLD,
            shared_intelligence_ref=None,
            observed_threat_level=None,
            reason_codes=("CONTROL_NO_PROACTIVE_SHARED_HOLD",),
        )

    if shared_intelligence_ref is None or not shared_intelligence_ref.strip():
        raise ValueError("treatment assessment requires Shared intelligence ref")

    level = shared_assessment.threat_level
    action = (
        Vt31ThreatConsumerAction.EXIT_NEXT_M1_OPEN
        if level in policy.exit_on_levels
        else Vt31ThreatConsumerAction.HOLD
    )
    return Vt31ThreatConsumerDecision(
        decision_time=decision_time,
        action=action,
        shared_intelligence_ref=shared_intelligence_ref,
        observed_threat_level=level,
        reason_codes=(
            ("MATERIAL_STI8_THREAT_TRADER_EXIT_NEXT_M1_OPEN",)
            if action is Vt31ThreatConsumerAction.EXIT_NEXT_M1_OPEN
            else ("STI8_NOT_MATERIAL_TRADER_HOLD",)
        ),
    )
