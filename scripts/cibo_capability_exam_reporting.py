"""Render the preregistered final CIBO capability-exam reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_capability_exam_reporting import (
    build_final_reporting_payloads,
    economic_lane_comparison_csv,
    function_accountability_csv,
    trader_columns_csv,
)


def _json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"expected JSON object: {path}")
    return raw


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--capability-report", type=Path, required=True)
    parser.add_argument("--execution-report", type=Path, required=True)
    parser.add_argument("--lane-diagnostics", type=Path, required=True)
    parser.add_argument("--compound-lane-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    payload = build_final_reporting_payloads(
        batch=_json(args.batch),
        capability_report=_json(args.capability_report),
        execution_report=_json(args.execution_report),
        lane_diagnostics=_json(args.lane_diagnostics),
        compound_lane_report=_json(args.compound_lane_report),
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    columns = payload["trader_columns"]
    functions = payload["function_accountability"]
    economics = payload["economic_lane_comparison"]

    _write_json(args.output_dir / "trader-column-report.json", columns)
    _write_json(
        args.output_dir / "cibo-function-accountability.json",
        functions,
    )
    _write_json(
        args.output_dir / "economic-lane-comparison.json",
        economics,
    )
    (args.output_dir / "trader-column-report.csv").write_text(
        trader_columns_csv(payload),
        encoding="utf-8",
    )
    (args.output_dir / "cibo-function-accountability.csv").write_text(
        function_accountability_csv(payload),
        encoding="utf-8",
    )
    (args.output_dir / "economic-lane-comparison.csv").write_text(
        economic_lane_comparison_csv(payload),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "candidate_id": payload["candidate_id"],
                "trader_columns": len(columns["traders"]),
                "functions_accounted": len(functions),
                "economic_lanes": [
                    item["lane_id"] for item in economics
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
