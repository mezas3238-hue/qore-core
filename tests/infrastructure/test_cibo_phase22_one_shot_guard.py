from unittest.mock import patch

from qore.infrastructure.cibo_phase22_execution_manifest import (
    build_phase22_execution_manifest,
)
from qore.infrastructure.cibo_phase22_git_durable_claim import (
    Phase22GitDurableClaimEvidence,
)
from qore.infrastructure.cibo_phase22_one_shot_guard import (
    DURABLE_CLAIM_BLOCKER,
    EXECUTION_ECONOMICS_BLOCKER,
    SYNTHETIC_FORBIDDEN_BLOCKER,
    Phase22ExecutionConsumptionReceipt,
    Phase22OneShotGuardStatus,
    assess_phase22_one_shot_guard,
)


def test_one_shot_guard_reflects_canonical_consumed_truth() -> None:
    assessment = assess_phase22_one_shot_guard()

    assert assessment.status is Phase22OneShotGuardStatus.CONSUMED
    assert assessment.execution_claimed is True
    assert assessment.fresh_outcomes_already_emitted is True
    assert assessment.authorized_to_create_durable_claim is False
    assert assessment.authorized_to_emit_first_fresh_outcome is False
    assert assessment.productive_authority is False
    assert len(assessment.store_paths) == 5


def test_one_shot_guard_ready_fixture_without_canonical_receipt() -> None:
    with patch(
        "qore.infrastructure.cibo_phase22_one_shot_guard."
        "load_phase22_execution_consumption_receipt",
        return_value=None,
    ):
        assessment = assess_phase22_one_shot_guard()

    assert assessment.status is Phase22OneShotGuardStatus.READY
    assert EXECUTION_ECONOMICS_BLOCKER not in assessment.blockers
    assert SYNTHETIC_FORBIDDEN_BLOCKER not in assessment.blockers
    assert assessment.blockers == ()
    assert assessment.execution_claimed is False
    assert assessment.fresh_outcomes_already_emitted is False
    assert assessment.durable_claim_proven is False
    assert assessment.authorized_to_create_durable_claim is True
    assert assessment.authorized_to_emit_first_fresh_outcome is False
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
    assert assessment.durable_claim_proven is False
    assert assessment.authorized_to_create_durable_claim is False
    assert assessment.authorized_to_emit_first_fresh_outcome is False


def test_remote_durable_claim_is_required_to_authorize_first_fresh_outcome() -> None:
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
    evidence = Phase22GitDurableClaimEvidence(
        source_head_sha="a" * 40,
        claim_commit_sha="b" * 40,
        remote_head_sha="b" * 40,
        branch_name="agent/cibo-integrator-ab-001",
        claim_receipt_sha256="sha256:" + "c" * 64,
        claim_file_sha256="sha256:" + "d" * 64,
        consumption_file_sha256="sha256:" + "e" * 64,
        changed_paths=(
            "docs/research/CIBO-PHASE22-V2-CONSUMPTION-RECEIPT.json",
            "docs/research/CIBO-PHASE22-V2-ONE-SHOT-CLAIM.json",
        ),
        parent_claim_files_absent=True,
        working_tree_clean=True,
        remote_claim_observed=True,
        durable_claim_proven=True,
    )

    assessment = assess_phase22_one_shot_guard(
        consumption_receipt=receipt,
        durable_claim_evidence=evidence,
    )

    assert assessment.status is Phase22OneShotGuardStatus.CLAIMED
    assert assessment.execution_claimed is True
    assert assessment.durable_claim_proven is True
    assert assessment.authorized_to_create_durable_claim is False
    assert assessment.authorized_to_emit_first_fresh_outcome is True


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
    assert assessment.durable_claim_proven is False
    assert assessment.authorized_to_create_durable_claim is False
    assert assessment.authorized_to_emit_first_fresh_outcome is False
