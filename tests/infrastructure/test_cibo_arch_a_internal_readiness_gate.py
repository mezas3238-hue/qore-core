from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from qore.infrastructure import cibo_arch_a_internal_readiness as gate


def _row(
    row_id: str,
    *,
    terminal: bool,
    maturity: str = "ENGINE_CI_GREEN_REAL_EVIDENCE_OPEN",
) -> dict:
    return {
        "id": row_id,
        "kind": "RESEARCH",
        "mandatory": True,
        "certification_blocking": True,
        "current_maturity": maturity,
        "terminal_disposition": (
            "COMPLETED_AND_PROVEN" if terminal else None
        ),
        "evidence_refs": [f"evidence://{row_id}"],
        "blockers": [] if terminal else ["FRESH_OOS_EVIDENCE_REQUIRED"],
        "next_gate": (
            "Terminal."
            if terminal
            else "Bind real population and run frozen scientific gates."
        ),
    }


def _ledger() -> dict:
    rows = [
        _row(row_id, terminal=(row_id in {"T05", "T19", "GEN-C1"}))
        for row_id in gate.A_WORKSTREAM_IDS
    ]
    return {"workstreams": rows}


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_architect_a_readiness_allows_empirical_open_work(tmp_path: Path) -> None:
    path = tmp_path / "ledger.json"
    _write(path, _ledger())

    report = gate.evaluate_architect_a_internal_readiness(path)

    assert report.passed is True
    assert report.workstream_count == 38
    assert report.terminal_count == 3
    assert report.empirical_open_count == 35
    assert report.internal_debt_ids == ()
    assert report.scientific_closure_claimed is False
    assert report.integration_authority is False
    assert report.production_authority is False


@pytest.mark.parametrize(
    "marker",
    (
        "REGISTRY_RECONCILIATION_REQUIRED",
        "CI_PENDING",
        "NOT_IMPLEMENTED",
        "PREREGISTRATION_REQUIRED",
        "TEST_REQUIRED",
    ),
)
def test_architect_a_readiness_rejects_internal_debt_marker(
    tmp_path: Path,
    marker: str,
) -> None:
    payload = _ledger()
    payload["workstreams"][0]["current_maturity"] = marker
    path = tmp_path / "ledger.json"
    _write(path, payload)

    report = gate.evaluate_architect_a_internal_readiness(path)

    assert report.passed is False
    assert report.internal_debt_ids == ("T04",)


def test_architect_a_readiness_rejects_missing_workstream(
    tmp_path: Path,
) -> None:
    payload = _ledger()
    payload["workstreams"] = payload["workstreams"][1:]
    path = tmp_path / "ledger.json"
    _write(path, payload)

    report = gate.evaluate_architect_a_internal_readiness(path)

    assert report.passed is False
    assert report.missing_workstream_ids == ("T04",)


def test_architect_a_readiness_rejects_open_row_without_blocker(
    tmp_path: Path,
) -> None:
    payload = _ledger()
    payload["workstreams"][0]["blockers"] = []
    path = tmp_path / "ledger.json"
    _write(path, payload)

    report = gate.evaluate_architect_a_internal_readiness(path)

    assert report.passed is False
    assert report.internal_debt_ids == ("T04",)


def test_architect_a_readiness_rejects_missing_evidence(
    tmp_path: Path,
) -> None:
    payload = _ledger()
    payload["workstreams"][0]["evidence_refs"] = []
    path = tmp_path / "ledger.json"
    _write(path, payload)

    report = gate.evaluate_architect_a_internal_readiness(path)

    assert report.passed is False
    assert report.evidence_missing_ids == ("T04",)

