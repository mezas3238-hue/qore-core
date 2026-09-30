"""CLI for Architect-B exact sensor qualification frontier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b_sensor_qualification_frontier import (
    build_sensor_qualification_frontier,
)


def _load(path: Path) -> dict[str, object]:
    value: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return cast(dict[str, object], value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sensor-registry", type=Path, required=True)
    parser.add_argument("--identity-frontier", type=Path, required=True)
    parser.add_argument("--calendar-worklist", type=Path, required=True)
    parser.add_argument("--active-perception-boundary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_sensor_qualification_frontier(
        sensor_registry=_load(args.sensor_registry),
        identity_frontier=_load(args.identity_frontier),
        calendar_worklist=_load(args.calendar_worklist),
        active_perception_boundary=_load(args.active_perception_boundary),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": payload["status"],
        "sensor_count": payload["sensor_count"],
        "identity_next_step_ready_count": payload[
            "identity_next_step_ready_count"
        ],
        "full_real_source_evidence_count": payload[
            "full_real_source_evidence_count"
        ],
        "partial_real_source_evidence_count": payload[
            "partial_real_source_evidence_count"
        ],
        "admitted_count": payload["admitted_count"],
        "b16_complete": payload["b16_complete"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
