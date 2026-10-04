#!/usr/bin/env python3
"""B-16 scientific-value exam readiness census.

This command never opens research labels and never executes the exam. It only
counts sensors that satisfy the causal evidence prerequisites required before a
preregistered scientific-value exam may start.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worklist", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload: Any = json.loads(args.worklist.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("worklist must contain JSON object")
    if payload.get("identity") != "SHARED_B_SENSOR_QUALIFICATION_WORKLIST_001":
        raise ValueError("unexpected B16 worklist identity")
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("B16 worklist records missing")
    ready = sorted(
        str(row["provider_symbol"])
        for row in records
        if isinstance(row, dict)
        and row.get("state") == "READY_FOR_SCIENTIFIC_VALUE_EXAM"
    )
    result = {
        "identity": "SHARED_B_SENSOR_SCIENTIFIC_VALUE_EXAM_READINESS_001",
        "worklist_fingerprint_sha256": payload.get(
            "worklist_fingerprint_sha256"
        ),
        "sensor_count": len(records),
        "ready_for_scientific_value_exam_count": len(ready),
        "ready_symbols": ready,
        "research_labels_opened": False,
        "exam_executed": False,
        "automatic_admission": False,
        "final_shared_holdout_opened": False,
        "productive_authority": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