def _manifest_row(index: int) -> dict:
    plan = gate.FROZEN_PHASE20D_QUALIFICATION_PLAN
    frozen = gate.FROZEN_PHASE20_POLICY_CANDIDATE
    digest = "sha256:" + sha256(str(index).encode("utf-8")).hexdigest()
    return {
        "decision_evidence_sha256": digest,
        "signal_fingerprint": f"signal-{index}",
        "fold_id": ("WF1", "WF2", "WF3", "WF4")[index % 4],
        "trader_id": f"trader-{index % plan.minimum_global_lineages}",
        "candidate_id": frozen.candidate_id,
        "code_sha": frozen.code_sha,
        "parameter_sha256": frozen.parameter_sha256(),
        "baseline_policy_id": plan.baseline_policy_id,
        "provider_economics_sha256": digest,
        "executed_risk_sha256": digest,
        "settlement_sha256": digest,
        "release_evidence_sha256": digest,
        "policy_selected": index < plan.minimum_selected_outcomes,
    }


def _forward_manifest_payload(*, ready: bool) -> dict:
    plan = gate.FROZEN_PHASE20D_QUALIFICATION_PLAN
    frozen = gate.FROZEN_PHASE20_POLICY_CANDIDATE
    row_count = plan.minimum_candidate_outcomes
    rows = [_manifest_row(index) for index in range(row_count)]
    payload = {
        "manifest_id": gate.ARCH_B_FORWARD_MANIFEST_ID,
        "frozen_candidate_id": frozen.candidate_id,
        "frozen_code_sha": frozen.code_sha,
        "frozen_parameter_sha256": frozen.parameter_sha256(),
        "qualification_plan_id": plan.plan_id,
        "qualification_plan_sha256": gate.phase20d_qualification_plan_sha256(),
        "baseline_policy_id": plan.baseline_policy_id,
        "qualification_status": "PASS",
        "decision_epochs": plan.minimum_decision_epochs,
        "candidate_rows": row_count,
        "complete_lineage_rows": row_count,
        "rows": rows,
        "gaps": [],
        "ready_for_scientific_consumption": ready,
        "certification_ready": False,
        "productive_authority": False,
    }
    payload["manifest_sha256"] = gate.forward_manifest_payload_sha256(payload)
    return payload


def test_scientific_intake_accepts_ready_arch_b_manifest() -> None:
    report = gate.evaluate_architect_a_scientific_intake(
        _forward_manifest_payload(ready=True)
    )

    assert report.ready_for_batch_science is True
    assert report.blockers == ()
    assert report.fold_ids == ("WF1", "WF2", "WF3", "WF4")
    assert report.trader_lineage_count >= (
        gate.FROZEN_PHASE20D_QUALIFICATION_PLAN.minimum_global_lineages
    )
    assert report.scientific_closure_claimed is False
    assert report.integration_authority is False
    assert report.production_authority is False


def test_scientific_intake_stays_blocked_when_b_is_not_ready() -> None:
    report = gate.evaluate_architect_a_scientific_intake(
        _forward_manifest_payload(ready=False)
    )

    assert report.ready_for_batch_science is False
    assert report.blockers == (
        "ARCH_B_NOT_READY_FOR_SCIENTIFIC_CONSUMPTION",
    )


def test_scientific_intake_rejects_manifest_digest_drift() -> None:
    payload = _forward_manifest_payload(ready=True)
    payload["decision_epochs"] += 1

    with pytest.raises(
        gate.ArchitectAReadinessError,
        match="manifest digest drift",
    ):
        gate.evaluate_architect_a_scientific_intake(payload)


def test_scientific_intake_rejects_frozen_lineage_drift() -> None:
    payload = _forward_manifest_payload(ready=True)
    payload["frozen_code_sha"] = "0" * 40
    unsigned = dict(payload)
    unsigned.pop("manifest_sha256")
    payload["manifest_sha256"] = gate.forward_manifest_payload_sha256(unsigned)

    with pytest.raises(
        gate.ArchitectAReadinessError,
        match="frozen Phase20 lineage drift",
    ):
        gate.evaluate_architect_a_scientific_intake(payload)

