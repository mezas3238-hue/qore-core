from qore.infrastructure.cibo_phase22_execution_manifest import (
    build_phase22_execution_manifest,
)
from qore.infrastructure.cibo_phase22_one_shot_guard import (
    DURABLE_CLAIM_BLOCKER,
    EXECUTION_ECONOMICS_BLOCKER,
    SYNTHETIC_FORBIDDEN_BLOCKER,
    Phase22ExecutionConsumptionReceipt,
    Phase22OneShotGuardStatus,
    assess_phase22_one_shot_guard,
)


def test_one_shot_guard_accepts_frozen_dual_evidence_without_fake_history() -> None:
    assessment = assess_phase22_one_shot_guard()

    assert assessment.status is Phase22OneShotGuardStatus.READY
    assert EXECUTION_ECONOMICS_BLOCKER not in assessment.blockers
    assert SYNTHETIC_FORBIDDEN_BLOCKER not in assessment.blockers
    assert assessment.blockers == ()
    assert assessment.execution_claimed is False
    assert assessment.fresh_outcomes_already_emitted is False
    assert assessment.authorized_to_emit_first_fresh_outcome is True
    assert assessment.productive_authority is False
    assert len(assessment.store_paths) == 5


def test_durable_claim_prevents_rerun_before_outcome_emission() -> None:
    manifest = build_phase22_execution_manifest()
    receipt = Phase22ExecutionConsumptionReceipt(
        candidate_id=manifest.candidate_id,
        execution_manifest_sha256=manifest.fingerprint(),
        outcomes_emitted=False,
        claim_committed=True,
        claim_head_sha="a" * 40,
        claim_run_id=123,
        claim_run_attempt=1,
    )
    assessment = assess_phase22_one_shot_guard(
        consumption_receipt=receipt,
    )

    assert assessment.status is Phase22OneShotGuardStatus.CLAIMED
    assert DURABLE_CLAIM_BLOCKER in assessment.blockers
    assert assessment.execution_claimed is True
    assert assessment.fresh_outcomes_already_emitted is False
    assert assessment.authorized_to_emit_first_fresh_outcome is False


def test_consumed_receipt_prevents_second_fresh_execution() -> None:
    manifest = build_phase22_execution_manifest()
    receipt = Phase22ExecutionConsumptionReceipt(
        candidate_id=manifest.candidate_id,
        execution_manifest_sha256=manifest.fingerprint(),
        outcomes_emitted=True,
        claim_committed=True,
        claim_head_sha="b" * 40,
        claim_run_id=456,
        claim_run_attempt=1,
        outcome_bundle_sha256="sha256:" + "c" * 64,
    )
    assessment = assess_phase22_one_shot_guard(
        consumption_receipt=receipt,
    )

    assert assessment.status is Phase22OneShotGuardStatus.CONSUMED
    assert assessment.execution_claimed is True
    assert assessment.fresh_outcomes_already_emitted is True
    assert assessment.authorized_to_emit_first_fresh_outcome is False
