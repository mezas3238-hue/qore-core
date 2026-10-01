from __future__ import annotations

import importlib.util
import json
from dataclasses import fields, replace
from datetime import timedelta
from hashlib import sha256
from pathlib import Path

import pytest

from qore.infrastructure.cibo_arch_a_final_exam_system_controls import (
    authority_boundary_contract_sha256,
    build_architect_a_final_exam_system_controls,
)
from qore.infrastructure.cibo_arch_a_internal_readiness import (
    _COMPOUND_P8_REQUIRED_PROVEN_IDS,
    _REQUIRED_MECHANISM_EVIDENCE_KINDS,
    PHASE22_V2_INTAKE_SCHEMA,
    PHASE22_V2_MECHANISM_EVIDENCE_SCHEMA,
    PHASE22_V2_REQUIRED_FOLDS,
    PHASE22_V2_REQUIRED_RECEIPTS,
    PHASE22_V2_REQUIRED_TRADERS,
    ArchitectAPhase22V2CompoundClosureReceipt,
    ArchitectAPhase22V2MechanismEvidenceReceipt,
    ArchitectAPhase22V2ScientificIntakeReport,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)

_FIXTURE_PATH = Path(__file__).with_name("test_cibo_ce2i_final_certification.py")
_SPEC = importlib.util.spec_from_file_location("_final_system_fixture", _FIXTURE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_FIXTURE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_FIXTURE)


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode("utf-8")).hexdigest()