def test_scientific_batch_plan_covers_all_35_open_workstreams(
    tmp_path: Path,
) -> None:
    ledger_path = tmp_path / "ledger.json"
    _write(ledger_path, _ledger())
    readiness = gate.evaluate_architect_a_internal_readiness(ledger_path)
    intake = gate.evaluate_architect_a_scientific_intake(
        _forward_manifest_payload(ready=True)
    )

    plan = gate.build_architect_a_scientific_batch_plan(
        readiness,
        intake,
    )

    assert plan.population_batch_ready is True
    assert plan.remaining_workstream_count == 35
    assert len(plan.remaining_workstream_ids) == 35
    assert len(set(plan.remaining_workstream_ids)) == 35
    assert plan.wave_1_ids
    assert plan.wave_2_ids
    assert plan.wave_3_ids
    assert plan.wave_4_ids == ("CAPITAL_AMPLIFICATION",)
    assert plan.scientific_closure_claimed is False
    assert plan.production_authority is False


def test_scientific_batch_plan_blocks_until_b_intake_is_ready(
    tmp_path: Path,
) -> None:
    ledger_path = tmp_path / "ledger.json"
    _write(ledger_path, _ledger())
    readiness = gate.evaluate_architect_a_internal_readiness(ledger_path)
    intake = gate.evaluate_architect_a_scientific_intake(
        _forward_manifest_payload(ready=False)
    )

    plan = gate.build_architect_a_scientific_batch_plan(
        readiness,
        intake,
    )

    assert plan.population_batch_ready is False
    assert plan.blockers == ("ARCH_B_SCIENTIFIC_INTAKE_REQUIRED",)

def test_architect_a_readiness_rejects_manual_pass_evidence_drift(
    tmp_path: Path,
) -> None:
    payload = _ledger()
    payload["workstreams"][0]["evidence_refs"] = []
    path = tmp_path / "ledger.json"
    _write(path, payload)
    report = gate.evaluate_architect_a_internal_readiness(path)

    with pytest.raises(
        gate.ArchitectAReadinessError,
        match="pass/evidence drift",
    ):
        replace(report, passed=True)

def test_scientific_batch_plan_exposes_mechanism_evidence_contract(
    tmp_path: Path,
) -> None:
    ledger_path = tmp_path / "ledger.json"
    _write(ledger_path, _ledger())
    readiness = gate.evaluate_architect_a_internal_readiness(ledger_path)
    intake = gate.evaluate_architect_a_scientific_intake(
        _forward_manifest_payload(ready=True)
    )
    plan = gate.build_architect_a_scientific_batch_plan(readiness, intake)

    assert plan.required_mechanism_evidence_kinds == (
        "FORWARD_CAPITAL_TRUTH_CHRONOLOGY",
        "T08_FACTOR_CORRELATION_LINEAGE",
        "T09_T18_TRUE_SCARCITY_LINEAGE",
        "T15_RESERVATION_COUNTERFACTUAL_LINEAGE",
        "GENC10_TWIN_TRANSITION_LINEAGE",
        "GENC11_TRANSITION_CALIBRATION",
        "GENC12_CRISIS_FACTOR_SET",
        "GENC13_MEMORY_HYPOTHESIS",
        "PROTECTED_BASE_POLICY_IDENTITY",
        "COMPOUND_STRESS_LINEAGE",
        "STRICT_TEMPORAL_POPULATION_LINEAGE",
    )

def _mechanism_evidence_payload(
    intake: gate.ArchitectAScientificIntakeReport,
    *,
    complete: bool,
) -> dict:
    kinds = gate._REQUIRED_MECHANISM_EVIDENCE_KINDS
    selected = kinds if complete else kinds[:3]
    return {
        "schema": gate.MECHANISM_EVIDENCE_SCHEMA,
        "forward_manifest_sha256": intake.manifest_sha256,
        "evidence_refs": [
            {
                "kind": kind,
                "sha256": "sha256:"
                + sha256(kind.encode("utf-8")).hexdigest(),
            }
            for kind in selected
        ],
        "scientific_closure_claimed": False,
        "integration_authority": False,
        "production_authority": False,
    }


