from qore.infrastructure.cibo_phase22_one_shot_guard import (
    EXECUTION_ECONOMICS_BLOCKER,
    SYNTHETIC_FORBIDDEN_BLOCKER,
    Phase22ExecutionConsumptionReceipt,
    Phase22OneShotGuardStatus,
    assess_phase22_one_shot_guard,
)
from qore.infrastructure.cibo_phase22_execution_manifest import (
    build_phase22_execution_manifest,
)


def test_one_shot_guard_fails_closed_without_realized_provider_settlement() -> None:
    assessment = assess_phase22_one_shot_guard()

    assert assessment.status is Phase22OneShotGuardStatus.BLOCKED
    assert EXECUTION_ECONOMICS_BLOCKER in assessment.blockers
    assert SYNTHETIC_FORBIDDEN_BLOCKER in assessment.blockers
    assert assessment.fresh_outcomes_already_emitted is False
    assert assessment.authorized_to_emit_first_fresh_outcome is False
    assert assessment.productive_authority is False
    assert len(assessment.store_paths) == 5


def test_consumed_receipt_prevents_second_fresh_execution() -> None:
    manifest = build_phase22_execution_manifest()
    receipt = Phase22ExecutionConsumptionReceipt(
        candidate_id=manifest.candidate_id,
        execution_manifest_sha256=manifest.fingerprint(),
        outcomes_emitted=True,
    )
    assessment = assess_phase22_one_shot_guard(
        consumption_receipt=receipt,
    )

    assert assessment.status is Phase22OneShotGuardStatus.CONSUMED
    assert assessment.fresh_outcomes_already_emitted is True
    assert assessment.authorized_to_emit_first_fresh_outcome is False
