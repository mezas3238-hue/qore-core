from __future__ import annotations

from pytest import raises

from qore.infrastructure.cibo_account_capital_mission import (
    Ce2iActivationScope,
    CiboCapitalMission,
    CiboCapitalMissionPolicy,
    CiboCapitalObjective,
    eligible_ce2i_tool_codes_for_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_shadow_policy import (
    T12_SHADOW_POLICY_FROZEN_AT,
    T12_SHADOW_POLICY_ID,
    Phase20T12ToolEligibilityShadowDecision,
    build_phase20_t12_neutral_tool_eligibility_control,
    t12_shadow_policy_sha256,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboRegimePosture,
    CiboRegimeToolSelection,
)


def _mission() -> CiboCapitalMissionPolicy:
    return CiboCapitalMissionPolicy(
        mission=CiboCapitalMission.SANDBOX_SIMULATION,
        primary_objective=CiboCapitalObjective.SIMULATION,
        secondary_objective=CiboCapitalObjective.VALIDATION,
        ce2i_scope=Ce2iActivationScope.SIMULATION_ONLY,
        minimum_seed_required=True,
        sovereign_risk_required=True,
        provider_constraints_required=True,
        durable_capital_accounting_required=True,
        allow_research_tool_execution=True,
        allow_multi_tool_experiments=True,
        allow_cross_trader_competition=True,
        allow_self_financing_expansion=True,
        allow_original_base_capital_reallocation=True,
        capability_measurement_enabled=True,
        preserve_optionality_priority=True,
        rationale="T12 shadow unit-test mission",
    )


def test_t12_control_neutralizes_only_regime_tool_eligibility() -> None:
    mission = _mission()
    mission_tools = eligible_ce2i_tool_codes_for_mission(mission)
    treatment = CiboRegimeToolSelection(
        posture=CiboRegimePosture.DEFENSIVE,
        enabled_tools=("T03", "T08", "T10", "T11", "T13", "T14", "T15"),
        blocked_tools=tuple(
            code
            for code in mission_tools
            if code not in {"T03", "T08", "T10", "T11", "T13", "T14", "T15"}
        ),
        reason="current state requires defensive capital posture",
    )

    control = build_phase20_t12_neutral_tool_eligibility_control(
        mission=mission,
        treatment=treatment,
    )

    assert control.posture is treatment.posture
    assert control.reason == treatment.reason
    assert control.enabled_tools == mission_tools
    assert control.blocked_tools == ()
    assert treatment.enabled_tools != control.enabled_tools


def test_t12_shadow_contract_binds_policy_and_has_no_authority() -> None:
    sha = "sha256:" + "1" * 64
    shadow = Phase20T12ToolEligibilityShadowDecision(
        policy_id=T12_SHADOW_POLICY_ID,
        policy_sha256=t12_shadow_policy_sha256(),
        policy_frozen_at=T12_SHADOW_POLICY_FROZEN_AT,
        decision_epoch_id="epoch-1",
        decision_evidence_sha256=sha,
        baseline_policy_record_sha256="sha256:" + "2" * 64,
        treatment_enabled_tools=("T03",),
        treatment_blocked_tools=("T09",),
        control_enabled_tools=("T03", "T09"),
        control_blocked_tools=(),
        treatment_allocator_disposition="PRESERVE_CAPACITY",
        control_allocator_disposition="ALLOCATE",
        treatment_allocator_applied_tools=("T03",),
        control_allocator_applied_tools=("T03", "T09"),
        treatment_selected_signal_fingerprints=(),
        control_selected_signal_fingerprints=("signal-1",),
        selection_changed=True,
        allocator_changed=True,
    )

    assert shadow.decision_evidence_sha256 == sha
    assert shadow.outcome_present_at_seal is False
    assert shadow.runtime_authority is False
    assert shadow.risk_authority is False
    assert shadow.execution_authority is False


def test_t12_shadow_contract_fails_closed_on_outcome_presence() -> None:
    with raises(
        CiboCapitalManagementError,
        match="authority/causality drift",
    ):
        Phase20T12ToolEligibilityShadowDecision(
            policy_id=T12_SHADOW_POLICY_ID,
            policy_sha256=t12_shadow_policy_sha256(),
            policy_frozen_at=T12_SHADOW_POLICY_FROZEN_AT,
            decision_epoch_id="epoch-1",
            decision_evidence_sha256="sha256:" + "1" * 64,
            baseline_policy_record_sha256="sha256:" + "2" * 64,
            treatment_enabled_tools=("T03",),
            treatment_blocked_tools=(),
            control_enabled_tools=("T03",),
            control_blocked_tools=(),
            treatment_allocator_disposition="ALLOCATE",
            control_allocator_disposition="ALLOCATE",
            treatment_allocator_applied_tools=("T03",),
            control_allocator_applied_tools=("T03",),
            treatment_selected_signal_fingerprints=("signal-1",),
            control_selected_signal_fingerprints=("signal-1",),
            selection_changed=False,
            allocator_changed=False,
            outcome_present_at_seal=True,
        )
