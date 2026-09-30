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
    payload["workstreams"].append(
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
        }
    )
    payload["current_summary"] = {
        "mandatory_count": 2,
        "terminal_count": 1,
        "open_count": 1,
        "zero_open_work_pass": False,
        "final_certification_candidate": False,
    }
    return payload


def test_pre_exam_gate_excludes_only_final_exam(
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
    assert strict.open_workstream_ids == ("FINAL_INTEGRATED_CIBO_EXAM",)


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
        "mandatory_count": 2,
        "terminal_count": 0,
        "open_count": 2,
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
