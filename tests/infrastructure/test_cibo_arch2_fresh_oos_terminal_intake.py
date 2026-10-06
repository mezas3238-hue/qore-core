from types import SimpleNamespace

import pytest

from qore.infrastructure.cibo_arch2_fresh_oos_terminal_intake import (
    COMPLETED,
    FALSIFIED,
    build_arch2_fresh_oos_terminal_intake,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification import (
    Phase20QualificationStatus,
)
from qore.infrastructure.cibo_ce2i_phase22_holdout_gate import (
    Phase22HoldoutLineageAssessment,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification import (
    Phase22HoldoutQualificationReport,
    Phase22HoldoutQualificationStatus,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification_plan import (
    FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN,
    phase22_holdout_qualification_plan_sha256,
)
from qore.infrastructure.cibo_phase22_consumption_ledger import (
    Phase22ExecutionConsumptionReceipt,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    CANDIDATE_ID,
)


def _consumption(*, outcomes_emitted: bool = True) -> Phase22ExecutionConsumptionReceipt:
    return Phase22ExecutionConsumptionReceipt(
        candidate_id=CANDIDATE_ID,
        execution_manifest_sha256="sha256:" + "1" * 64,
        outcomes_emitted=outcomes_emitted,
        claim_committed=True,
        claim_head_sha="2" * 40,
        claim_run_id=123,
        claim_run_attempt=1,
        outcome_bundle_sha256=(
            "sha256:" + "3" * 64 if outcomes_emitted else None
        ),
    )


def _lineage(*, valid: bool = True) -> Phase22HoldoutLineageAssessment:
    return Phase22HoldoutLineageAssessment(
        lineage_valid=valid,
        reasons=() if valid else ("BAD_LINEAGE",),
        decision_epochs=80,
        policy_decisions=80,
        outcomes=200,
        collector_git_shas=("4" * 40,),
        earliest_decision_at=None,
        latest_decision_at=None,
        economic_holdout_passed=False,
    )


def _report(
    status: Phase22HoldoutQualificationStatus,
    *,
    lineage_valid: bool = True,
) -> Phase22HoldoutQualificationReport:
    report = object.__new__(Phase22HoldoutQualificationReport)
    object.__setattr__(report, "status", status)
    object.__setattr__(
        report,
        "plan_id",
        FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN.plan_id,
    )
    object.__setattr__(
        report,
        "plan_sha256",
        phase22_holdout_qualification_plan_sha256(),
    )
    object.__setattr__(report, "lineage", _lineage(valid=lineage_valid))
    economic_status = (
        Phase20QualificationStatus.PASS
        if status is Phase22HoldoutQualificationStatus.PASS
        else Phase20QualificationStatus.FAIL
    )
    object.__setattr__(
        report,
        "economic_report",
        (
            SimpleNamespace(status=economic_status)
            if status in {
                Phase22HoldoutQualificationStatus.PASS,
                Phase22HoldoutQualificationStatus.FAIL,
            }
            else None
        ),
    )
    object.__setattr__(
        report,
        "failures",
        () if status is Phase22HoldoutQualificationStatus.PASS else ("gate",),
    )
    return report


def test_fresh_oos_pass_recommends_completed_without_rerun() -> None:
    result = build_arch2_fresh_oos_terminal_intake(
        consumption=_consumption(),
        qualification=_report(Phase22HoldoutQualificationStatus.PASS),
    )

    assert result.fresh_oos_terminal_ready is True
    assert result.terminal_recommendation == COMPLETED
    assert result.rerun_authorized is False
    assert result.canonical_ledger_modified is False
    assert result.productive_authority is False


def test_fresh_oos_fail_recommends_falsified_without_rescue() -> None:
    result = build_arch2_fresh_oos_terminal_intake(
        consumption=_consumption(),
        qualification=_report(Phase22HoldoutQualificationStatus.FAIL),
    )

    assert result.fresh_oos_terminal_ready is True
    assert result.terminal_recommendation == FALSIFIED
    assert result.rerun_authorized is False


def test_fresh_oos_not_ready_remains_nonterminal() -> None:
    result = build_arch2_fresh_oos_terminal_intake(
        consumption=_consumption(),
        qualification=_report(Phase22HoldoutQualificationStatus.NOT_READY),
    )

    assert result.fresh_oos_terminal_ready is False
    assert result.terminal_recommendation is None


def test_fresh_oos_requires_consumed_one_shot() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="emitted fresh outcomes",
    ):
        build_arch2_fresh_oos_terminal_intake(
            consumption=_consumption(outcomes_emitted=False),
            qualification=_report(Phase22HoldoutQualificationStatus.PASS),
        )
