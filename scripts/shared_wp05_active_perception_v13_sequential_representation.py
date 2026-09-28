"""Build the source-only WP-05 V13 sequential microstructure trajectory."""

from __future__ import annotations

import argparse
import json
from bisect import bisect_right
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from shared_wp05_active_perception_v12_anchor_observability import (
    _assign_anchors_to_windows,
    _discover_pages,
    _load_anchor_manifest,
    _load_side_events,
)
from shared_wp05_active_perception_v12_microstructure_representation import (
    _load_observability,
    _snapshot,
)

from qore.infrastructure.core_stack_v2.active_perception_v12_microstructure_representation import (
    EXPECTED_GLOBAL_DATASET_SHA256,
    EXPECTED_SOURCE_ANCHOR_SHA256,
    normalize_v12_microstructure_snapshot,
)
from qore.infrastructure.core_stack_v2.active_perception_v13_sequential_representation import (
    EXPECTED_V13_ROW_COUNT,
    V13_BASE_FEATURES,
    V13_CHECKPOINTS_MINUTES,
    V13_MIN_CHECKPOINT_COVERAGE_BPS,
    V13_REPRESENTATION_IDENTITY,
    v13_artifact_fingerprint,
    v13_flat_feature_names,
    v13_representation_contract_fingerprint,
    v13_representation_contract_payload,
    v13_rows_sha256,
)


class V13SequentialRepresentationError(RuntimeError):
    """V13 source-only sequential representation failed closed."""


@dataclass(frozen=True, slots=True)
class _SideSeries:
    times: tuple[datetime, ...]
    prices: tuple[int, ...]
    variation_prefix: tuple[int, ...]


def _series(events: list[tuple[datetime, int, int, int]]) -> _SideSeries:
    times = tuple(item[0] for item in events)
    prices = tuple(item[3] for item in events)
    if not times:
        return _SideSeries(times=(), prices=(), variation_prefix=())
    prefix = [0] * len(prices)
    for index in range(1, len(prices)):
        prefix[index] = prefix[index - 1] + abs(prices[index] - prices[index - 1])
    return _SideSeries(
        times=times,
        prices=prices,
        variation_prefix=tuple(prefix),
    )


def _side_state(
    series: _SideSeries,
    *,
    evaluation_at: datetime,
) -> tuple[int | None, int | None, tuple[tuple[int, int, int], ...]]:
    if not series.times:
        return None, None, tuple((0, 0, 0) for _ in V13_CHECKPOINTS_MINUTES)

    right = bisect_right(series.times, evaluation_at)
    if right <= 0:
        latest_age: int | None = None
        latest_price: int | None = None
    else:
        latest_at = series.times[right - 1]
        latest_age = int((evaluation_at - latest_at).total_seconds() * 1000)
        if latest_age < 0:
            raise V13SequentialRepresentationError(
                "future provider event escaped causal bisect"
            )
        latest_price = series.prices[right - 1]

    from qore.infrastructure.core_stack_v2.active_perception_v12_microstructure_representation import (
        FROZEN_WINDOWS_MS,
    )

    window_values: list[tuple[int, int, int]] = []
    for window_ms in FROZEN_WINDOWS_MS:
        cutoff = evaluation_at - timedelta(milliseconds=window_ms)
        left = bisect_right(series.times, cutoff, 0, right)
        count = right - left
        if count <= 0:
            window_values.append((0, 0, 0))
            continue
        displacement = series.prices[right - 1] - series.prices[left]
        variation = (
            0
            if count == 1
            else series.variation_prefix[right - 1] - series.variation_prefix[left]
        )
        window_values.append((count, variation, displacement))
    return latest_age, latest_price, tuple(window_values)


def _artifact_payload(
    *,
    rows: tuple[dict[str, object], ...],
    usable_counts: tuple[int, ...],
    crossed_counts: tuple[int, ...],
) -> dict[str, object]:
    if len(rows) != EXPECTED_V13_ROW_COUNT:
        raise V13SequentialRepresentationError("V13 row population drift")
    coverage_bps = tuple(
        count * 10_000 // len(rows)
        for count in usable_counts
    )
    status = (
        "source_only_frozen"
        if all(value >= V13_MIN_CHECKPOINT_COVERAGE_BPS for value in coverage_bps)
        else "source_only_rejected"
    )
    rows_sha = v13_rows_sha256(rows)
    contract_fp = v13_representation_contract_fingerprint()
    artifact_fp = v13_artifact_fingerprint(
        contract_fingerprint=contract_fp,
        rows_sha256=rows_sha,
        checkpoint_coverage_bps=coverage_bps,
    )
    return {
        "identity": V13_REPRESENTATION_IDENTITY,
        "status": status,
        "partition": "r8",
        "row_count": len(rows),
        "checkpoints_minutes": list(V13_CHECKPOINTS_MINUTES),
        "base_feature_count": len(V13_BASE_FEATURES),
        "trajectory_feature_count": len(v13_flat_feature_names()),
        "minimum_checkpoint_coverage_bps": V13_MIN_CHECKPOINT_COVERAGE_BPS,
        "checkpoint_usable_pair_count": list(usable_counts),
        "checkpoint_usable_pair_coverage_bps": list(coverage_bps),
        "checkpoint_crossed_causal_quote_count": list(crossed_counts),
        "source_anchor_sha256": EXPECTED_SOURCE_ANCHOR_SHA256,
        "global_dataset_sha256": EXPECTED_GLOBAL_DATASET_SHA256,
        "contract": v13_representation_contract_payload(),
        "contract_fingerprint_sha256": contract_fp,
        "rows_sha256": rows_sha,
        "representation_artifact_fingerprint_sha256": artifact_fp,
        "rows": list(rows),
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "shared_methodology_authority": False,
        "shared_sizing_authority": False,
        "shared_risk_authority": False,
        "shared_order_authority": False,
        "shared_execution_authority": False,
    }


