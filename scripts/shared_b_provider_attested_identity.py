"""CLI for Architect-B provider-attested identity boundary evidence."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b_provider_attested_identity import (
    build_provider_attested_identity_boundary,
)


def _load(path: Path) -> dict[str, object]:
    value: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return cast(dict[str, object], value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-schedule", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--known-at", default=None)
    args = parser.parse_args()

    known_at = (
        datetime.fromisoformat(args.known_at)
        if args.known_at is not None
        else datetime.now(UTC)
    )
    payload = build_provider_attested_identity_boundary(
        provider_schedule=_load(args.provider_schedule),
        known_at=known_at,
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
                "index_sensor_count": payload["index_sensor_count"],
                "cryptocurrency_sensor_count": payload[
                    "cryptocurrency_sensor_count"
                ],
                "provider_neutral_reference_identity_verified_count": (
                    payload[
                        "provider_neutral_reference_identity_verified_count"
                    ]
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
