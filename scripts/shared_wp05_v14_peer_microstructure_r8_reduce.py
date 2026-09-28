"""Reduce exact source-only WP-05 V14 peer acquisition reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

from qore.infrastructure.core_stack_v2.active_perception_v14_peer_acquisition import (
    EXPECTED_MANIFEST_SHA256,
    V14PeerFamily,
    reduce_v14_peer_reports,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    reduced: dict[str, object] = {}
    for peer in V14PeerFamily:
        pattern = f"{peer.value.lower()}-shard-*-report.json"
        reports: list[dict[str, object]] = []
        for path in sorted(args.reports_dir.glob(pattern)):
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError(f"V14 peer report must be object: {path.name}")
            reports.append(cast(dict[str, object], raw))
        reduced[peer.value] = reduce_v14_peer_reports(
            tuple(reports),
            peer=peer,
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        )

    payload = {
        "identity": "QORE_SHARED_WP05_V14_CROSS_MARKET_SOURCE_ACQUISITION_001",
        "partition": "r8_source_only",
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "peers": reduced,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "scientific_v14_outcomes_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
