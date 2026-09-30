from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest


def _load_gate_module() -> ModuleType:
    path = Path("scripts/cibo_zero_open_work_gate.py")
    spec = importlib.util.spec_from_file_location(
        "cibo_zero_open_work_gate",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load CIBO zero-open-work gate")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load_gate_module()


def _ledger(*, disposition: str | None, blocking: bool = True) -> dict:
    terminal_count = 1 if disposition is not None else 0
    open_count = 1 - terminal_count
    return {
        "schema": "QORE_CIBO_MASTER_OPEN_WORK_LEDGER_V1",
        "terminal_dispositions": [
            "COMPLETED_AND_PROVEN",
            "FALSIFIED_AND_CLOSED",
            "SUPERSEDED_WITH_PROVEN_LINEAGE",
            "EXTERNAL_DEPENDENCY_BLOCKED",
        ],
        "current_summary": {
            "mandatory_count": 1,
            "terminal_count": terminal_count,
            "open_count": open_count,
            "zero_open_work_pass": open_count == 0,
            "final_certification_candidate": False,
        },
        "workstreams": [
            {
                "id": "TEST",
                "kind": "SYSTEM",
                "mandatory": True,
                "certification_blocking": blocking,
                "current_maturity": (
                    "COMPLETED_AND_PROVEN"
                    if disposition == "COMPLETED_AND_PROVEN"
                    else "OPEN_REQUIRED"
                ),
                "terminal_disposition": disposition,
                "evidence_refs": (
                    ["test://terminal-evidence"]
                    if disposition is not None
                    else []
                ),
                "blockers": (
                    ["REAL_EXTERNAL_BLOCKER"]
                    if disposition == "EXTERNAL_DEPENDENCY_BLOCKED"
                    else []
                ),
                "next_gate": "Close the test workstream.",
            }
        ],
    }


def _write(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_zero_open_work_gate_blocks_open_required_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = tmp_path / "ledger.json"
    _write(ledger, _ledger(disposition=None))
    monkeypatch.setattr(gate, "_REQUIRED_CANONICAL_ARTIFACTS", ())
    monkeypatch.setattr(gate, "_INVENTORY_GLOBS", ())
    monkeypatch.setattr(gate, "_MARKER_SCAN_GLOBS", ())

    verdict = gate.evaluate_gate(
        repo_root=tmp_path,
        ledger_path=ledger,
    )

    assert verdict.passed is False
    assert verdict.open_workstream_ids == ("TEST",)
    assert verdict.reasons == ("UNCLOSED_REQUIRED_WORKSTREAM",)


def test_zero_open_work_gate_passes_only_terminal_proven_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = tmp_path / "ledger.json"
    _write(ledger, _ledger(disposition="COMPLETED_AND_PROVEN"))
    monkeypatch.setattr(gate, "_REQUIRED_CANONICAL_ARTIFACTS", ())
    monkeypatch.setattr(gate, "_INVENTORY_GLOBS", ())
    monkeypatch.setattr(gate, "_MARKER_SCAN_GLOBS", ())

    verdict = gate.evaluate_gate(
        repo_root=tmp_path,
        ledger_path=ledger,
    )

    assert verdict.passed is True
    assert verdict.terminal_workstream_count == 1
    assert verdict.open_workstream_ids == ()
    assert verdict.reasons == ()


def test_external_dependency_blocks_when_certification_critical(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = tmp_path / "ledger.json"
    _write(
        ledger,
        _ledger(
            disposition="EXTERNAL_DEPENDENCY_BLOCKED",
            blocking=True,
        ),
    )
    monkeypatch.setattr(gate, "_REQUIRED_CANONICAL_ARTIFACTS", ())
    monkeypatch.setattr(gate, "_INVENTORY_GLOBS", ())
    monkeypatch.setattr(gate, "_MARKER_SCAN_GLOBS", ())

    verdict = gate.evaluate_gate(
        repo_root=tmp_path,
        ledger_path=ledger,
    )

    assert verdict.passed is False
    assert verdict.certification_blocking_external_dependency_ids == (
        "TEST",
    )


def test_gate_detects_missing_required_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = tmp_path / "ledger.json"
    _write(ledger, _ledger(disposition="COMPLETED_AND_PROVEN"))
    monkeypatch.setattr(
        gate,
        "_REQUIRED_CANONICAL_ARTIFACTS",
        ("required/missing.json",),
    )
    monkeypatch.setattr(gate, "_INVENTORY_GLOBS", ())
    monkeypatch.setattr(gate, "_MARKER_SCAN_GLOBS", ())

    verdict = gate.evaluate_gate(
        repo_root=tmp_path,
        ledger_path=ledger,
    )

    assert verdict.passed is False
    assert verdict.missing_required_artifacts == (
        "required/missing.json",
    )
    assert "MISSING_REQUIRED_ARTIFACT" in verdict.reasons


def test_gate_detects_high_signal_orphan_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = tmp_path / "ledger.json"
    _write(ledger, _ledger(disposition="COMPLETED_AND_PROVEN"))
    source = tmp_path / "src"
    source.mkdir()
    (source / "cibo_test.py").write_text(
        "# TODO unresolved certification work\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(gate, "_REQUIRED_CANONICAL_ARTIFACTS", ())
    monkeypatch.setattr(gate, "_INVENTORY_GLOBS", ("src/cibo_*.py",))
    monkeypatch.setattr(gate, "_MARKER_SCAN_GLOBS", ("src/cibo_*.py",))
    monkeypatch.setattr(
        gate,
        "_WORKSTREAM_CLASSIFIERS",
        (("src/cibo_*.py", "TEST"),),
    )

    verdict = gate.evaluate_gate(
        repo_root=tmp_path,
        ledger_path=ledger,
    )

    assert verdict.passed is False
    assert verdict.high_signal_marker_hits == (
        "src/cibo_test.py:1:TODO",
    )
    assert "HIGH_SIGNAL_UNRESOLVED_CODE_MARKER" in verdict.reasons


def test_gate_marks_unclassified_inventory_as_orphan_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = tmp_path / "ledger.json"
    payload = _ledger(disposition="COMPLETED_AND_PROVEN")
    payload["workstreams"].append(
        {
            "id": "ORPHAN_INVENTORY",
            "kind": "GOVERNANCE",
            "mandatory": True,
            "certification_blocking": True,
            "current_maturity": "OPEN_REQUIRED",
            "terminal_disposition": None,
            "evidence_refs": [],
            "blockers": ["MANUAL_CLASSIFICATION_REQUIRED"],
            "next_gate": "Classify every CIBO inventory path.",
        }
    )
    payload["current_summary"] = {
        "mandatory_count": 2,
        "terminal_count": 1,
        "open_count": 1,
        "zero_open_work_pass": False,
        "final_certification_candidate": False,
    }
    _write(ledger, payload)
    source = tmp_path / "src"
    source.mkdir()
    (source / "cibo_unknown.py").write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(gate, "_REQUIRED_CANONICAL_ARTIFACTS", ())
    monkeypatch.setattr(gate, "_INVENTORY_GLOBS", ("src/cibo_*.py",))
    monkeypatch.setattr(gate, "_MARKER_SCAN_GLOBS", ())
    monkeypatch.setattr(gate, "_WORKSTREAM_CLASSIFIERS", ())

    verdict = gate.evaluate_gate(
        repo_root=tmp_path,
        ledger_path=ledger,
    )

    assert verdict.passed is False
    assert verdict.orphan_candidate_paths == ("src/cibo_unknown.py",)
    assert "UNCLASSIFIED_ORPHAN_CANDIDATE" in verdict.reasons


def test_gate_rejects_current_summary_count_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = tmp_path / "ledger.json"
    payload = _ledger(disposition=None)
    payload["current_summary"]["open_count"] = 0
    _write(ledger, payload)
    monkeypatch.setattr(gate, "_REQUIRED_CANONICAL_ARTIFACTS", ())
    monkeypatch.setattr(gate, "_INVENTORY_GLOBS", ())
    monkeypatch.setattr(gate, "_MARKER_SCAN_GLOBS", ())

    with pytest.raises(
        gate.CiboZeroOpenWorkGateError,
        match="current_summary open_count drift",
    ):
        gate.evaluate_gate(repo_root=tmp_path, ledger_path=ledger)


def test_gate_rejects_closed_terminal_with_blockers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = tmp_path / "ledger.json"
    payload = _ledger(disposition="COMPLETED_AND_PROVEN")
    payload["workstreams"][0]["blockers"] = ["STALE_BLOCKER"]
    _write(ledger, payload)
    monkeypatch.setattr(gate, "_REQUIRED_CANONICAL_ARTIFACTS", ())
    monkeypatch.setattr(gate, "_INVENTORY_GLOBS", ())
    monkeypatch.setattr(gate, "_MARKER_SCAN_GLOBS", ())

    with pytest.raises(
        gate.CiboZeroOpenWorkGateError,
        match="closed terminal workstream cannot retain blockers",
    ):
        gate.evaluate_gate(repo_root=tmp_path, ledger_path=ledger)


def test_gate_rejects_terminal_without_evidence_refs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = tmp_path / "ledger.json"
    payload = _ledger(disposition="FALSIFIED_AND_CLOSED")
    payload["workstreams"][0]["current_maturity"] = "FALSIFIED_AND_CLOSED"
    payload["workstreams"][0]["evidence_refs"] = []
    _write(ledger, payload)
    monkeypatch.setattr(gate, "_REQUIRED_CANONICAL_ARTIFACTS", ())
    monkeypatch.setattr(gate, "_INVENTORY_GLOBS", ())
    monkeypatch.setattr(gate, "_MARKER_SCAN_GLOBS", ())

    with pytest.raises(
        gate.CiboZeroOpenWorkGateError,
        match="terminal workstream requires evidence references",
    ):
        gate.evaluate_gate(repo_root=tmp_path, ledger_path=ledger)


def test_gate_rejects_unsafe_final_candidate_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = tmp_path / "ledger.json"
    payload = _ledger(disposition="COMPLETED_AND_PROVEN")
    payload["current_summary"]["final_certification_candidate"] = True
    _write(ledger, payload)
    monkeypatch.setattr(
        gate,
        "_REQUIRED_CANONICAL_ARTIFACTS",
        ("required/missing.json",),
    )
    monkeypatch.setattr(gate, "_INVENTORY_GLOBS", ())
    monkeypatch.setattr(gate, "_MARKER_SCAN_GLOBS", ())

    with pytest.raises(
        gate.CiboZeroOpenWorkGateError,
        match="final-certification candidate contradicts gate evidence",
    ):
        gate.evaluate_gate(repo_root=tmp_path, ledger_path=ledger)


def _pre_exam_ledger() -> dict:
    payload = _ledger(disposition="COMPLETED_AND_PROVEN")
    payload["workstreams"][0]["id"] = "SCIENTIFIC_WORK"
    payload["workstreams"].extend(
        (
            {
                "id": "FINAL_INTEGRATED_CIBO_EXAM",
                "kind": "CERTIFICATION",
                "mandatory": True,
                "certification_blocking": True,
                "current_maturity": "FINAL_EXAM_EXECUTION_BLOCKED",
                "terminal_disposition": None,
                "evidence_refs": ["docs/research/final-exam.md"],
                "blockers": ["PRE_EXAM_ZERO_OPEN_PASS_REQUIRED"],
                "next_gate": "Run the final integrated exam.",
            },
            {
                "id": "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
                "kind": "CERTIFICATION",
                "mandatory": True,
                "certification_blocking": True,
                "current_maturity": "WAITING_FOR_FINAL_INTEGRATED_EXAM",
                "terminal_disposition": None,
                "evidence_refs": ["docs/research/world-cup-exam.md"],
                "blockers": ["FINAL_INTEGRATED_CIBO_EXAM_REQUIRED"],
                "next_gate": (
                    "Run after the final integrated exam and before strict closure."
                ),
            },
        )
    )
    payload["current_summary"] = {
        "mandatory_count": 3,
        "terminal_count": 1,
        "open_count": 2,
        "zero_open_work_pass": False,
        "final_certification_candidate": False,
    }
    return payload


def test_pre_exam_gate_excludes_both_mandatory_certification_exams(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = tmp_path / "ledger.json"
    _write(ledger, _pre_exam_ledger())
    monkeypatch.setattr(gate, "_REQUIRED_CANONICAL_ARTIFACTS", ())
    monkeypatch.setattr(gate, "_INVENTORY_GLOBS", ())
    monkeypatch.setattr(gate, "_MARKER_SCAN_GLOBS", ())

    pre_exam = gate.evaluate_pre_exam_gate(
        repo_root=tmp_path,
        ledger_path=ledger,
    )
    strict = gate.evaluate_gate(
        repo_root=tmp_path,
        ledger_path=ledger,
    )

    assert pre_exam.scope == "PRE_EXAM"
    assert pre_exam.passed is True
    assert pre_exam.open_workstream_ids == ()
    assert pre_exam.mandatory_workstream_count == 1
    assert strict.scope == "STRICT"
    assert strict.passed is False
    assert strict.open_workstream_ids == (
        "FINAL_INTEGRATED_CIBO_EXAM",
        "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
    )


def test_pre_exam_gate_still_blocks_other_open_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = tmp_path / "ledger.json"
    payload = _pre_exam_ledger()
    payload["workstreams"][0]["current_maturity"] = "OPEN_REQUIRED"
    payload["workstreams"][0]["terminal_disposition"] = None
    payload["workstreams"][0]["evidence_refs"] = []
    payload["current_summary"] = {
        "mandatory_count": 3,
        "terminal_count": 0,
        "open_count": 3,
        "zero_open_work_pass": False,
        "final_certification_candidate": False,
    }
    _write(ledger, payload)
    monkeypatch.setattr(gate, "_REQUIRED_CANONICAL_ARTIFACTS", ())
    monkeypatch.setattr(gate, "_INVENTORY_GLOBS", ())
    monkeypatch.setattr(gate, "_MARKER_SCAN_GLOBS", ())

    verdict = gate.evaluate_pre_exam_gate(
        repo_root=tmp_path,
        ledger_path=ledger,
    )

    assert verdict.passed is False
    assert verdict.open_workstream_ids == ("SCIENTIFIC_WORK",)


def test_integrator_preserves_architect_b_inventory_classifiers() -> None:
    inventory = (
        "src/qore/infrastructure/cibo_arch_b_forward_economic_manifest.py",
        "src/qore/infrastructure/cibo_ctrader_demo_account_capability.py",
        "src/qore/infrastructure/cibo_research_memory.py",
    )
    ledger_ids = frozenset(
        {
            "FORWARD_QUALIFICATION",
            "PROVIDER_ECONOMICS",
            "LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK",
        }
    )

    assignments, orphans = gate._classify_inventory(
        inventory,
        ledger_ids=ledger_ids,
    )

    assert dict(assignments) == {
        (
            "src/qore/infrastructure/"
            "cibo_arch_b_forward_economic_manifest.py"
        ): "FORWARD_QUALIFICATION",
        (
            "src/qore/infrastructure/"
            "cibo_ctrader_demo_account_capability.py"
        ): "PROVIDER_ECONOMICS",
        "src/qore/infrastructure/cibo_research_memory.py": (
            "LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK"
        ),
    }
    assert orphans == ()


def test_integrator_classifies_new_crossboundary_and_forward_inventory() -> None:
    inventory = (
        "src/qore/infrastructure/cibo_crossboundary_evidence_receipt.py",
        "src/qore/infrastructure/cibo_receipt_bound_final_integrated_exam.py",
        "src/qore/infrastructure/cibo_usd60_prerequisite_receipts.py",
        "src/qore/infrastructure/cibo_ce2i_provider_execution_calibration.py",
        "scripts/cibo_phase20_provider_execution_calibration.py",
        "src/qore/infrastructure/cibo_ce2i_provider_economics_component_freeze.py",
        "src/qore/infrastructure/cibo_integrated_capital_forward_binding.py",
        ".github/workflows/cibo-integrated-capital-forward-binding.yml",
        ".github/workflows/cibo-architect-a-internal-readiness.yml",
        ".github/workflows/cibo-ctrader-demo-provider-economics.yml",
        ".github/workflows/cibo-crossboundary-evidence-receipt.yml",
    )
    ledger_ids = frozenset(
        {
            "CE2I_CROSS_TOOL_INFRASTRUCTURE",
            "FINAL_INTEGRATED_CIBO_EXAM",
            "USD60_CAPABILITY_PROGRAM",
            "PROVIDER_ECONOMICS",
            "INTEGRATED_CAPITAL_TRUTH",
            "ZERO_OPEN_WORK_GATE",
        }
    )

    assignments, orphans = gate._classify_inventory(
        inventory,
        ledger_ids=ledger_ids,
    )

    assert dict(assignments) == {
        "src/qore/infrastructure/cibo_crossboundary_evidence_receipt.py": (
            "CE2I_CROSS_TOOL_INFRASTRUCTURE"
        ),
        "src/qore/infrastructure/cibo_receipt_bound_final_integrated_exam.py": (
            "FINAL_INTEGRATED_CIBO_EXAM"
        ),
        "src/qore/infrastructure/cibo_usd60_prerequisite_receipts.py": (
            "USD60_CAPABILITY_PROGRAM"
        ),
        "src/qore/infrastructure/cibo_ce2i_provider_execution_calibration.py": (
            "PROVIDER_ECONOMICS"
        ),
        "scripts/cibo_phase20_provider_execution_calibration.py": (
            "PROVIDER_ECONOMICS"
        ),
        "src/qore/infrastructure/cibo_ce2i_provider_economics_component_freeze.py": (
            "PROVIDER_ECONOMICS"
        ),
        "src/qore/infrastructure/cibo_integrated_capital_forward_binding.py": (
            "INTEGRATED_CAPITAL_TRUTH"
        ),
        ".github/workflows/cibo-integrated-capital-forward-binding.yml": (
            "INTEGRATED_CAPITAL_TRUTH"
        ),
        ".github/workflows/cibo-architect-a-internal-readiness.yml": (
            "ZERO_OPEN_WORK_GATE"
        ),
        ".github/workflows/cibo-ctrader-demo-provider-economics.yml": (
            "PROVIDER_ECONOMICS"
        ),
        ".github/workflows/cibo-crossboundary-evidence-receipt.yml": (
            "CE2I_CROSS_TOOL_INFRASTRUCTURE"
        ),
    }
    assert orphans == ()


def test_integrator_resolves_architect_b_crossboundary_request_002() -> None:
    inventory = (
        "src/qore/infrastructure/cibo_arch_b_forward_economic_manifest.py",
        "scripts/cibo_phase20_arch_b_forward_economic_manifest.py",
        "src/qore/infrastructure/cibo_ce2i_phase20_t02_structural_oos.py",
        "src/qore/infrastructure/cibo_ce2i_phase20_t03_margin_population.py",
        "src/qore/infrastructure/cibo_ce2i_phase20_t11_execution_population.py",
        "src/qore/infrastructure/cibo_ce2i_phase20_t11_cost_binding.py",
        "src/qore/infrastructure/cibo_ce2i_execution_efficiency.py",
        "src/qore/infrastructure/cibo_ctrader_demo_account_capability.py",
        "src/qore/infrastructure/cibo_ctrader_demo_capability_registry.py",
        "src/qore/infrastructure/cibo_ce2i_provider_execution_calibration.py",
        "scripts/cibo_phase20_provider_execution_calibration.py",
        "src/qore/infrastructure/cibo_t20_capital_release.py",
        "src/qore/infrastructure/cibo_usd60_exam_readiness.py",
        "src/qore/infrastructure/cibo_integrated_capital_forward_binding.py",
        "src/qore/infrastructure/cibo_research_memory.py",
        "tests/infrastructure/test_cibo_risk_integration_closure.py",
        ".github/workflows/cibo-risk-integration-closure.yml",
        "docs/research/CIBO-RISK-INTEGRATION-CLOSURE-V1.md",
    )
    ledger_ids = frozenset(
        {
            "FORWARD_QUALIFICATION",
            "T02",
            "T03",
            "T11",
            "PROVIDER_ECONOMICS",
            "T20",
            "USD60_CAPABILITY_PROGRAM",
            "INTEGRATED_CAPITAL_TRUTH",
            "LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK",
            "RISK_INTEGRATION",
        }
    )

    assignments, orphans = gate._classify_inventory(
        inventory,
        ledger_ids=ledger_ids,
    )

    expected = (
        "FORWARD_QUALIFICATION",
        "FORWARD_QUALIFICATION",
        "T02",
        "T03",
        "T11",
        "T11",
        "T11",
        "PROVIDER_ECONOMICS",
        "PROVIDER_ECONOMICS",
        "PROVIDER_ECONOMICS",
        "PROVIDER_ECONOMICS",
        "T20",
        "USD60_CAPABILITY_PROGRAM",
        "INTEGRATED_CAPITAL_TRUTH",
        "LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK",
        "RISK_INTEGRATION",
        "RISK_INTEGRATION",
        "RISK_INTEGRATION",
    )
    assert tuple(item[1] for item in assignments) == expected
    assert orphans == ()


def test_integrator_classifies_pre_holdout_chain_inventory() -> None:
    inventory = (
        "src/qore/infrastructure/cibo_ce2i_calibration_freeze_manifest.py",
        "src/qore/infrastructure/cibo_receipt_bound_calibration_freeze.py",
        ".github/workflows/cibo-calibration-freeze-manifest.yml",
        "src/qore/infrastructure/cibo_ce2i_pre_holdout_gate.py",
        "src/qore/infrastructure/cibo_receipt_bound_pre_holdout.py",
        "tests/infrastructure/test_cibo_receipt_bound_pre_holdout.py",
    )
    ledger_ids = frozenset(
        {
            "FORWARD_QUALIFICATION",
            "USD60_CAPABILITY_PROGRAM",
        }
    )

    assignments, orphans = gate._classify_inventory(
        inventory,
        ledger_ids=ledger_ids,
    )

    assert dict(assignments) == {
        "src/qore/infrastructure/cibo_ce2i_calibration_freeze_manifest.py": (
            "FORWARD_QUALIFICATION"
        ),
        "src/qore/infrastructure/cibo_receipt_bound_calibration_freeze.py": (
            "FORWARD_QUALIFICATION"
        ),
        ".github/workflows/cibo-calibration-freeze-manifest.yml": (
            "FORWARD_QUALIFICATION"
        ),
        "src/qore/infrastructure/cibo_ce2i_pre_holdout_gate.py": (
            "USD60_CAPABILITY_PROGRAM"
        ),
        "src/qore/infrastructure/cibo_receipt_bound_pre_holdout.py": (
            "USD60_CAPABILITY_PROGRAM"
        ),
        "tests/infrastructure/test_cibo_receipt_bound_pre_holdout.py": (
            "USD60_CAPABILITY_PROGRAM"
        ),
    }
    assert orphans == ()


def test_integrator_classifies_t02_t11_forward_surfaces() -> None:
    inventory = (
        "src/qore/infrastructure/cibo_ce2i_t02_terminal_reason_evidence.py",
        "src/qore/infrastructure/cibo_ce2i_phase20_t02_structural_oos.py",
        ".github/workflows/cibo-t02-forward-structural-oos.yml",
        "docs/research/CIBO-B-T02-FORWARD-STRUCTURAL-OOS-V1.md",
        "src/qore/infrastructure/cibo_ce2i_t11_execution_cost_calibration.py",
        ".github/workflows/cibo-t11-execution-cost-calibration.yml",
        "docs/research/CIBO-B-T03-T11-FORWARD-EVIDENCE-RECONCILIATION-V1.md",
    )
    ledger_ids = frozenset({"T02", "T11"})

    assignments, orphans = gate._classify_inventory(
        inventory,
        ledger_ids=ledger_ids,
    )

    assert dict(assignments) == {
        "src/qore/infrastructure/cibo_ce2i_t02_terminal_reason_evidence.py": "T02",
        "src/qore/infrastructure/cibo_ce2i_phase20_t02_structural_oos.py": "T02",
        ".github/workflows/cibo-t02-forward-structural-oos.yml": "T02",
        "docs/research/CIBO-B-T02-FORWARD-STRUCTURAL-OOS-V1.md": "T02",
        "src/qore/infrastructure/cibo_ce2i_t11_execution_cost_calibration.py": "T11",
        ".github/workflows/cibo-t11-execution-cost-calibration.yml": "T11",
        "docs/research/CIBO-B-T03-T11-FORWARD-EVIDENCE-RECONCILIATION-V1.md": "T11",
    }
    assert orphans == ()


def test_integrator_classifies_new_crossboundary_delivery_surfaces_precisely() -> None:
    inventory = (
        "src/qore/infrastructure/cibo_arch_a_capital_state_delivery.py",
        "tests/infrastructure/test_cibo_arch_a_capital_state_delivery.py",
        ".github/workflows/cibo-architect-a-capital-state-delivery.yml",
        "src/qore/infrastructure/cibo_arch_a_forward_compound_delivery.py",
        "tests/infrastructure/test_cibo_arch_a_forward_compound_delivery.py",
        ".github/workflows/cibo-architect-a-forward-compound-delivery.yml",
        "src/qore/infrastructure/cibo_compound_path_history.py",
        "tests/infrastructure/test_cibo_compound_path_history.py",
        ".github/workflows/cibo-compound-path-history.yml",
        "src/qore/infrastructure/cibo_arch_a_path_evidence_delivery.py",
        "tests/infrastructure/test_cibo_arch_a_path_evidence_delivery.py",
        ".github/workflows/cibo-architect-a-path-evidence-delivery.yml",
        "src/qore/infrastructure/cibo_receipt_bound_usd60_exam_readiness.py",
        "tests/infrastructure/test_cibo_receipt_bound_usd60_exam_readiness.py",
        ".github/workflows/cibo-usd60-pre-exam-readiness.yml",
        ".github/workflows/cibo-arch-b-forward-economic-manifest.yml",
        ".github/workflows/cibo-b-provider-forward-tool-readiness.yml",
        ".github/workflows/cibo-t13-drawdown-reserve-oos-utility.yml",
        ".github/workflows/cibo-t20-capital-release.yml",
        ".github/workflows/cibo-ctrader-demo-account-capability.yml",
    )
    ledger_ids = frozenset(
        {
            "INTEGRATED_CAPITAL_TRUTH",
            "COMPOUND_ENGINE",
            "USD60_CAPABILITY_PROGRAM",
            "FORWARD_QUALIFICATION",
            "T11",
            "T13",
            "T20",
            "PROVIDER_ECONOMICS",
        }
    )

    assignments, orphans = gate._classify_inventory(
        inventory,
        ledger_ids=ledger_ids,
    )

    expected = (
        "INTEGRATED_CAPITAL_TRUTH",
        "INTEGRATED_CAPITAL_TRUTH",
        "INTEGRATED_CAPITAL_TRUTH",
        "COMPOUND_ENGINE",
        "COMPOUND_ENGINE",
        "COMPOUND_ENGINE",
        "INTEGRATED_CAPITAL_TRUTH",
        "INTEGRATED_CAPITAL_TRUTH",
        "INTEGRATED_CAPITAL_TRUTH",
        "INTEGRATED_CAPITAL_TRUTH",
        "INTEGRATED_CAPITAL_TRUTH",
        "INTEGRATED_CAPITAL_TRUTH",
        "USD60_CAPABILITY_PROGRAM",
        "USD60_CAPABILITY_PROGRAM",
        "USD60_CAPABILITY_PROGRAM",
        "FORWARD_QUALIFICATION",
        "T11",
        "T13",
        "T20",
        "PROVIDER_ECONOMICS",
    )
    assert tuple(item[1] for item in assignments) == expected
    assert orphans == ()


def test_integrator_classifies_ctrader_taxonomy_and_t17_limited_risk() -> None:
    inventory = (
        "src/qore/infrastructure/cibo_ctrader_demo_instrument_taxonomy.py",
        "tests/infrastructure/test_cibo_ctrader_demo_instrument_taxonomy.py",
        "src/qore/infrastructure/cibo_ce2i_t17_limited_risk_capability.py",
        "scripts/cibo_t17_limited_risk_capability_probe.py",
        "tests/infrastructure/test_cibo_ce2i_t17_limited_risk_capability.py",
        "tests/infrastructure/test_cibo_t17_limited_risk_capability_probe.py",
    )
    ledger_ids = frozenset({"PROVIDER_ECONOMICS", "T17"})

    assignments, orphans = gate._classify_inventory(
        inventory,
        ledger_ids=ledger_ids,
    )

    assert dict(assignments) == {
        "src/qore/infrastructure/cibo_ctrader_demo_instrument_taxonomy.py": (
            "PROVIDER_ECONOMICS"
        ),
        "tests/infrastructure/test_cibo_ctrader_demo_instrument_taxonomy.py": (
            "PROVIDER_ECONOMICS"
        ),
        "src/qore/infrastructure/cibo_ce2i_t17_limited_risk_capability.py": "T17",
        "scripts/cibo_t17_limited_risk_capability_probe.py": "T17",
        "tests/infrastructure/test_cibo_ce2i_t17_limited_risk_capability.py": "T17",
        "tests/infrastructure/test_cibo_t17_limited_risk_capability_probe.py": "T17",
    }
    assert orphans == ()