def test_mechanism_evidence_receipt_reports_missing_kinds() -> None:
    intake = gate.evaluate_architect_a_scientific_intake(
        _forward_manifest_payload(ready=True)
    )
    receipt = gate.evaluate_architect_a_mechanism_evidence(
        _mechanism_evidence_payload(intake, complete=False),
        intake,
    )

    assert receipt.ready_for_full_mechanism_science is False
    assert receipt.present_kinds == gate._REQUIRED_MECHANISM_EVIDENCE_KINDS[:3]
    assert receipt.missing_kinds == gate._REQUIRED_MECHANISM_EVIDENCE_KINDS[3:]


def test_mechanism_evidence_receipt_can_be_complete() -> None:
    intake = gate.evaluate_architect_a_scientific_intake(
        _forward_manifest_payload(ready=True)
    )
    receipt = gate.evaluate_architect_a_mechanism_evidence(
        _mechanism_evidence_payload(intake, complete=True),
        intake,
    )

    assert receipt.ready_for_full_mechanism_science is True
    assert receipt.missing_kinds == ()
    assert receipt.blockers == ()


def test_mechanism_evidence_receipt_rejects_manifest_lineage_drift() -> None:
    intake = gate.evaluate_architect_a_scientific_intake(
        _forward_manifest_payload(ready=True)
    )
    payload = _mechanism_evidence_payload(intake, complete=True)
    payload["forward_manifest_sha256"] = "sha256:" + "0" * 64

    with pytest.raises(
        gate.ArchitectAReadinessError,
        match="forward-manifest lineage drift",
    ):
        gate.evaluate_architect_a_mechanism_evidence(payload, intake)

def test_architect_a_readiness_accepts_terminal_external_dependency(
    tmp_path: Path,
) -> None:
    payload = _ledger()
    row = payload["workstreams"][0]
    row["terminal_disposition"] = "EXTERNAL_DEPENDENCY_BLOCKED"
    row["current_maturity"] = (
        "TERMINAL_EXTERNAL_DEPENDENCY_BLOCKED_REAL_PHASE20D_REQUIRED"
    )
    row["blockers"] = ["ARCH_B_REAL_PHASE20D_FORWARD_POPULATION_NOT_AVAILABLE"]
    path = tmp_path / "ledger.json"
    _write(path, payload)

    report = gate.evaluate_architect_a_internal_readiness(path)

    assert report.passed is True
    assert "T04" in report.terminal_ids
    assert "T04" not in report.empirical_open_ids
    assert report.external_dependency_count == 1
    assert report.external_dependency_ids == ("T04",)
    assert report.internal_debt_ids == ()


def test_scientific_batch_plan_reenters_terminal_external_dependencies(
    tmp_path: Path,
) -> None:
    payload = _ledger()
    internally_complete = {"T05", "T19", "GEN-C1"}
    for row in payload["workstreams"]:
        if row["id"] in internally_complete:
            continue
        row["terminal_disposition"] = "EXTERNAL_DEPENDENCY_BLOCKED"
        row["current_maturity"] = (
            "TERMINAL_EXTERNAL_DEPENDENCY_BLOCKED_REAL_PHASE22_REQUIRED"
        )
        row["blockers"] = ["PHASE22_V2_EMPIRICAL_EVIDENCE_REQUIRED"]

    ledger_path = tmp_path / "ledger.json"
    _write(ledger_path, payload)
    readiness = gate.evaluate_architect_a_internal_readiness(ledger_path)
    intake = gate.evaluate_architect_a_scientific_intake(
        _forward_manifest_payload(ready=True)
    )

    assert readiness.passed is True
    assert readiness.terminal_count == 38
    assert readiness.empirical_open_count == 0
    assert readiness.external_dependency_count == 35

    plan = gate.build_architect_a_scientific_batch_plan(readiness, intake)

    assert plan.population_batch_ready is True
    assert plan.complete_without_execution is False
    assert plan.remaining_workstream_count == 35
    assert set(plan.remaining_workstream_ids) == set(
        readiness.external_dependency_ids
    )



