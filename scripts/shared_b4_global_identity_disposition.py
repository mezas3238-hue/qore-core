"""CLI for Architect B4 exact identity-disposition closure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b4_global_identity_disposition import (
    build_identity_disposition_registry,
)


def _load(path: Path) -> dict[str, object]:
    value: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return cast(dict[str, object], value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontier-v3", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_identity_disposition_registry(
        frontier_v3=_load(args.frontier_v3),
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
                "calendar_qualification_candidate_count": payload[
                    "calendar_qualification_candidate_count"
                ],
                "explicit_unknown_or_limited_count": payload[
                    "explicit_unknown_or_limited_count"
                ],
                "b06_epistemic_closure_complete": payload[
                    "b06_epistemic_closure_complete"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
