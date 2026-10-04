#!/usr/bin/env python3
"""Materialize B16 read-only source-acquisition queue."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b_sensor_source_acquisition_queue import (
    build_b16_source_acquisition_queue,
)

_CREDENTIAL_GROUPS = (
    ("QORE_CTRADER_CLIENT_ID", "QORE_CTRADER_DEMO_CLIENT_ID"),
    ("QORE_CTRADER_CLIENT_SECRET", "QORE_CTRADER_DEMO_CLIENT_SECRET"),
    ("QORE_CTRADER_ACCESS_TOKEN", "QORE_CTRADER_DEMO_ACCESS_TOKEN"),
    ("QORE_CTRADER_REFRESH_TOKEN", "QORE_CTRADER_DEMO_REFRESH_TOKEN"),
    ("QORE_CTRADER_DEMO_ACCOUNT_ID", "QORE_CTRADER_ACCOUNT_ID"),
)


def _credentials_available() -> bool:
    return all(
        any(bool(os.environ.get(name, "")) for name in group)
        for group in _CREDENTIAL_GROUPS
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worklist", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw: Any = json.loads(args.worklist.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("worklist must contain JSON object")
    payload = build_b16_source_acquisition_queue(
        cast(dict[str, object], raw),
        provider_credentials_available=_credentials_available(),
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
                "state_counts": payload["state_counts"],
                "source_acquisition_candidate_count": payload[
                    "source_acquisition_candidate_count"
                ],
                "execution_ready_candidate_count": payload[
                    "execution_ready_candidate_count"
                ],
                "provider_credentials_available": payload[
                    "provider_credentials_available"
                ],
                "execution_status": payload["execution_status"],
                "partial_source_blindspot_symbols": payload[
                    "partial_source_blindspot_symbols"
                ],
                "queue_fingerprint_sha256": payload[
                    "queue_fingerprint_sha256"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
