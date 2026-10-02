"""Run the frozen WP-05 V12 source-only raw integrity audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.core_stack_v2.active_perception_v12_source_integrity import (
    audit_v12_source_only_dataset,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--expected-git-sha", required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--expected-global-dataset-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = audit_v12_source_only_dataset(
        raw_root=args.raw_root,
        expected_git_sha=args.expected_git_sha,
        expected_manifest_sha256=args.expected_manifest_sha256,
        expected_global_dataset_sha256=args.expected_global_dataset_sha256,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "raw_page_count": report["raw_page_count"],
                "raw_bid_tick_count": report["raw_bid_tick_count"],
                "raw_ask_tick_count": report["raw_ask_tick_count"],
                "page_key_duplicate_count": report["page_key_duplicate_count"],
                "page_key_conflict_count": report["page_key_conflict_count"],
                "strict_page_time_overlap_count": report[
                    "strict_page_time_overlap_count"
                ],
                "exact_boundary_row_repeat_count": report[
                    "exact_boundary_row_repeat_count"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