def _phase22_v2_manifest_payload(
    *,
    qualification_status: str = "PASS",
    future_leakage: bool = False,
) -> dict:
    plan = gate.FROZEN_PHASE20D_QUALIFICATION_PLAN
    receipts = {
        name: "sha256:" + sha256(name.encode("utf-8")).hexdigest()
        for name in gate.PHASE22_V2_REQUIRED_RECEIPTS
    }
    payload = {
        "schema": gate.PHASE22_V2_INTAKE_SCHEMA,
        "candidate_id": gate.PHASE22_V2_CANDIDATE_ID,
        "window_start": gate.PHASE22_V2_WINDOW_START,
        "window_end_exclusive": gate.PHASE22_V2_WINDOW_END_EXCLUSIVE,
        "qualification_plan_sha256": gate.phase20d_qualification_plan_sha256(),
        "qualification_status": qualification_status,
        "trader_ids": list(gate.PHASE22_V2_REQUIRED_TRADERS),
        "fold_ids": list(gate.PHASE22_V2_REQUIRED_FOLDS),
        "decision_epochs": plan.minimum_decision_epochs,
        "candidate_outcomes": plan.minimum_candidate_outcomes,
        "selected_outcomes": plan.minimum_selected_outcomes,
        "calendar_span_days": plan.minimum_calendar_span_days,
        "distinct_trading_days": plan.minimum_distinct_trading_days,
        "minimum_fold_candidate_outcomes": (
            plan.minimum_fold_candidate_outcomes
        ),
        "minimum_fold_lineages": plan.minimum_fold_lineages,
        "minimum_outcomes_any_lineage": plan.minimum_outcomes_per_lineage,
        "candidate_outcome_coverage": format(
            plan.minimum_candidate_outcome_coverage, "f"
        ),
        "selected_outcome_coverage": format(
            plan.required_selected_outcome_coverage, "f"
        ),
        "baseline_selected_outcome_coverage": format(
            plan.required_baseline_selected_outcome_coverage, "f"
        ),
        "receipts": receipts,
        "source_receipt_sealed": True,
        "pre_holdout_freeze_sealed": True,
        "parity_7_of_7": True,
        "fresh_execution_complete": True,
        "lineage_gate_passed": True,
        "economic_qualification_executed": True,
        "future_leakage": future_leakage,
        "synthetic_evidence_used": False,
        "retuning_after_fresh": False,
        "outcome_selected_configuration": False,
        "productive_authority": False,
        "certification_ready": False,
    }
    payload["manifest_sha256"] = gate.forward_manifest_payload_sha256(payload)
    return payload


@pytest.mark.parametrize("status", ("PASS", "FAIL"))
def test_phase22_v2_intake_accepts_terminal_scientific_outcome(
    status: str,
) -> None:
    report = gate.evaluate_architect_a_phase22_v2_scientific_intake(
        _phase22_v2_manifest_payload(qualification_status=status)
    )

    assert report.qualification_status == status
    assert report.ready_for_scientific_reentry is True
    assert report.blockers == ()
    assert report.trader_ids == gate.PHASE22_V2_REQUIRED_TRADERS
    assert report.fold_ids == gate.PHASE22_V2_REQUIRED_FOLDS
    assert report.scientific_closure_claimed is False
    assert report.production_authority is False


def test_phase22_v2_intake_rejects_burned_v1_candidate() -> None:
    payload = _phase22_v2_manifest_payload()
    payload["candidate_id"] = "CIBO_USD60_6M_HOLDOUT_2017H1_V1"
    unsigned = dict(payload)
    unsigned.pop("manifest_sha256")
    payload["manifest_sha256"] = gate.forward_manifest_payload_sha256(unsigned)

    with pytest.raises(
        gate.ArchitectAReadinessError,
        match="candidate identity drift",
    ):
        gate.evaluate_architect_a_phase22_v2_scientific_intake(payload)


