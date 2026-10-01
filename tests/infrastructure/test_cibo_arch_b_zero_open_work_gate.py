from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest


def _load_gate_module() -> ModuleType:
    path = Path("scripts/cibo_arch_b_zero_open_work_gate.py")
    spec = importlib.util.spec_from_file_location(
        "cibo_arch_b_zero_open_work_gate",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Architect-B zero-open gate")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load_gate_module()


def _package() -> dict:
    completed = {
        "T01",
        "T17",
        "RISK_INTEGRATION",
        "CMA_FOUNDATION_INTEGRATION",
        "LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK",
    }
    rows = []
    for workstream_id in gate._B_IDS:
        if workstream_id in completed:
            rows.append(
                {
                    "id": workstream_id,
                    "recommendation": (
                        "FALSIFIED_AND_CLOSED"
                        if workstream_id == "T17"
                        else "COMPLETED_AND_PROVEN"
                    ),
                    "certification_blocking": False,
                    "blockers": [],
                }
            )
        else:
            rows.append(
                {
                    "id": workstream_id,
                    "recommendation": "EXTERNAL_DEPENDENCY_BLOCKED",
                    "certification_blocking": True,
                    "blockers": ["REAL_EXTERNAL_EVIDENCE_REQUIRED"],
                }
            )
    return {
        "schema": "CIBO_ARCH_B_TERMINAL_DISPOSITION_PACKAGE_V1",
        "governance": {
            "draft_unmerged": True,
            "master_ledger_modified": False,
            "holdout_2017h1_opened": False,
            "live_authority": False,
            "productive_authority": False,
            "real_capital_authority": False,
        },
        "dispositions": rows,
    }


def _write(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_b_gate_passes_scope_closure_but_keeps_certification_blocked(
    tmp_path: Path,
) -> None:
    package = tmp_path / "package.json"
    _write(package, _package())

    verdict = gate.evaluate_gate(package_path=package)

    assert verdict.passed is True
    assert verdict.b_workstream_count == 15
    assert verdict.terminal_count == 15
    assert verdict.open_workstream_ids == ()
    assert verdict.certification_ready is False
    assert len(verdict.completed_or_falsified_ids) == 5
    assert len(verdict.external_dependency_blocked_ids) == 10
    assert verdict.certification_blocking_ids == (
        verdict.external_dependency_blocked_ids
    )
    assert verdict.reasons == (
        "ARCHITECT_B_TERMINAL_EXTERNAL_DEPENDENCIES_STILL_BLOCK_CERTIFICATION",
    )


def test_b_gate_rejects_external_dependency_without_blocker(
    tmp_path: Path,
) -> None:
    payload = _package()
    row = next(
        item
        for item in payload["dispositions"]
        if item["recommendation"] == "EXTERNAL_DEPENDENCY_BLOCKED"
    )
    row["blockers"] = []
    package = tmp_path / "package.json"
    _write(package, payload)

    with pytest.raises(
        gate.ArchitectBZeroOpenWorkGateError,
        match="external dependency",
    ):
        gate.evaluate_gate(package_path=package)


def test_b_gate_rejects_missing_b_workstream(tmp_path: Path) -> None:
    payload = _package()
    payload["dispositions"].pop()
    package = tmp_path / "package.json"
    _write(package, payload)

    with pytest.raises(
        gate.ArchitectBZeroOpenWorkGateError,
        match="set/order drift",
    ):
        gate.evaluate_gate(package_path=package)


def test_b_gate_rejects_holdout_or_runtime_authority(tmp_path: Path) -> None:
    payload = _package()
    payload["governance"]["holdout_2017h1_opened"] = True
    package = tmp_path / "package.json"
    _write(package, payload)

    with pytest.raises(
        gate.ArchitectBZeroOpenWorkGateError,
        match="governance violation",
    ):
        gate.evaluate_gate(package_path=package)
