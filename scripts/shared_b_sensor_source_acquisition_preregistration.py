#!/usr/bin/env python3
"""CLI for B16 source-only acquisition preregistration."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b_sensor_source_acquisition_preregistration import (
    build_b16_source_acquisition_preregistration,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw: Any = json.loads(args.queue.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("source queue must contain JSON object")
    payload = build_b16_source_acquisition_preregistration(
        cast(dict[str, object], raw),
        preregistered_at=datetime.now(UTC),
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
                "candidate_count": payload["candidate_count"],
                "candidate_set_sha256": payload["candidate_set_sha256"],
                "pilot_indices": payload["pilot_indices"],
                "preregistration_fingerprint_sha256": payload[
                    "preregistration_fingerprint_sha256"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
