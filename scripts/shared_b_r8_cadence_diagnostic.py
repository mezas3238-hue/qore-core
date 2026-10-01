"""CLI for Architect-B R8 empirical cadence diagnostic."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b_r8_cadence_diagnostic import (
    build_r8_empirical_cadence_diagnostic,
)


def _load(path: Path) -> dict[str, object]:
    value: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return cast(dict[str, object], value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--raw-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_r8_empirical_cadence_diagnostic(
        raw_root=args.raw_root,
        raw_manifest=_load(args.raw_manifest),
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
                "sensor_side_count": payload["sensor_side_count"],
                "cadence_policy_registry_frozen": payload[
                    "cadence_policy_registry_frozen"
                ],
                "b08_complete": payload["b08_complete"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
