import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from qore.infrastructure.cibo_ce2i_final_certification import (
    CiboEconomicCertificationStatus,
    Phase22QualificationReceipt,
    assess_cibo_final_economic_certification,
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
    Phase21PolicySurfaceDigests,
    build_phase21_empirical_validation_receipt,
    build_phase21_qualification_receipt,
    build_phase21_policy_freeze,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification_plan import (
    FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN,
    phase22_holdout_qualification_plan_sha256,
)

QUALIFIED_AT = datetime(2026, 10, 26, 20, 0, tzinfo=UTC)
PHASE21_FROZEN_AT = QUALIFIED_AT + timedelta(hours=4)


def _sha(index: int) -> str:
    return f"sha256:{index:064x}"


def _qualification_artifact_json() -> str:
    candidate = FROZEN_PHASE20_POLICY_CANDIDATE
    report = {
        "schema": "qore.cibo.phase20d.v2-qualification.v5",
        "status": "PASS",
        "plan_id": FROZEN_PHASE20D_QUALIFICATION_PLAN.plan_id,
        "plan_sha256": phase20d_qualification_plan_sha256(),
        "candidate_id": candidate.candidate_id,
        "failures_or_pending_reasons": [],
        "readiness": {
            "ready": True,
            "reasons": [],
            "decision_epochs": 80,
            "candidate_instances": 240,
            "candidate_outcomes": 240,
            "selected_instances": 80,
            "selected_outcomes": 80,
            "candidate_outcome_coverage": "1",
            "selected_outcome_coverage": "1",
            "calendar_span_days": 28,
            "distinct_trading_days": 20,
            "represented_lineages": 7,
            "minimum_outcomes_any_lineage": 8,
            "minimum_fold_candidate_outcomes": 60,
            "minimum_fold_lineages": 4,
            "missing_policy_decisions": 0,
            "pre_freeze_decisions": 0,
        },
        "economics": {
            "policy_net_delta_usd": "120",
            "baseline_net_delta_usd": "80",
            "policy_settlement_cash_drawdown_usd": "10",
            "baseline_settlement_cash_drawdown_usd": "12",
            "policy_capital_productivity": "0.10",
            "baseline_capital_productivity": "0.08",
            "policy_selected_outcome_coverage": "1",
            "baseline_selected_outcome_coverage": "1",
            "candidate_outcome_coverage": "1",
        },
        "folds": [
            {
                "fold_id": f"fold-{index + 1}",
                "policy_net_delta_usd": "30",
            }
            for index in range(4)
        ],
        "dataset": [{"decision_epoch_id": "epoch-test"}],
        "provenance": {
            "git_sha": "b" * 40,
            "evidence_store_sha256": _sha(1),
            "policy_store_sha256": _sha(2),
            "evidence_generation": 1,
            "policy_generation": 1,
            "decision_count": 80,
            "outcome_count": 240,
            "policy_decision_count": 80,
            "collector_git_shas": ["a" * 40],
            "missing_collector_git_sha_decisions": 0,
        },
        "phase20d_gate": {
            "status": "PASS",
            "eligible_for_phase21": True,
            "blockers": [],
            "requires_exact_evidence_and_policy_digests": True,
            "requires_single_collector_git_sha": True,
        },
        "final_certification": {
            "status": "PENDING_PHASE21_PHASE22",
            "eligible": False,
            "phase20d_eligible_for_phase21": True,
        },
    }
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


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


def _phase21_manifest():
    candidate = FROZEN_PHASE20_POLICY_CANDIDATE
    qualification = build_phase21_qualification_receipt(
        qualification_artifact_json=_qualification_artifact_json(),
        qualified_at=QUALIFIED_AT,
    )
    validations = tuple(
        build_phase21_empirical_validation_receipt(
            kind=kind,
            qualification=qualification,
            validator_git_sha=f"{index + 1:040x}",
            observed_at=QUALIFIED_AT + timedelta(hours=index + 1),
            validation_payload=_validation_payload(kind),
        )
        for index, kind in enumerate(Phase21EmpiricalValidationKind)
    )
    surface = Phase21PolicySurfaceDigests(
        state_machine_sha256=_sha(101),
        tool_registry_sha256=_sha(102),
        eligibility_sha256=_sha(103),
        source_ledger_sha256=_sha(104),
        trader_adapters_sha256=_sha(105),
        provider_profiles_sha256=_sha(106),
    )
    return build_phase21_policy_freeze(
        qualification=qualification,
        empirical_validations=validations,
        policy_surface=surface,
        frozen_at=PHASE21_FROZEN_AT,
    )


def _receipt(*, phase21_sha: str) -> Phase22QualificationReceipt:
    candidate = FROZEN_PHASE20_POLICY_CANDIDATE
    plan = FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN
    qualified_at = PHASE21_FROZEN_AT + timedelta(days=29)
    validator_git_sha = "c" * 40
    artifact = {
        "schema": "qore.cibo.phase22.holdout-qualification.v1",
        "status": "PASS",
        "candidate_id": candidate.candidate_id,
        "candidate_parameter_sha256": candidate.parameter_sha256(),
        "phase21_manifest_sha256": phase21_sha,
        "phase22_plan_id": plan.plan_id,
        "phase22_plan_sha256": phase22_holdout_qualification_plan_sha256(),
        "holdout_evidence_store_sha256": _sha(201),
        "holdout_policy_store_sha256": _sha(202),
        "validator_git_sha": validator_git_sha,
        "qualified_at": qualified_at.isoformat(),
        "evidence_class": "FORWARD_EMPIRICAL_HOLDOUT",
        "lineage_valid": True,
        "economic_holdout_passed": True,
        "lineage": {
            "decision_epochs": 80,
            "policy_decisions": 80,
            "outcomes": 240,
            "collector_git_shas": ["d" * 40],
        },
        "economic": {
            "status": "PASS",
            "failures": [],
            "policy_net_delta_usd": "120",
            "baseline_net_delta_usd": "80",
            "policy_settlement_cash_drawdown_usd": "10",
            "baseline_settlement_cash_drawdown_usd": "12",
            "policy_capital_productivity": "0.10",
            "baseline_capital_productivity": "0.08",
            "policy_selected_outcome_coverage": "1",
            "baseline_selected_outcome_coverage": "1",
            "candidate_outcome_coverage": "1",
        },
        "failures": [],
        "governance": {
            "synthetic_evidence_used": False,
            "holdout_mining_used": False,
            "outcome_aware_refit": False,
            "qualification_population_reused": False,
        },
    }
    artifact_json = json.dumps(artifact, indent=2, sort_keys=True) + "\n"
    artifact_sha256 = (
        "sha256:" + sha256(artifact_json.encode("utf-8")).hexdigest()
    )
    return Phase22QualificationReceipt(
        candidate_id=candidate.candidate_id,
        candidate_parameter_sha256=candidate.parameter_sha256(),
        phase21_manifest_sha256=phase21_sha,
        phase22_plan_id=plan.plan_id,
        phase22_plan_sha256=phase22_holdout_qualification_plan_sha256(),
        holdout_evidence_store_sha256=_sha(201),
        holdout_policy_store_sha256=_sha(202),
        qualification_artifact_sha256=artifact_sha256,
        qualification_artifact_json=artifact_json,
        validator_git_sha=validator_git_sha,
        qualified_at=qualified_at,
        evidence_class="FORWARD_EMPIRICAL_HOLDOUT",
        passed=True,
        lineage_valid=True,
        economic_holdout_passed=True,
    )


def test_phase22_receipt_rejects_detached_artifact_digest() -> None:
    receipt = _receipt(phase21_sha=_sha(301))

    try:
        replace(receipt, qualification_artifact_sha256=_sha(999))
    except Exception as error:
        assert "artifact digest mismatch" in str(error)
    else:
        raise AssertionError("detached Phase22 artifact digest was accepted")


def test_final_certification_remains_pending_without_phase22_receipt() -> None:
    manifest = _phase21_manifest()

    decision = assess_cibo_final_economic_certification(
        phase21_manifest=manifest,
        phase22_receipt=None,
    )

    assert decision.status is CiboEconomicCertificationStatus.PENDING
    assert decision.blockers == ("PHASE22_QUALIFICATION_RECEIPT_REQUIRED",)
    assert decision.live_authorized is False
    assert decision.real_capital_authorized is False


def test_final_certification_requires_exact_phase21_lineage() -> None:
    manifest = _phase21_manifest()

    decision = assess_cibo_final_economic_certification(
        phase21_manifest=manifest,
        phase22_receipt=_receipt(phase21_sha=_sha(999)),
    )

    assert decision.status is CiboEconomicCertificationStatus.INVALID
    assert decision.blockers == ("PHASE21_MANIFEST_LINEAGE_MISMATCH",)


def test_final_certification_accepts_exact_sealed_economic_chain_only() -> None:
    manifest = _phase21_manifest()

    decision = assess_cibo_final_economic_certification(
        phase21_manifest=manifest,
        phase22_receipt=_receipt(
            phase21_sha=manifest.manifest_sha256(),
        ),
    )

    assert decision.status is CiboEconomicCertificationStatus.CERTIFIED
    assert decision.blockers == ()
    assert decision.demo_execution_authorized is False
    assert decision.live_authorized is False
    assert decision.real_capital_authorized is False
    assert decision.merge_authorized is False
