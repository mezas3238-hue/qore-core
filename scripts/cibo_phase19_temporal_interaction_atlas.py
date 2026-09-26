"""Build a sealed Phase-19 temporal interaction atlas from chronology evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_phase19_interaction_evidence import (
    Phase19TemporalOverlapAtlas,
    Phase19TraderPairOverlap,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
)

EXPECTED_SCHEMA = "qore.cibo.phase19.integrated_chronology_replay.v1"
EXPECTED_STATUS = "CHRONOLOGY_GREEN_USD_PROVIDER_ECONOMICS_BLOCKED"


def _load(path: Path) -> tuple[bytes, dict[str, Any]]:
    raw = path.read_bytes()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("Phase 19 chronology report must be an object")
    return raw, payload


def build_atlas(
    *,
    report_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    raw, report = _load(report_path)
    if report.get("schema") != EXPECTED_SCHEMA:
        raise ValueError("Phase 19 chronology report schema drift")
    if report.get("status") != EXPECTED_STATUS:
        raise ValueError("Phase 19 chronology report status drift")

    readiness = report.get("readiness")
    if not isinstance(readiness, dict):
        raise ValueError("Phase 19 readiness payload missing")
    if readiness.get("phase18_population_complete") is not True:
        raise ValueError("Phase 19 source population is incomplete")
    if readiness.get("chronology_replay_authorized") is not True:
        raise ValueError("Phase 19 chronology replay is not authorized")
    if readiness.get("usd_portfolio_replay_authorized") is not False:
        raise ValueError("Phase 19 USD replay must remain fail-closed")
    if readiness.get("cross_trader_r_aggregation_authorized") is not False:
        raise ValueError("Phase 19 cross-Trader R aggregation must remain forbidden")

    common_window = report.get("common_window")
    if not isinstance(common_window, dict):
        raise ValueError("Phase 19 common window missing")
    if common_window.get("fully_observed_intervals_only") is not True:
        raise ValueError("Phase 19 atlas requires fully observed intervals")
    start = datetime.fromisoformat(str(common_window["start"]))
    end = datetime.fromisoformat(str(common_window["end"]))

    total = report.get("cross_trader_overlapping_pairs")
    if type(total) is not int or total <= 0:
        raise ValueError("Phase 19 cross-Trader overlap total invalid")

    pair_counts = report.get("cross_trader_pair_overlap_counts")
    if not isinstance(pair_counts, dict):
        raise ValueError("Phase 19 pair-overlap matrix missing")

    overlaps: list[Phase19TraderPairOverlap] = []
    for index, left in enumerate(PHASE19_REQUIRED_TRADERS):
        for right in PHASE19_REQUIRED_TRADERS[index + 1 :]:
            left_value, right_value = sorted((left.value, right.value))
            key = f"{left_value}|{right_value}"
            raw_count = pair_counts.get(key, 0)
            if type(raw_count) is not int or raw_count < 0:
                raise ValueError(f"Phase 19 pair count invalid: {key}")
            overlaps.append(
                Phase19TraderPairOverlap(
                    left_trader=left,
                    right_trader=right,
                    overlapping_pairs=raw_count,
                )
            )

    report_sha256 = hashlib.sha256(raw).hexdigest()
    atlas = Phase19TemporalOverlapAtlas(
        source_evidence_id=f"sha256:{report_sha256}",
        common_window_start=start,
        common_window_end=end,
        total_cross_trader_overlap_pairs=total,
        pair_overlaps=tuple(overlaps),
    )

    output: dict[str, Any] = {
        "schema": "qore.cibo.phase19.temporal_interaction_atlas.v1",
        "identity": "CIBO_PHASE19_TEMPORAL_INTERACTION_ATLAS_V1",
        "source_report_sha256": report_sha256,
        "common_window": {
            "start": atlas.common_window_start.isoformat(),
            "end": atlas.common_window_end.isoformat(),
        },
        "total_cross_trader_overlap_pairs": (
            atlas.total_cross_trader_overlap_pairs
        ),
        "weight_interpretation": (
            "pair_share_of_all_cross_trader_overlap_pairs_in_common_window"
        ),
        "pair_weights": [
            {
                "left_trader": item.unordered_key[0].value,
                "right_trader": item.unordered_key[1].value,
                "overlapping_pairs": item.overlapping_pairs,
                "temporal_overlap_weight": str(
                    atlas.overlap_share(*item.unordered_key)
                ),
            }
            for item in sorted(
                atlas.pair_overlaps,
                key=lambda overlap: (
                    overlap.unordered_key[0].value,
                    overlap.unordered_key[1].value,
                ),
            )
        ],
        "governance": {
            "research_only": True,
            "observational_only": True,
            "allocator_authority_changed": False,
            "sizing_authority_changed": False,
            "qore_risk_authority_changed": False,
            "execution_authority_changed": False,
            "cross_trader_r_aggregation_performed": False,
            "usd_capital_arithmetic_performed": False,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            build_atlas(
                report_path=args.report,
                output_path=args.output,
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
