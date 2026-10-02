"""Reduce exact source-only WP-05 V15 cross-asset acquisition reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

from qore.infrastructure.core_stack_v2.active_perception_v15_cross_asset_acquisition import (
    EXPECTED_MANIFEST_SHA256,
    V15CrossAssetFamily,
    reduce_v15_cross_asset_reports,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    reduced: dict[str, object] = {}
    for family in V15CrossAssetFamily:
        pattern = f"{family.value.lower()}-shard-*-report.json"
        reports: list[dict[str, object]] = []
        for path in sorted(args.reports_dir.glob(pattern)):
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError(f"V15 report must be object: {path.name}")
            reports.append(cast(dict[str, object], raw))
        reduced[family.value] = reduce_v15_cross_asset_reports(
            tuple(reports),
            family=family,
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        )

    payload = {
        "identity": "QORE_SHARED_WP05_V15_CROSS_ASSET_SOURCE_ACQUISITION_001",
        "partition": "r8_source_only",
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "sensors": reduced,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "scientific_v15_outcomes_opened": False,
        "productive_authority": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
