"""CLI for Architect B4 temporal-disposition registry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b4_temporal_disposition_registry import (
    build_temporal_disposition_registry,
)


def _load(path: Path) -> dict[str, object]:
    value: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return cast(dict[str, object], value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calendar-worklist", type=Path, required=True)
    parser.add_argument("--r8-historical-frontier", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_temporal_disposition_registry(
        calendar_worklist=_load(args.calendar_worklist),
        r8_historical_frontier=_load(args.r8_historical_frontier),
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
                "sensor_count": payload["sensor_count"],
                "r8_historical_session_partial_count": payload[
                    "r8_historical_session_partial_count"
                ],
                "comparability_eligible_count": payload[
                    "comparability_eligible_count"
                ],
                "b07_epistemic_closure_complete": payload[
                    "b07_epistemic_closure_complete"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
