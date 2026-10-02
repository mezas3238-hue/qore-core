"""Reduce all sanitized WP-05 V12 full-R8 shard reports fail-closed."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

from qore.infrastructure.core_stack_v2.active_perception_v12_full_acquisition import (
    FROZEN_WINDOW_COUNT,
    reduce_v12_full_acquisition_reports,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    paths = tuple(sorted(args.reports_dir.glob("shard-*-report.json")))
    reports: list[dict[str, object]] = []
    for path in paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"shard report is not a JSON object: {path.name}")
        reports.append(cast(dict[str, object], raw))

    reduced = reduce_v12_full_acquisition_reports(
        tuple(reports),
        expected_manifest_sha256=args.expected_manifest_sha256,
        expected_window_count=FROZEN_WINDOW_COUNT,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(reduced, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(reduced, sort_keys=True))


if __name__ == "__main__":
    main()
