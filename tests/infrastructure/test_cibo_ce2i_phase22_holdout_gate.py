import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
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
    build_phase21_policy_freeze,
    build_phase21_qualification_receipt,
)
from qore.infrastructure.cibo_ce2i_phase22_holdout_gate import (
    assess_phase22_holdout_lineage,
)

QUALIFIED_AT = datetime(2026, 10, 26, 20, 0, tzinfo=UTC)
PHASE21_FROZEN_AT = QUALIFIED_AT + timedelta(hours=4)
COLLECTOR_SHA = "a" * 40


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
        "causal_tool_readiness": {
            "tools": [
                {
                    "tool_code": code,
                    "state": "FORWARD_POPULATION_READY",
                    "stream_bound": True,
                    "forward_population_ready": True,
                    "observed_epochs": 80,
                    "qualifying_epochs": 80,
                    "blockers": [],
                }
                for code in (
                    "T08",
                    "T09",
                    "T12",
                    "T13",
                    "T14",
                    "T15",
                    "T18",
                )
            ],
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
            "requires_all_causal_tool_gates_ready": True,
            "causal_tool_gate_codes": [
                "T08",
                "T09",
                "T12",
                "T13",
                "T14",
                "T15",
                "T18",
            ],
        },
        "final_certification": {
            "status": "PENDING_PHASE21_PHASE22",
            "eligible": False,
            "phase20d_eligible_for_phase21": True,
            "requires_all_causal_tool_gates_ready": True,
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


def _decision(
    *,
    evidence_sha: str,
    decision_at: datetime,
    collector_git_sha: str | None = COLLECTOR_SHA,
    sealed_at: datetime | None = None,
    seal_deadline_at: datetime | None = None,
) -> Phase20ForwardDecisionSeal:
    candidate = FROZEN_PHASE20_POLICY_CANDIDATE
    effective_sealed_at = (
        decision_at + timedelta(milliseconds=100)
        if sealed_at is None
        else sealed_at
    )
    effective_deadline = (
        decision_at + timedelta(seconds=2)
        if seal_deadline_at is None
        else seal_deadline_at
    )
    return Phase20ForwardDecisionSeal(
        evidence_id=f"evidence-{evidence_sha[-4:]}",
        decision_epoch_id=f"epoch-{evidence_sha[-4:]}",
        evidence_sha256=evidence_sha,
        decision_at=decision_at,
        sealed_at=effective_sealed_at,
        seal_deadline_at=effective_deadline,
        candidate_id=candidate.candidate_id,
        code_sha=candidate.code_sha,
        parameter_sha256=candidate.parameter_sha256(),
        signal_fingerprints=("signal-one",),
        canonical_payload_json='{"candidates":[]}',
        collector_git_sha=collector_git_sha,
    )


def _policy(evidence_sha: str) -> Phase20ForwardPolicyDecisionSeal:
    return Phase20ForwardPolicyDecisionSeal(
        evidence_sha256=evidence_sha,
        policy_record_sha256=_sha(500),
        allocator_disposition="ABSTAIN",
        selected_signal_fingerprints=(),
        canonical_record_json="{}",
    )


def _assess(
    *,
    qualification_decision: Phase20ForwardDecisionSeal,
    holdout_decision: Phase20ForwardDecisionSeal,
    policies: tuple[Phase20ForwardPolicyDecisionSeal, ...] | None = None,
):
    return assess_phase22_holdout_lineage(
        phase21_manifest=_phase21_manifest(),
        qualification_evidence_book=VersionedPhase20ForwardEvidenceBook(
            generation=1,
            decisions=(qualification_decision,),
        ),
        holdout_evidence_book=VersionedPhase20ForwardEvidenceBook(
            generation=1,
            decisions=(holdout_decision,),
        ),
        holdout_policy_book=VersionedPhase20ForwardPolicyBook(
            generation=1,
            decisions=(
                (_policy(holdout_decision.evidence_sha256),)
                if policies is None
                else policies
            ),
        ),
        qualification_evidence_store_sha256=_sha(1),
        qualification_policy_store_sha256=_sha(2),
        holdout_evidence_store_sha256=_sha(11),
        holdout_policy_store_sha256=_sha(12),
    )


def test_phase22_lineage_accepts_only_fresh_disjoint_frozen_policy() -> None:
    qualification_decision = _decision(
        evidence_sha=_sha(201),
        decision_at=QUALIFIED_AT - timedelta(days=1),
    )
    holdout_decision = _decision(
        evidence_sha=_sha(202),
        decision_at=datetime(2016, 2, 15, 14, 0, tzinfo=UTC),
        sealed_at=PHASE21_FROZEN_AT + timedelta(seconds=1),
        seal_deadline_at=PHASE21_FROZEN_AT + timedelta(seconds=3),
    )

    assessment = _assess(
        qualification_decision=qualification_decision,
        holdout_decision=holdout_decision,
    )

    assert assessment.lineage_valid is True
    assert assessment.reasons == ()
    assert assessment.decision_epochs == 1
    assert assessment.policy_decisions == 1
    assert assessment.collector_git_shas == (COLLECTOR_SHA,)
    assert assessment.economic_holdout_passed is False


def test_phase22_lineage_rejects_pre_freeze_seal() -> None:
    qualification_decision = _decision(
        evidence_sha=_sha(201),
        decision_at=QUALIFIED_AT - timedelta(days=1),
    )
    holdout_decision = _decision(
        evidence_sha=_sha(202),
        decision_at=datetime(2016, 2, 15, 14, 0, tzinfo=UTC),
        sealed_at=PHASE21_FROZEN_AT,
        seal_deadline_at=PHASE21_FROZEN_AT + timedelta(seconds=2),
    )

    assessment = _assess(
        qualification_decision=qualification_decision,
        holdout_decision=holdout_decision,
    )

    assert assessment.lineage_valid is False
    assert (
        "HOLDOUT_DECISION_SEAL_NOT_POST_PHASE21_FREEZE"
        in assessment.reasons
    )


def test_phase22_lineage_rejects_market_time_outside_preregistered_holdout() -> None:
    qualification_decision = _decision(
        evidence_sha=_sha(201),
        decision_at=QUALIFIED_AT - timedelta(days=1),
    )
    holdout_decision = _decision(
        evidence_sha=_sha(202),
        decision_at=datetime(2016, 4, 19, tzinfo=UTC),
        sealed_at=PHASE21_FROZEN_AT + timedelta(seconds=1),
        seal_deadline_at=PHASE21_FROZEN_AT + timedelta(seconds=3),
    )

    assessment = _assess(
        qualification_decision=qualification_decision,
        holdout_decision=holdout_decision,
    )

    assert assessment.lineage_valid is False
    assert "HOLDOUT_DECISION_OUTSIDE_PREREGISTERED_WINDOW" in assessment.reasons


def test_phase22_lineage_rejects_qualification_decision_reuse() -> None:
    reused_sha = _sha(201)
    qualification_decision = _decision(
        evidence_sha=reused_sha,
        decision_at=QUALIFIED_AT - timedelta(days=1),
    )
    holdout_decision = replace(
        qualification_decision,
        evidence_id="holdout-evidence",
        decision_epoch_id="holdout-epoch",
        decision_at=datetime(2016, 2, 15, 14, 0, tzinfo=UTC),
        sealed_at=PHASE21_FROZEN_AT + timedelta(milliseconds=1100),
        seal_deadline_at=PHASE21_FROZEN_AT + timedelta(seconds=3),
    )

    assessment = _assess(
        qualification_decision=qualification_decision,
        holdout_decision=holdout_decision,
    )

    assert assessment.lineage_valid is False
    assert "QUALIFICATION_DECISION_REUSED_IN_HOLDOUT" in assessment.reasons


def test_phase22_lineage_requires_complete_collector_git_sha() -> None:
    qualification_decision = _decision(
        evidence_sha=_sha(201),
        decision_at=QUALIFIED_AT - timedelta(days=1),
    )
    holdout_decision = _decision(
        evidence_sha=_sha(202),
        decision_at=datetime(2016, 2, 15, 14, 0, tzinfo=UTC),
        sealed_at=PHASE21_FROZEN_AT + timedelta(seconds=1),
        seal_deadline_at=PHASE21_FROZEN_AT + timedelta(seconds=3),
        collector_git_sha=None,
    )

    assessment = _assess(
        qualification_decision=qualification_decision,
        holdout_decision=holdout_decision,
    )

    assert assessment.lineage_valid is False
    assert "HOLDOUT_COLLECTOR_GIT_LINEAGE_INCOMPLETE" in assessment.reasons


def test_phase22_lineage_requires_one_policy_record_per_decision() -> None:
    qualification_decision = _decision(
        evidence_sha=_sha(201),
        decision_at=QUALIFIED_AT - timedelta(days=1),
    )
    holdout_decision = _decision(
        evidence_sha=_sha(202),
        decision_at=datetime(2016, 2, 15, 14, 0, tzinfo=UTC),
        sealed_at=PHASE21_FROZEN_AT + timedelta(seconds=1),
        seal_deadline_at=PHASE21_FROZEN_AT + timedelta(seconds=3),
    )

    assessment = _assess(
        qualification_decision=qualification_decision,
        holdout_decision=holdout_decision,
        policies=(),
    )

    assert assessment.lineage_valid is False
    assert "HOLDOUT_POLICY_DECISION_SET_MISMATCH" in assessment.reasons
