"""CLI for Architect-B R8 temporal calibration eligibility."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b_r8_calibration_eligibility import (
    build_r8_temporal_calibration_eligibility,
)


def _load(path: Path) -> dict[str, object]:
    value: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return cast(dict[str, object], value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cadence-diagnostic", type=Path, required=True)
    parser.add_argument("--historical-calendar", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_r8_temporal_calibration_eligibility(
        cadence_diagnostic=_load(args.cadence_diagnostic),
        historical_calendar=_load(args.historical_calendar),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "joint_calibration_eligible_sensor_count": payload[
                    "joint_calibration_eligible_sensor_count"
                ],
                "b08_complete": payload["b08_complete"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
