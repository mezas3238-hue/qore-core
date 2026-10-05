#!/usr/bin/env python3
"""Fail-closed scientific evidence gate for Shared Integrator 1 A1 lane."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

IDENTITY = "QORE_SHARED_INTEGRATOR_1_A1_SCIENTIFIC_EVIDENCE_GATE_001"
MC14_ID = "QORE_SHARED_A1_MC14_SHARED_LAB_REPLAY_RUNNER_001"
MC18_ID = "QORE_SHARED_A1_MC18_SHARED_LAB_CALIBRATION_RUNNER_001"
A1_FUNCTIONAL_ID = "QORE_SHARED_A1_FUNCTIONAL_CAUSALITY_EXAM_001"

ALLOWED_MC14_XAUUSD = {
    "TEMPORALLY_REPLICATED_RESEARCH_RELATION_FOUND",
    "FALSIFIED_AND_CLOSED_FOR_THIS_MECHANISM",
    "INSUFFICIENT_DO_NOT_INFER",
}


def _rows(roots: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _safe(row: dict[str, Any]) -> bool:
    return (
        row.get("protected_final_holdout_opened") is not True
        and row.get("productive_authority") is not True
        and row.get("knowledge_auto_promotion") is not True
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--runtime-evidence-dir",
        type=Path,
        action="append",
        default=[],
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    roots = [Path("docs/shared/evidence"), *args.runtime_evidence_dir]
    rows = _rows(roots)

    functional = next(
        (
            row for row in rows
            if row.get("identity") == A1_FUNCTIONAL_ID
            and row.get("status") == "A1_FUNCTIONAL_CAUSALITY_ENGINEERING_PASS"
            and _safe(row)
        ),
        None,
    )

    mc14 = next(
        (
            row for row in rows
            if row.get("identity") == MC14_ID
            and row.get("status") == "GOVERNED_REPLAY_EXECUTION_COMPLETE"
            and _safe(row)
        ),
        None,
    )
    mc14_terminal = False
    mc14_disposition = None
    if mc14 is not None:
        disposition = mc14.get("scientific_disposition")
        if isinstance(disposition, dict):
            xauusd = disposition.get("XAUUSD_DEFENSIVE_PROXY")
            us2000 = disposition.get("US2000_BREADTH_PROXY")
            mc14_disposition = xauusd
            mc14_terminal = (
                xauusd in ALLOWED_MC14_XAUUSD
                and us2000 == "INSUFFICIENT_DO_NOT_INFER"
                and mc14.get("lab_task_pass_means_only_execution_integrity") is True
            )

    mc18 = next(
        (
            row for row in rows
            if row.get("identity") == MC18_ID
            and row.get("status") == "GOVERNED_CALIBRATION_EXECUTION_COMPLETE"
            and _safe(row)
        ),
        None,
    )
    mc18_disposition = None if mc18 is None else mc18.get("scientific_disposition")
    mc18_terminal_falsification = (
        mc18 is not None
        and mc18_disposition == "MC18_CONSUMED_DEVELOPMENT_CALIBRATION_FALSIFIED"
        and mc18.get("next_gate") == "FALSIFIED_AND_KEEP_RAW_ENGINE_UNCALIBRATED"
        and mc18.get("mc18_completed_and_proven") is False
    )
    mc18_calibration_pass_waiting_independent = (
        mc18 is not None
        and mc18_disposition == "MC18_CONSUMED_DEVELOPMENT_CALIBRATION_PASS"
        and mc18.get("next_gate") == "FREEZE_FOR_FUTURE_INDEPENDENT_MC27_EVALUATION"
        and mc18.get("mc18_completed_and_proven") is False
    )

    blockers: list[str] = []
    if functional is None:
        blockers.append("A1_FUNCTIONAL_CAUSALITY_EXECUTION")
    if not mc14_terminal:
        blockers.append("A1_MC14_GOVERNED_REPLAY_TERMINAL_DISPOSITION")
    if mc18 is None:
        blockers.append("A1_MC18_CONSUMED_DEVELOPMENT_CALIBRATION")
    elif mc18_calibration_pass_waiting_independent:
        blockers.append("A1_MC18_FUTURE_INDEPENDENT_MC27_EVIDENCE")
    elif not mc18_terminal_falsification:
        blockers.append("A1_MC18_VALID_TERMINAL_OR_NEXT_GATE_DISPOSITION")

    blockers = sorted(set(blockers))
    terminal = not blockers
    payload = {
        "identity": IDENTITY,
        "status": (
            "I1_A1_SCIENTIFIC_PACKAGE_TERMINAL"
            if terminal
            else "I1_A1_SCIENTIFIC_PACKAGE_OPEN"
        ),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "functional_engineering_pass": functional is not None,
        "mc14_terminal": mc14_terminal,
        "mc14_disposition": mc14_disposition,
        "mc18_disposition": mc18_disposition,
        "mc18_terminal_falsification": mc18_terminal_falsification,
        "mc18_waiting_future_independent_mc27": (
            mc18_calibration_pass_waiting_independent
        ),
        "scientific_pass_claimed": False,
        "productive_authority": False,
        "protected_final_holdout_opened": False,
        "outcome_aware_rescue_used": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    raise SystemExit(0 if terminal else 2)


if __name__ == "__main__":
    main()
