from __future__ import annotations

from dataclasses import replace
import json
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

