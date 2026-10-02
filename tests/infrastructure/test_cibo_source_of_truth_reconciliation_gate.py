from __future__ import annotations

import importlib.util
import json
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts/cibo_source_of_truth_reconciliation_gate.py"
)
SPEC = importlib.util.spec_from_file_location(
    "cibo_source_of_truth_reconciliation_gate",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_current_integrated_checkpoint_is_internally_reconciled() -> None:
    errors = gate.validate_reconciliation()

    assert errors == []
    report = gate.build_report(git_sha="a" * 40)
    assert report["pass"] is True
    ledger = _load(gate.LEDGER)
    summary = ledger["current_summary"]
    assert report["mandatory_count"] == summary["mandatory_count"]
    assert report["terminal_count"] == summary["terminal_count"]
    assert report["open_count"] == summary["open_count"]
    assert report["all_child_delta_files_accounted"] is True
    assert report["world_cup_mandatory"] is True
    assert report["productive_authority"] is False
    assert report["certification_claim"] is False


def test_non_terminal_maturity_cannot_be_counted_terminal(
    tmp_path: Path,
    monkeypatch,
) -> None:
    payload = _load(gate.LEDGER)
    row = next(
        item
        for item in payload["workstreams"]
        if item["id"] == "FRESH_OOS"
    )
    row["terminal_disposition"] = "EXTERNAL_DEPENDENCY_BLOCKED"
    payload["current_summary"]["terminal_count"] += 1
    payload["current_summary"]["open_count"] -= 1
    ledger = tmp_path / "ledger.json"
    _write(ledger, payload)
    monkeypatch.setattr(gate, "LEDGER", ledger)

    errors = gate.validate_reconciliation()

    assert (
        "FRESH_OOS non-terminal maturity cannot have terminal disposition"
        in errors
    )


def test_world_cup_cannot_be_dropped_from_integrated_ledger(
    tmp_path: Path,
    monkeypatch,
) -> None:
    payload = _load(gate.LEDGER)
    row = next(
        item
        for item in payload["workstreams"]
        if item["id"] == "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM"
    )
    row["mandatory"] = False
    row["certification_blocking"] = False
    payload["current_summary"]["mandatory_count"] -= 1
    payload["current_summary"]["open_count"] -= 1
    ledger = tmp_path / "ledger.json"
    _write(ledger, payload)
    monkeypatch.setattr(gate, "LEDGER", ledger)

    errors = gate.validate_reconciliation()

    assert "integrated mandatory workstream count must remain 64" in errors
    assert (
        "required exam not mandatory: WORLD_CUP_MAXIMUM_CAPABILITY_EXAM"
        in errors
    )
    assert (
        "required exam not certification-blocking: "
        "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM"
    ) in errors


def test_child_head_drift_is_rejected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    payload = _load(gate.ACCOUNTING)
    payload["architect_b"]["head_sha"] = "f" * 40
    accounting = tmp_path / "accounting.json"
    _write(accounting, payload)
    monkeypatch.setattr(gate, "ACCOUNTING", accounting)

    errors = gate.validate_reconciliation()

    assert "architect_b child-accounting HEAD drift" in errors


def test_evidence_register_must_follow_latest_child_head(
    tmp_path: Path,
    monkeypatch,
) -> None:
    payload = _load(gate.EVIDENCE)
    row = next(
        item
        for item in payload["pending_candidates"]
        if item["owner"] == "ARCHITECT_A"
    )
    row["latest_head_sha"] = "e" * 40
    evidence = tmp_path / "evidence.json"
    _write(evidence, payload)
    monkeypatch.setattr(gate, "EVIDENCE", evidence)

    errors = gate.validate_reconciliation()

    assert "ARCHITECT_A evidence-register HEAD drift" in errors


def test_terminal_risk_requires_accepted_success_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    payload = _load(gate.EVIDENCE)
    payload["accepted_batches"] = [
        item
        for item in payload["accepted_batches"]
        if item.get("owner") != "INTEGRATOR_RISK_RECONCILIATION"
    ]
    evidence = tmp_path / "evidence.json"
    _write(evidence, payload)
    monkeypatch.setattr(gate, "EVIDENCE", evidence)

    errors = gate.validate_reconciliation()

    assert "Risk terminal ledger lacks accepted SUCCESS evidence" in errors


def test_current_governance_docs_preserve_two_exam_sequence() -> None:
    errors = gate.validate_reconciliation()

    assert not any(
        "roadmap missing canonical phrase" in item
        or "world_cup missing canonical phrase" in item
        or "sequence missing canonical phrase" in item
        for item in errors
    )