def test_phase22_v2_intake_blocks_future_leakage() -> None:
    report = gate.evaluate_architect_a_phase22_v2_scientific_intake(
        _phase22_v2_manifest_payload(future_leakage=True)
    )

    assert report.ready_for_scientific_reentry is False
    assert "FUTURE_LEAKAGE_PROHIBITED" in report.blockers


def test_phase22_v2_batch_reenters_all_external_a_workstreams(
    tmp_path: Path,
) -> None:
    payload = _ledger()
    internally_complete = {"T05", "T19", "GEN-C1"}
    for row in payload["workstreams"]:
        if row["id"] in internally_complete:
            continue
        row["terminal_disposition"] = "EXTERNAL_DEPENDENCY_BLOCKED"
        row["current_maturity"] = (
            "TERMINAL_EXTERNAL_DEPENDENCY_BLOCKED_REAL_PHASE22_REQUIRED"
        )
        row["blockers"] = ["PHASE22_V2_EMPIRICAL_EVIDENCE_REQUIRED"]

    ledger_path = tmp_path / "ledger.json"
    _write(ledger_path, payload)
    readiness = gate.evaluate_architect_a_internal_readiness(ledger_path)
    intake = gate.evaluate_architect_a_phase22_v2_scientific_intake(
        _phase22_v2_manifest_payload(qualification_status="FAIL")
    )

    plan = gate.build_architect_a_phase22_v2_scientific_batch_plan(
        readiness,
        intake,
    )

    assert plan.population_batch_ready is True
    assert plan.complete_without_execution is False
    assert plan.remaining_workstream_count == 35
    assert set(plan.remaining_workstream_ids) == set(
        readiness.external_dependency_ids
    )


def _phase22_v2_mechanism_payload(
    intake: gate.ArchitectAPhase22V2ScientificIntakeReport,
    *,
    complete: bool,
) -> dict:
    kinds = gate._REQUIRED_MECHANISM_EVIDENCE_KINDS
    selected = kinds if complete else kinds[:4]
    return {
        "schema": gate.PHASE22_V2_MECHANISM_EVIDENCE_SCHEMA,
        "phase22_manifest_sha256": intake.manifest_sha256,
        "evidence_refs": [
            {
                "kind": kind,
                "sha256": "sha256:"
                + sha256(("phase22-" + kind).encode("utf-8")).hexdigest(),
            }
            for kind in selected
        ],
        "scientific_closure_claimed": False,
        "integration_authority": False,
        "production_authority": False,
    }


def test_phase22_v2_mechanism_receipt_reports_partial_delivery() -> None:
    intake = gate.evaluate_architect_a_phase22_v2_scientific_intake(
        _phase22_v2_manifest_payload()
    )
    receipt = gate.evaluate_architect_a_phase22_v2_mechanism_evidence(
        _phase22_v2_mechanism_payload(intake, complete=False),
        intake,
    )

    assert receipt.ready_for_full_mechanism_science is False
    assert receipt.present_kinds == gate._REQUIRED_MECHANISM_EVIDENCE_KINDS[:4]
    assert receipt.missing_kinds == gate._REQUIRED_MECHANISM_EVIDENCE_KINDS[4:]


def test_phase22_v2_mechanism_receipt_accepts_complete_delivery() -> None:
    intake = gate.evaluate_architect_a_phase22_v2_scientific_intake(
        _phase22_v2_manifest_payload(qualification_status="FAIL")
    )
    receipt = gate.evaluate_architect_a_phase22_v2_mechanism_evidence(
        _phase22_v2_mechanism_payload(intake, complete=True),
        intake,
    )

    assert receipt.ready_for_full_mechanism_science is True
    assert receipt.missing_kinds == ()
    assert receipt.blockers == ()


