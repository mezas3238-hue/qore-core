"""CLI for Architect-B canonical calendar qualification worklist."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b_canonical_calendar_worklist import (
    build_canonical_calendar_qualification_worklist,
)


def _load(path: Path) -> dict[str, object]:
    value: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return cast(dict[str, object], value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity-frontier", type=Path, required=True)
    parser.add_argument("--fx-hours-boundary", type=Path, required=True)
    parser.add_argument("--commodity-pack", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_canonical_calendar_qualification_worklist(
        identity_frontier=_load(args.identity_frontier),
        fx_hours_boundary=_load(args.fx_hours_boundary),
        commodity_pack=_load(args.commodity_pack),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": payload["status"],
        "sensor_count": payload["sensor_count"],
        "canonical_calendar_verified_count": payload[
            "canonical_calendar_verified_count"
        ],
        "category_counts": payload["category_counts"],
        "b07_complete": payload["b07_complete"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
