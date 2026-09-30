from __future__ import annotations

import json
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
