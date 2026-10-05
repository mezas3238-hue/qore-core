#!/usr/bin/env python3
"""Integrator-1 runtime runner for the canonical WP11 blocker audit.

This runner does not create missing scientific evidence. It projects stronger
same-run MC23/MC24 evidence into the legacy prerequisite field names expected by
WP11, invokes the canonical monotonic blocker audit, writes the exact blocker
set, and fails closed while any blocker remains.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from shared_wp11_exact_blocker_audit import audit_blockers

MC23_ID = "QORE_SHARED_MC23_VALIDATED_NOVEL_REGIME_ADAPTATION_001"
MC24_ID = "QORE_SHARED_MC24_VALIDATED_ADAPTATION_HALF_LIFE_001"
MC25_LINEAGE_ID = "QORE_SHARED_MC25_WP04_V3B_LINEAGE_INTEGRITY_STRESS_001"
MC25_PERFORMANCE_ID = "QORE_SHARED_MC25_WP04_V3B_PERFORMANCE_STRESS_001"


def _load_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not root.is_dir():
        raise ValueError(f"runtime evidence directory missing: {root}")
    for path in sorted(root.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", type=Path, default=Path("result"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows = _load_rows(args.result_dir)
    mc23 = [copy.deepcopy(row) for row in rows if row.get("identity") == MC23_ID]
    mc24 = [copy.deepcopy(row) for row in rows if row.get("identity") == MC24_ID]
    mc25 = [
        copy.deepcopy(row)
        for row in rows
        if row.get("identity") in {MC25_LINEAGE_ID, MC25_PERFORMANCE_ID}
        or any(
            key in row
            for key in (
                "formal_stress_stage_completed",
                "shadow_stage_bound",
                "certification_stage_bound",
                "promotion_allowed",
            )
        )
    ]

    for row in mc23:
        if (
            row.get("real_novel_regime_validated_adaptation") is True
            and row.get("mc23_completed_and_proven") is True
        ):
            row["real_novelty_detection_bound"] = True

    for row in mc24:
        if (
            row.get("prior_real_regression_suite_bound") is True
            and row.get("mc24_completed_and_proven") is True
        ):
            row["real_adaptation_regression_suite_bound"] = True

    payload = audit_blockers(
        mc23_rows=tuple(mc23),
        mc24_rows=tuple(mc24),
        mc25_rows=tuple(mc25),
    )
    payload["integrator_projection_only"] = True
    payload["scientific_evidence_created_by_runner"] = False
    payload["runtime_evidence_dir"] = str(args.result_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    raise SystemExit(0 if payload.get("wp11_completed_and_proven") is True else 2)


if __name__ == "__main__":
    main()
