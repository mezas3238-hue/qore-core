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
    return {
        "schema": "QORE_CIBO_MASTER_OPEN_WORK_LEDGER_V1",
        "terminal_dispositions": [
            "COMPLETED_AND_PROVEN",
            "FALSIFIED_AND_CLOSED",
            "SUPERSEDED_WITH_PROVEN_LINEAGE",
            "EXTERNAL_DEPENDENCY_BLOCKED",
        ],
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
                "evidence_refs": [],
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
