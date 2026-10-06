"""Preregistered pre-outcome shadow ablation for CE2I T12.

T12 is not certified merely because all seven Trader lineages emit the common
CiboCapitalRegimeState schema. The scientific claim is narrower: regime-driven
tool eligibility must add fresh OOS utility.

This module preregisters a shadow control that keeps the exact same causal
decision evidence, mission, regime posture, MPC plan, provider economics,
candidates and downstream QORE Risk boundary. It neutralizes only the T12
intervention on enabled_tools by restoring the complete mission-eligible CE2I
surface before Phase20H allocation.

The control never reads outcomes and never receives runtime, Risk, execution,
DEMO-governed, LIVE, real-capital or merge authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from qore.infrastructure.cibo_account_capital_mission import (
    CiboCapitalMissionPolicy,
    eligible_ce2i_tool_codes_for_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardDecisionEvidence,
    Phase20ForwardDecisionRecord,
    phase20_forward_decision_record_sha256,
    phase20_forward_evidence_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_robust_allocator import (
    Phase20RobustAllocatorDecision,
    propose_phase20h_robust_allocation,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboRegimeToolSelection,
)

T12_SHADOW_POLICY_ID = (
    "CIBO_T12_REGIME_TOOL_ELIGIBILITY_SHADOW_ABLATION_V1"
)
T12_SHADOW_POLICY_FROZEN_AT = datetime(
    2026,
    9,
    29,
    15,
    0,
    tzinfo=UTC,
)


def t12_shadow_policy_sha256() -> str:
    payload = {
        "policy_id": T12_SHADOW_POLICY_ID,
        "frozen_at": T12_SHADOW_POLICY_FROZEN_AT.isoformat(),
        "treatment": (
            "frozen V3 regime-driven enabled_tools and blocked_tools"
        ),
        "control": (
            "same regime posture/reason; restore complete ordered "
            "mission-eligible CE2I enabled_tools; blocked_tools empty"
        ),
        "mpc": "reuse exact treatment MPC plan",
        "allocator": (
            "rerun Phase20H with identical causal candidates/headroom "
            "and control tool eligibility"
        ),
        "risk": "unchanged downstream sovereign QORE Risk",
        "outcome_aware": False,
        "runtime_authority": False,
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_phase20_t12_neutral_tool_eligibility_control(
    *,
    mission: CiboCapitalMissionPolicy,
    treatment: CiboRegimeToolSelection,
) -> CiboRegimeToolSelection:
    """Neutralize only T12 tool eligibility while preserving regime posture."""

    if not isinstance(mission, CiboCapitalMissionPolicy):
        raise CiboCapitalManagementError(
            "Phase20 T12 control requires canonical capital mission"
        )
    if not isinstance(treatment, CiboRegimeToolSelection):
        raise CiboCapitalManagementError(
            "Phase20 T12 control requires canonical treatment regime"
        )

    mission_tools = eligible_ce2i_tool_codes_for_mission(mission)
    if not set(treatment.enabled_tools).issubset(set(mission_tools)):
        raise CiboCapitalManagementError(
            "Phase20 T12 treatment surface exceeds mission eligibility"
        )

    return CiboRegimeToolSelection(
        posture=treatment.posture,
        enabled_tools=mission_tools,
        blocked_tools=(),
        reason=treatment.reason,
    )


@dataclass(frozen=True, slots=True)
class Phase20T12ToolEligibilityShadowDecision:
    policy_id: str
    policy_sha256: str
    policy_frozen_at: datetime
    decision_epoch_id: str
    decision_evidence_sha256: str
    baseline_policy_record_sha256: str
    treatment_enabled_tools: tuple[str, ...]
    treatment_blocked_tools: tuple[str, ...]
    control_enabled_tools: tuple[str, ...]
    control_blocked_tools: tuple[str, ...]
    treatment_allocator_disposition: str
    control_allocator_disposition: str
    treatment_allocator_applied_tools: tuple[str, ...]
    control_allocator_applied_tools: tuple[str, ...]
    treatment_selected_signal_fingerprints: tuple[str, ...]
    control_selected_signal_fingerprints: tuple[str, ...]
    selection_changed: bool
    allocator_changed: bool
    outcome_present_at_seal: bool = False
    runtime_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.policy_id != T12_SHADOW_POLICY_ID:
            raise CiboCapitalManagementError(
                "Phase20 T12 shadow policy identity drift"
            )
        if self.policy_sha256 != t12_shadow_policy_sha256():
            raise CiboCapitalManagementError(
                "Phase20 T12 shadow policy digest drift"
            )
        if self.policy_frozen_at != T12_SHADOW_POLICY_FROZEN_AT:
            raise CiboCapitalManagementError(
                "Phase20 T12 shadow policy freeze drift"
            )
        if not self.decision_epoch_id:
            raise CiboCapitalManagementError(
                "Phase20 T12 shadow decision epoch id is required"
            )
        for name in (
            "decision_evidence_sha256",
            "baseline_policy_record_sha256",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or not value.startswith("sha256:")
                or len(value) != 71
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T12 shadow {name} is invalid"
                )
        for name in (
            "treatment_enabled_tools",
            "treatment_blocked_tools",
            "control_enabled_tools",
            "control_blocked_tools",
            "treatment_allocator_applied_tools",
            "control_allocator_applied_tools",
            "treatment_selected_signal_fingerprints",
            "control_selected_signal_fingerprints",
        ):
            values = getattr(self, name)
            if len(values) != len(set(values)):
                raise CiboCapitalManagementError(
                    f"Phase20 T12 shadow {name} must be unique"
                )
        if set(self.treatment_enabled_tools) & set(
            self.treatment_blocked_tools
        ):
            raise CiboCapitalManagementError(
                "Phase20 T12 treatment tool may not be enabled and blocked"
            )
        if self.control_blocked_tools:
            raise CiboCapitalManagementError(
                "Phase20 T12 control must neutralize regime tool blocking"
            )
        if not set(self.treatment_enabled_tools).issubset(
            set(self.control_enabled_tools)
        ):
            raise CiboCapitalManagementError(
                "Phase20 T12 control must contain treatment enabled tools"
            )
        expected_selection_changed = (
            self.treatment_selected_signal_fingerprints
            != self.control_selected_signal_fingerprints
        )
        if self.selection_changed != expected_selection_changed:
            raise CiboCapitalManagementError(
                "Phase20 T12 selection-changed flag drift"
            )
        expected_allocator_changed = (
            self.treatment_allocator_disposition
            != self.control_allocator_disposition
            or self.treatment_allocator_applied_tools
            != self.control_allocator_applied_tools
            or expected_selection_changed
        )
        if self.allocator_changed != expected_allocator_changed:
            raise CiboCapitalManagementError(
                "Phase20 T12 allocator-changed flag drift"
            )
        if (
            self.outcome_present_at_seal
            or self.runtime_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "Phase20 T12 shadow experiment authority/causality drift"
            )


def evaluate_phase20_t12_shadow_decision(
    *,
    evidence: Phase20ForwardDecisionEvidence,
    treatment_record: Phase20ForwardDecisionRecord,
) -> tuple[
    Phase20T12ToolEligibilityShadowDecision,
    Phase20RobustAllocatorDecision,
]:
    """Evaluate the preregistered T12 control strictly before outcomes."""

    if not isinstance(evidence, Phase20ForwardDecisionEvidence):
        raise CiboCapitalManagementError(
            "Phase20 T12 shadow requires canonical forward evidence"
        )
    if not isinstance(treatment_record, Phase20ForwardDecisionRecord):
        raise CiboCapitalManagementError(
            "Phase20 T12 shadow requires canonical treatment record"
        )
    if evidence.decision_at < T12_SHADOW_POLICY_FROZEN_AT:
        raise CiboCapitalManagementError(
            "Phase20 T12 shadow cannot evaluate pre-freeze decisions"
        )
    if evidence.outcome_present:
        raise CiboCapitalManagementError(
            "Phase20 T12 shadow cannot evaluate evidence containing outcome"
        )

    evidence_sha = phase20_forward_evidence_sha256(evidence)
    if treatment_record.evidence_sha256 != evidence_sha:
        raise CiboCapitalManagementError(
            "Phase20 T12 treatment/evidence binding drift"
        )

    treatment_regime = treatment_record.regime
    control_regime = build_phase20_t12_neutral_tool_eligibility_control(
        mission=evidence.mission,
        treatment=treatment_regime,
    )

    # Preserve the exact treatment MPC plan. This experiment is only about
    # T12's regime-driven tool eligibility, not posture or optionality logic.
    mpc_plan = treatment_record.mpc_plan
    control_allocator = propose_phase20h_robust_allocation(
        mission=evidence.mission,
        regime=control_regime,
        hard_risk_headroom_usd=mpc_plan.deployable_stop_risk_usd,
        margin_headroom_usd=mpc_plan.deployable_margin_usd,
        concentration_limit_by_group=evidence.concentration_limit_by_group,
        candidates=tuple(item.candidate for item in evidence.candidates),
        known_options=(),
    )

    treatment_allocator = treatment_record.allocator_decision
    treatment_selected = _selected(treatment_allocator)
    control_selected = _selected(control_allocator)
    selection_changed = treatment_selected != control_selected
    allocator_changed = (
        treatment_allocator.disposition.value
        != control_allocator.disposition.value
        or treatment_allocator.applied_tools
        != control_allocator.applied_tools
        or selection_changed
    )

    shadow = Phase20T12ToolEligibilityShadowDecision(
        policy_id=T12_SHADOW_POLICY_ID,
        policy_sha256=t12_shadow_policy_sha256(),
        policy_frozen_at=T12_SHADOW_POLICY_FROZEN_AT,
        decision_epoch_id=evidence.decision_epoch_id,
        decision_evidence_sha256=evidence_sha,
        baseline_policy_record_sha256=(
            phase20_forward_decision_record_sha256(treatment_record)
        ),
        treatment_enabled_tools=treatment_regime.enabled_tools,
        treatment_blocked_tools=treatment_regime.blocked_tools,
        control_enabled_tools=control_regime.enabled_tools,
        control_blocked_tools=control_regime.blocked_tools,
        treatment_allocator_disposition=(
            treatment_allocator.disposition.value
        ),
        control_allocator_disposition=control_allocator.disposition.value,
        treatment_allocator_applied_tools=(
            treatment_allocator.applied_tools
        ),
        control_allocator_applied_tools=control_allocator.applied_tools,
        treatment_selected_signal_fingerprints=treatment_selected,
        control_selected_signal_fingerprints=control_selected,
        selection_changed=selection_changed,
        allocator_changed=allocator_changed,
    )
    return shadow, control_allocator


def _selected(
    decision: Phase20RobustAllocatorDecision,
) -> tuple[str, ...]:
    allocation = decision.allocation
    if allocation is None:
        return ()
    return allocation.selected_signal_fingerprints
