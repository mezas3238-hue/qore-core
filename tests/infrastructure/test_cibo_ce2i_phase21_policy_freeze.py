from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_phase21_policy_freeze import (
    Phase21EmpiricalValidationKind,
    Phase21EmpiricalValidationReceipt,
    Phase21PolicySurfaceDigests,
    Phase21QualificationReceipt,
    build_phase21_policy_freeze,
)

QUALIFIED_AT = datetime(2026, 10, 26, 20, 0, tzinfo=UTC)


def _sha(index: int) -> str:
    return f"sha256:{index:064x}"


def _qualification() -> Phase21QualificationReceipt:
    candidate = FROZEN_PHASE20_POLICY_CANDIDATE
    return Phase21QualificationReceipt(
        candidate_id=candidate.candidate_id,
        candidate_parameter_sha256=candidate.parameter_sha256(),
        plan_id=FROZEN_PHASE20D_QUALIFICATION_PLAN.plan_id,
        plan_sha256=phase20d_qualification_plan_sha256(),
        evidence_store_sha256=_sha(1),
        policy_store_sha256=_sha(2),
        qualification_artifact_sha256=_sha(3),
        qualified_at=QUALIFIED_AT,
        passed=True,
    )


def _validation(
    kind: Phase21EmpiricalValidationKind,
    *,
    offset_hours: int,
) -> Phase21EmpiricalValidationReceipt:
    candidate = FROZEN_PHASE20_POLICY_CANDIDATE
    return Phase21EmpiricalValidationReceipt(
        kind=kind,
        candidate_id=candidate.candidate_id,
        candidate_parameter_sha256=candidate.parameter_sha256(),
        qualification_artifact_sha256=_sha(3),
        evidence_class="FORWARD_EMPIRICAL",
        artifact_sha256=_sha(10 + offset_hours),
        observed_at=QUALIFIED_AT + timedelta(hours=offset_hours),
        passed=True,
    )


def _validations() -> tuple[Phase21EmpiricalValidationReceipt, ...]:
    return (
        _validation(
            Phase21EmpiricalValidationKind.CAPITAL_STATE_MONTE_CARLO,
            offset_hours=1,
        ),
        _validation(
            Phase21EmpiricalValidationKind.PROVIDER_STRESS,
            offset_hours=2,
        ),
        _validation(
            Phase21EmpiricalValidationKind.INTERACTION_ABLATION,
            offset_hours=3,
        ),
    )


def _surface() -> Phase21PolicySurfaceDigests:
    return Phase21PolicySurfaceDigests(
        state_machine_sha256=_sha(101),
        tool_registry_sha256=_sha(102),
        eligibility_sha256=_sha(103),
        source_ledger_sha256=_sha(104),
        trader_adapters_sha256=_sha(105),
        provider_profiles_sha256=_sha(106),
    )


def test_phase21_freeze_requires_complete_forward_empirical_lineage() -> None:
    manifest = build_phase21_policy_freeze(
        qualification=_qualification(),
        empirical_validations=_validations(),
        policy_surface=_surface(),
        frozen_at=QUALIFIED_AT + timedelta(hours=4),
    )

    assert manifest.candidate_id == (
        FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id
    )
    assert manifest.manifest_sha256().startswith("sha256:")
    assert len(manifest.manifest_sha256()) == 71
    assert manifest.demo_execution_authorized is False
    assert manifest.live_authorized is False
    assert manifest.real_capital_authorized is False
    assert manifest.merge_authorized is False


def test_phase21_freeze_rejects_missing_empirical_validation_kind() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="requires MC, provider stress and interaction ablation",
    ):
        build_phase21_policy_freeze(
            qualification=_qualification(),
            empirical_validations=_validations()[:-1],
            policy_surface=_surface(),
            frozen_at=QUALIFIED_AT + timedelta(hours=4),
        )


def test_phase21_freeze_rejects_synthetic_empirical_receipt() -> None:
    receipt = _validation(
        Phase21EmpiricalValidationKind.PROVIDER_STRESS,
        offset_hours=2,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="must be FORWARD_EMPIRICAL",
    ):
        replace(receipt, evidence_class="SYNTHETIC_CONTRACT")


def test_phase21_freeze_rejects_qualification_lineage_mismatch() -> None:
    validations = list(_validations())
    validations[0] = replace(
        validations[0],
        qualification_artifact_sha256=_sha(999),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="qualification lineage mismatch",
    ):
        build_phase21_policy_freeze(
            qualification=_qualification(),
            empirical_validations=tuple(validations),
            policy_surface=_surface(),
            frozen_at=QUALIFIED_AT + timedelta(hours=4),
        )


def test_phase21_freeze_must_follow_all_empirical_validation() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="freeze must follow empirical validation",
    ):
        build_phase21_policy_freeze(
            qualification=_qualification(),
            empirical_validations=_validations(),
            policy_surface=_surface(),
            frozen_at=QUALIFIED_AT + timedelta(hours=3),
        )


def test_phase21_manifest_digest_is_order_invariant_for_receipts() -> None:
    forward = build_phase21_policy_freeze(
        qualification=_qualification(),
        empirical_validations=_validations(),
        policy_surface=_surface(),
        frozen_at=QUALIFIED_AT + timedelta(hours=4),
    )
    reverse = build_phase21_policy_freeze(
        qualification=_qualification(),
        empirical_validations=tuple(reversed(_validations())),
        policy_surface=_surface(),
        frozen_at=QUALIFIED_AT + timedelta(hours=4),
    )

    assert forward.manifest_sha256() == reverse.manifest_sha256()