def run(
    *,
    raw_root: Path,
    anchor_manifest_path: Path,
    observability_report_path: Path,
) -> dict[str, object]:
    _load_observability(observability_report_path)
    anchors, anchor_digest = _load_anchor_manifest(anchor_manifest_path)
    if anchor_digest != EXPECTED_SOURCE_ANCHOR_SHA256:
        raise V13SequentialRepresentationError("source anchor digest drift")

    grouped, bounds = _discover_pages(raw_root)
    assigned = _assign_anchors_to_windows(anchors, bounds)
    rows: list[dict[str, object] | None] = [None] * len(anchors)
    usable_counts = [0] * len(V13_CHECKPOINTS_MINUTES)
    crossed_counts = [0] * len(V13_CHECKPOINTS_MINUTES)

    for window_index, window_anchors in sorted(assigned.items()):
        bid_series = _series(
            _load_side_events(grouped.get((window_index, "BID"), []))
        )
        ask_series = _series(
            _load_side_events(grouped.get((window_index, "ASK"), []))
        )
        window_end = bounds[window_index][1]

        for anchor_index, source_at in window_anchors:
            row: dict[str, object] = {
                "source_at": source_at.astimezone(UTC).isoformat(
                    timespec="microseconds"
                ),
            }
            for checkpoint_index, minute in enumerate(V13_CHECKPOINTS_MINUTES):
                evaluation_at = source_at + timedelta(minutes=minute)
                if evaluation_at > window_end:
                    raise V13SequentialRepresentationError(
                        "raw acquisition window does not cover frozen checkpoint"
                    )
                snapshot = _snapshot(
                    evaluation_at=evaluation_at,
                    bid=_side_state(
                        bid_series,
                        evaluation_at=evaluation_at,
                    ),
                    ask=_side_state(
                        ask_series,
                        evaluation_at=evaluation_at,
                    ),
                )
                normalized = normalize_v12_microstructure_snapshot(snapshot)
                if int(normalized["causal_pair_available"]) == 1:
                    usable_counts[checkpoint_index] += 1
                if int(normalized["crossed_causal_quote"]) == 1:
                    crossed_counts[checkpoint_index] += 1
                for field in V13_BASE_FEATURES:
                    row[f"t{minute}_{field}"] = normalized[field]
            rows[anchor_index] = row

    if any(row is None for row in rows):
        raise V13SequentialRepresentationError(
            "not every frozen source anchor produced a V13 trajectory row"
        )
    frozen_rows = tuple(cast(dict[str, object], row) for row in rows)
    source_times = tuple(str(row["source_at"]) for row in frozen_rows)
    if source_times != tuple(sorted(source_times)):
        raise V13SequentialRepresentationError("V13 rows lost chronological order")
    if len(source_times) != len(set(source_times)):
        raise V13SequentialRepresentationError("V13 source timestamps are not unique")

    return _artifact_payload(
        rows=frozen_rows,
        usable_counts=tuple(usable_counts),
        crossed_counts=tuple(crossed_counts),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--anchor-manifest", type=Path, required=True)
    parser.add_argument("--observability-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        raw_root=args.raw_root,
        anchor_manifest_path=args.anchor_manifest,
        observability_report_path=args.observability_report,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "row_count": payload["row_count"],
                "checkpoint_usable_pair_count": payload[
                    "checkpoint_usable_pair_count"
                ],
                "checkpoint_usable_pair_coverage_bps": payload[
                    "checkpoint_usable_pair_coverage_bps"
                ],
                "checkpoint_crossed_causal_quote_count": payload[
                    "checkpoint_crossed_causal_quote_count"
                ],
                "contract_fingerprint_sha256": payload[
                    "contract_fingerprint_sha256"
                ],
                "rows_sha256": payload["rows_sha256"],
                "representation_artifact_fingerprint_sha256": payload[
                    "representation_artifact_fingerprint_sha256"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