def test_phase22_v2_mechanism_receipt_rejects_manifest_drift() -> None:
    intake = gate.evaluate_architect_a_phase22_v2_scientific_intake(
        _phase22_v2_manifest_payload()
    )
    payload = _phase22_v2_mechanism_payload(intake, complete=True)
    payload["phase22_manifest_sha256"] = "sha256:" + "0" * 64

    with pytest.raises(
        gate.ArchitectAReadinessError,
        match="mechanism manifest lineage drift",
    ):
        gate.evaluate_architect_a_phase22_v2_mechanism_evidence(
            payload,
            intake,
        )


def test_phase22_v2_workstream_matrix_unlocks_only_satisfied_evidence() -> None:
    intake = gate.evaluate_architect_a_phase22_v2_scientific_intake(
        _phase22_v2_manifest_payload()
    )
    payload = {
        "schema": gate.PHASE22_V2_MECHANISM_EVIDENCE_SCHEMA,
        "phase22_manifest_sha256": intake.manifest_sha256,
        "evidence_refs": [
            {
                "kind": kind,
                "sha256": "sha256:"
                + sha256(("partial-" + kind).encode("utf-8")).hexdigest(),
            }
            for kind in (
                "FORWARD_CAPITAL_TRUTH_CHRONOLOGY",
                "T09_T18_TRUE_SCARCITY_LINEAGE",
            )
        ],
        "scientific_closure_claimed": False,
        "integration_authority": False,
        "production_authority": False,
    }
    mechanism = gate.evaluate_architect_a_phase22_v2_mechanism_evidence(
        payload,
        intake,
    )
    matrix = gate.evaluate_architect_a_phase22_v2_workstream_evidence(
        intake,
        mechanism,
    )

    assert "T09" in matrix.ready_ids
    assert "T18" in matrix.ready_ids
    assert "AS_IS_ECONOMIC_BASELINE" in matrix.ready_ids
    assert "GEN-C6" in matrix.blocked_ids
    assert "INTERNAL_CAPITAL_MARKET" in matrix.blocked_ids
    assert "GEN-C10" in matrix.blocked_ids
    assert matrix.all_external_workstreams_ready is False


def test_phase22_v2_workstream_matrix_full_evidence_unlocks_all() -> None:
    intake = gate.evaluate_architect_a_phase22_v2_scientific_intake(
        _phase22_v2_manifest_payload(qualification_status="FAIL")
    )
    mechanism = gate.evaluate_architect_a_phase22_v2_mechanism_evidence(
        _phase22_v2_mechanism_payload(intake, complete=True),
        intake,
    )
    matrix = gate.evaluate_architect_a_phase22_v2_workstream_evidence(
        intake,
        mechanism,
    )

    assert matrix.all_external_workstreams_ready is True
    assert matrix.blocked_ids == ()
    assert len(matrix.ready_ids) == 35
    assert set(matrix.ready_ids) == set(
        gate._PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM
    )


def test_phase22_v2_workstream_matrix_requires_admissible_intake() -> None:
    payload = _phase22_v2_manifest_payload(future_leakage=True)
    intake = gate.evaluate_architect_a_phase22_v2_scientific_intake(payload)
    mechanism_payload = {
        "schema": gate.PHASE22_V2_MECHANISM_EVIDENCE_SCHEMA,
        "phase22_manifest_sha256": intake.manifest_sha256,
        "evidence_refs": [],
        "scientific_closure_claimed": False,
        "integration_authority": False,
        "production_authority": False,
    }
    mechanism = gate.evaluate_architect_a_phase22_v2_mechanism_evidence(
        mechanism_payload,
        intake,
    )

    with pytest.raises(
        gate.ArchitectAReadinessError,
        match="requires admissible scientific intake",
    ):
        gate.evaluate_architect_a_phase22_v2_workstream_evidence(
            intake,
            mechanism,
        )
