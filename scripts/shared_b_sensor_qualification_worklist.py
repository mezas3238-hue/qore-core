#!/usr/bin/env python3
"""CLI for B-16 outcome-free sensor qualification worklist."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b_sensor_qualification_worklist import (
    build_sensor_qualification_worklist,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontier", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    raw: Any = json.loads(args.frontier.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("frontier must contain JSON object")
    payload = build_sensor_qualification_worklist(
        cast(dict[str, object], raw)
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "sensor_count": payload["sensor_count"],
                "state_counts": payload["state_counts"],
                "gap_counts": payload["gap_counts"],
                "minimum_missing_evidence_count": payload[
                    "minimum_missing_evidence_count"
                ],
                "nearest_evidence_completion_symbols": payload[
                    "nearest_evidence_completion_symbols"
                ],
                "ready_for_scientific_value_exam_count": payload[
                    "ready_for_scientific_value_exam_count"
                ],
                "causal_qualification_complete_count": payload[
                    "causal_qualification_complete_count"
                ],
                "worklist_fingerprint_sha256": payload[
                    "worklist_fingerprint_sha256"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
