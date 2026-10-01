from qore.infrastructure.cibo_ce2i_pre_holdout_freeze_v2 import (
    PARITY_BLOCKER,
    CiboPhase22V2PreHoldoutState,
    evaluate_phase22_v2_pre_holdout_readiness,
)


def test_v2_pre_holdout_is_locked_until_exact_7_of_7_parity() -> None:
    readiness = evaluate_phase22_v2_pre_holdout_readiness()

    assert readiness.state is CiboPhase22V2PreHoldoutState.LOCKED_PENDING_PARITY
    assert readiness.candidate_id == (
        "CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2"
    )
    assert readiness.blockers == (PARITY_BLOCKER,)
    assert readiness.parity_manifest_sha256 is None
    assert readiness.burn_clean is True
    assert readiness.source_stage_outcomes_inspected is False
    assert readiness.source_stage_trader_logic_executed is False
    assert readiness.ready_to_unseal_v2 is False
    assert readiness.productive_authority is False


def test_v2_pre_holdout_binds_all_frozen_governance_planes() -> None:
    readiness = evaluate_phase22_v2_pre_holdout_readiness()

    assert readiness.source_receipt_sha256.startswith("sha256:")
    assert readiness.phase21_policy_freeze_sha256.startswith("sha256:")
    assert len(readiness.phase21_policy_freeze_head_sha) == 40
    assert readiness.calibration_freeze_sha256.startswith("sha256:")
    assert readiness.provider_core_freeze_sha256.startswith("sha256:")
    assert len(readiness.candidate_code_sha) == 40
    assert readiness.candidate_parameter_sha256.startswith("sha256:")
    assert readiness.qualification_plan_sha256.startswith("sha256:")
