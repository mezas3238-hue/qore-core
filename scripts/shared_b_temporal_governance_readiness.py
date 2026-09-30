"""CLI for Architect-B B-08 temporal governance readiness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b_temporal_governance_readiness import (
    build_temporal_governance_readiness,
)


def _load(path: Path) -> dict[str, object]:
    value: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return cast(dict[str, object], value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calendar-worklist", type=Path, required=True)
    parser.add_argument("--source-clock-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_temporal_governance_readiness(
        calendar_worklist=_load(args.calendar_worklist),
        source_clock_audit=_load(args.source_clock_audit),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": payload["status"],
        "source_clock_tick_count": payload["source_clock_tick_count"],
        "temporal_governance_status": payload["temporal_governance_status"],
        "temporal_governance_blockers": payload["temporal_governance_blockers"],
        "b08_complete": payload["b08_complete"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
