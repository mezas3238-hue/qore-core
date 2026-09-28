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
    build_phase21_empirical_validation_receipt,
    build_phase21_policy_freeze,
)

QUALIFIED_AT = datetime(2026, 10, 26, 20, 0, tzinfo=UTC)


def _sha(index: int) -> str:
    return f"sha256:{index:064x}"


def _validation_payload(
    kind: Phase21EmpiricalValidationKind,
) -> dict[str, object]:
    if kind is Phase21EmpiricalValidationKind.CAPITAL_STATE_MONTE_CARLO:
        return {
            "simulation_count": 1000,
            "policy_capacity_breach_paths": 0,
            "baseline_capacity_breach_paths": 0,
            "policy_p95_drawdown_usd": "8",
            "baseline_p95_drawdown_usd": "10",
            "policy_median_ending_delta_usd": "12",
            "baseline_median_ending_delta_usd": "10",
        }
    if kind is Phase21EmpiricalValidationKind.PROVIDER_STRESS:
        return {
            "scenario_count": 9,
            "policy_constraint_bypasses": 0,
            "baseline_constraint_bypasses": 0,
            "policy_worst_case_net_delta_usd": "8",
            "baseline_worst_case_net_delta_usd": "7",
            "policy_provider_failure_incidence": "0.10",
            "baseline_provider_failure_incidence": "0.15",
        }
    return {
        "ablation_case_count": 3,
        "unsafe_interaction_count": 0,
        "population_mismatch_count": 0,
        "full_policy_pareto_dominated_by_ablation": False,
    }


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
    return build_phase21_empirical_validation_receipt(
        kind=kind,
        qualification=_qualification(),
        validator_git_sha=f"{offset_hours:040x}",
        observed_at=QUALIFIED_AT + timedelta(hours=offset_hours),
        validation_payload=_validation_payload(kind),
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


def test_phase21_empirical_monte_carlo_cannot_self_declare_pass() -> None:
    payload = _validation_payload(
        Phase21EmpiricalValidationKind.CAPITAL_STATE_MONTE_CARLO
    )
    payload["policy_p95_drawdown_usd"] = "11"

    with pytest.raises(
        CiboCapitalManagementError,
        match="capital-state Monte Carlo did not PASS",
    ):
        build_phase21_empirical_validation_receipt(
            kind=Phase21EmpiricalValidationKind.CAPITAL_STATE_MONTE_CARLO,
            qualification=_qualification(),
            validator_git_sha="1" * 40,
            observed_at=QUALIFIED_AT + timedelta(hours=1),
            validation_payload=payload,
        )


def test_phase21_empirical_provider_stress_cannot_self_declare_pass() -> None:
    payload = _validation_payload(
        Phase21EmpiricalValidationKind.PROVIDER_STRESS
    )
    payload["policy_constraint_bypasses"] = 1

    with pytest.raises(
        CiboCapitalManagementError,
        match="provider stress did not PASS",
    ):
        build_phase21_empirical_validation_receipt(
            kind=Phase21EmpiricalValidationKind.PROVIDER_STRESS,
            qualification=_qualification(),
            validator_git_sha="2" * 40,
            observed_at=QUALIFIED_AT + timedelta(hours=2),
            validation_payload=payload,
        )


def test_phase21_empirical_ablation_cannot_self_declare_pass() -> None:
    payload = _validation_payload(
        Phase21EmpiricalValidationKind.INTERACTION_ABLATION
    )
    payload["full_policy_pareto_dominated_by_ablation"] = True

    with pytest.raises(
        CiboCapitalManagementError,
        match="interaction ablation did not PASS",
    ):
        build_phase21_empirical_validation_receipt(
            kind=Phase21EmpiricalValidationKind.INTERACTION_ABLATION,
            qualification=_qualification(),
            validator_git_sha="3" * 40,
            observed_at=QUALIFIED_AT + timedelta(hours=3),
            validation_payload=payload,
        )


def test_phase21_empirical_receipt_rejects_detached_report_digest() -> None:
    receipt = _validation(
        Phase21EmpiricalValidationKind.PROVIDER_STRESS,
        offset_hours=2,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="artifact digest/report mismatch",
    ):
        replace(receipt, artifact_sha256=_sha(999))


def test_phase21_empirical_receipt_rejects_detached_population() -> None:
    receipt = _validation(
        Phase21EmpiricalValidationKind.INTERACTION_ABLATION,
        offset_hours=3,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="source population digest mismatch",
    ):
        replace(receipt, source_population_sha256=_sha(999))


def test_phase21_freeze_rejects_qualification_lineage_mismatch() -> None:
    validations = list(_validations())
    detached_qualification = replace(
        _qualification(),
        qualification_artifact_sha256=_sha(999),
    )
    validations[0] = build_phase21_empirical_validation_receipt(
        kind=Phase21EmpiricalValidationKind.CAPITAL_STATE_MONTE_CARLO,
        qualification=detached_qualification,
        validator_git_sha=f"{1:040x}",
        observed_at=QUALIFIED_AT + timedelta(hours=1),
        validation_payload=_validation_payload(
            Phase21EmpiricalValidationKind.CAPITAL_STATE_MONTE_CARLO
        ),
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