def _capital_truth_artifact() -> str:
    payload = {
        "binding_id": "CIBO_INTEGRATED_CAPITAL_FORWARD_POPULATION_BINDING_V1",
        "manifest_sha256": _sha("forward-manifest"),
        "manifest_rows": 100,
        "compound_settlements": 100,
        "manifest_positive_profit_usd": "12.00",
        "compound_positive_profit_usd": "12.00",
        "manifest_scientifically_ready": True,
        "account_scope_match": True,
        "settlement_population_exact": True,
        "positive_profit_reconciliation_match": True,
        "integrated_capital_truth_pass": True,
        "ready_for_scientific_consumption": True,
        "blockers": [],
        "source_ledger_sha256": _sha("source-ledger"),
        "compound_cycle_state_sha256": _sha("compound-cycle"),
        "runtime_authority": False,
        "sizing_authority": False,
        "risk_authority": False,
        "execution_authority": False,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _chain():
    phase21 = _FIXTURE._phase21_manifest()
    phase22 = _FIXTURE._receipt(phase21_sha=phase21.manifest_sha256())
    capital_truth_artifact = _capital_truth_artifact()
    capital_truth_sha256 = "sha256:" + sha256(
        capital_truth_artifact.encode("utf-8")
    ).hexdigest()
    refs = []
    for name in PHASE22_V2_REQUIRED_RECEIPTS:
        if name == "qualification_report_sha256":
            value = phase22.qualification_artifact_sha256
        elif name == "holdout_evidence_store_sha256":
            value = phase22.holdout_evidence_store_sha256
        elif name == "holdout_policy_store_sha256":
            value = phase22.holdout_policy_store_sha256
        elif name == "integrated_capital_truth_sha256":
            value = capital_truth_sha256
        else:
            value = _sha(name)
        refs.append((name, value))
    intake = ArchitectAPhase22V2ScientificIntakeReport(
        schema=PHASE22_V2_INTAKE_SCHEMA,
        manifest_sha256=_sha("phase22-handoff"),
        candidate_id="CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2",
        qualification_status="PASS",
        trader_ids=PHASE22_V2_REQUIRED_TRADERS,
        fold_ids=PHASE22_V2_REQUIRED_FOLDS,
        decision_epochs=80,
        candidate_outcomes=200,
        selected_outcomes=60,
        calendar_span_days=28,
        distinct_trading_days=20,
        minimum_fold_candidate_outcomes=40,
        minimum_fold_lineages=4,
        minimum_outcomes_any_lineage=8,
        candidate_outcome_coverage="0.95",
        selected_outcome_coverage="1.00",
        baseline_selected_outcome_coverage="1.00",
        receipt_refs=tuple(refs),
        ready_for_scientific_reentry=True,
        blockers=(),
    )
    evidence_refs = tuple(
        (kind, _sha(kind)) for kind in _REQUIRED_MECHANISM_EVIDENCE_KINDS
    )
    mechanism = ArchitectAPhase22V2MechanismEvidenceReceipt(
        schema=PHASE22_V2_MECHANISM_EVIDENCE_SCHEMA,
        phase22_manifest_sha256=intake.manifest_sha256,
        evidence_refs=evidence_refs,
        present_kinds=_REQUIRED_MECHANISM_EVIDENCE_KINDS,
        missing_kinds=(),
        ready_for_full_mechanism_science=True,
        blockers=(),
    )
    compound = ArchitectAPhase22V2CompoundClosureReceipt(
        phase22_manifest_sha256=intake.manifest_sha256,
        closure_batch_sha256=_sha("closure-batch"),
        genc1_evidence_sha256=_sha("genc1"),
        required_proven_ids=_COMPOUND_P8_REQUIRED_PROVEN_IDS,
        missing_or_nonproven_ids=(),
        compound_closure_terminal=True,
        blockers=(),
    )
    return phase22, intake, mechanism, compound, capital_truth_artifact


def test_authority_contract_is_code_derived_and_trader_volume_free() -> None:
    trader_fields = {item.name for item in fields(TraderOpportunityEnvelope)}
    assert not {
        "volume",
        "lots",
        "risk_usd",
        "requested_risk_usd",
        "capital_allocation_usd",
    } & trader_fields
    assert authority_boundary_contract_sha256().startswith("sha256:")


def test_arch_a_derives_e1_e6_e10_from_exact_phase22_chain() -> None:
    phase22, intake, mechanism, compound, capital_truth_artifact = _chain()
    receipts = build_architect_a_final_exam_system_controls(
        integrated_git_sha="a" * 40,
        phase22_receipt=phase22,
        intake=intake,
        mechanism=mechanism,
        compound_closure=compound,
        integrated_capital_truth_artifact_json=capital_truth_artifact,
        observed_at=phase22.qualified_at + timedelta(minutes=1),
    )
    assert tuple(item.receipt_id for item in receipts) == (
        "E1_AUTHORITY",
        "E2_CAPITAL_CONSERVATION",
        "E3_REALIZED_CAPITAL_LAW",
        "E4_PROVIDER_TRUTH",
        "E5_RISK_PRECEDENCE",
        "E6_CHRONOLOGY_NO_LEAKAGE",
        "E10_DETERMINISTIC_REPLAY",
    )


def test_arch_a_system_controls_reject_phase22_store_drift() -> None:
    phase22, intake, mechanism, compound, capital_truth_artifact = _chain()
    intake = replace(
        intake,
        receipt_refs=tuple(
            (
                name,
                _sha("wrong-evidence")
                if name == "holdout_evidence_store_sha256"
                else digest,
            )
            for name, digest in intake.receipt_refs
        ),
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="Phase22 store lineage drift",
    ):
        build_architect_a_final_exam_system_controls(
            integrated_git_sha="a" * 40,
            phase22_receipt=phase22,
            intake=intake,
            mechanism=mechanism,
            compound_closure=compound,
            integrated_capital_truth_artifact_json=capital_truth_artifact,
            observed_at=phase22.qualified_at + timedelta(minutes=1),
        )


def test_arch_a_system_controls_require_strict_temporal_evidence() -> None:
    phase22, intake, mechanism, compound, capital_truth_artifact = _chain()
    evidence_refs = tuple(
        item
        for item in mechanism.evidence_refs
        if item[0] != "STRICT_TEMPORAL_POPULATION_LINEAGE"
    )
    present = tuple(kind for kind, _digest in evidence_refs)
    missing = tuple(
        kind
        for kind in _REQUIRED_MECHANISM_EVIDENCE_KINDS
        if kind not in set(present)
    )
    mechanism = replace(
        mechanism,
        evidence_refs=evidence_refs,
        present_kinds=present,
        missing_kinds=missing,
        ready_for_full_mechanism_science=False,
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="STRICT_TEMPORAL_POPULATION_LINEAGE",
    ):
        build_architect_a_final_exam_system_controls(
            integrated_git_sha="a" * 40,
            phase22_receipt=phase22,
            intake=intake,
            mechanism=mechanism,
            compound_closure=compound,
            integrated_capital_truth_artifact_json=capital_truth_artifact,
            observed_at=phase22.qualified_at + timedelta(minutes=1),
        )


def test_arch_a_system_controls_require_proven_compound() -> None:
    phase22, intake, mechanism, compound, capital_truth_artifact = _chain()
    compound = replace(
        compound,
        missing_or_nonproven_ids=("GEN-C9",),
        compound_closure_terminal=False,
        blockers=("GEN-C9_NOT_PROVEN",),
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="require proven Compound closure",
    ):
        build_architect_a_final_exam_system_controls(
            integrated_git_sha="a" * 40,
            phase22_receipt=phase22,
            intake=intake,
            mechanism=mechanism,
            compound_closure=compound,
            integrated_capital_truth_artifact_json=capital_truth_artifact,
            observed_at=phase22.qualified_at + timedelta(minutes=1),
        )


def test_arch_a_system_controls_reject_capital_truth_artifact_drift() -> None:
    phase22, intake, mechanism, compound, capital_truth_artifact = _chain()
    with pytest.raises(
        CiboCapitalManagementError,
        match="Integrated Capital Truth digest drift",
    ):
        build_architect_a_final_exam_system_controls(
            integrated_git_sha="a" * 40,
            phase22_receipt=phase22,
            intake=intake,
            mechanism=mechanism,
            compound_closure=compound,
            integrated_capital_truth_artifact_json=(
                capital_truth_artifact + " "
            ),
            observed_at=phase22.qualified_at + timedelta(minutes=1),
        )


def test_arch_a_system_controls_reject_failed_capital_truth_gate() -> None:
    phase22, intake, mechanism, compound, capital_truth_artifact = _chain()
    payload = json.loads(capital_truth_artifact)
    payload["settlement_population_exact"] = False
    payload["ready_for_scientific_consumption"] = False
    payload["blockers"] = ["POPULATION_MISMATCH"]
    bad_artifact = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    bad_sha = "sha256:" + sha256(bad_artifact.encode("utf-8")).hexdigest()
    intake = replace(
        intake,
        receipt_refs=tuple(
            (
                name,
                bad_sha
                if name == "integrated_capital_truth_sha256"
                else digest,
            )
            for name, digest in intake.receipt_refs
        ),
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="gate failed: settlement_population_exact",
    ):
        build_architect_a_final_exam_system_controls(
            integrated_git_sha="a" * 40,
            phase22_receipt=phase22,
            intake=intake,
            mechanism=mechanism,
            compound_closure=compound,
            integrated_capital_truth_artifact_json=bad_artifact,
            observed_at=phase22.qualified_at + timedelta(minutes=1),
        )
