"""Build the frozen source-only WP-05 V12 microstructure representation."""

from __future__ import annotations

import argparse
import hashlib
import json
from bisect import bisect_right
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

from shared_wp05_active_perception_v12_anchor_observability import (
    _assign_anchors_to_windows,
    _discover_pages,
    _load_anchor_manifest,
    _load_side_events,
)

from qore.infrastructure.core_stack_v2.active_perception_v12_anchor_observability import (
    ANCHOR_OBSERVABILITY_IDENTITY,
    v12_anchor_observability_digest,
)
from qore.infrastructure.core_stack_v2.active_perception_v12_microstructure_foundation import (
    V12CausalMicrostructureSnapshot,
    V12MicrostructureAvailability,
    V12MicrostructureWindowStats,
)
from qore.infrastructure.core_stack_v2.active_perception_v12_microstructure_representation import (
    EXPECTED_ANCHOR_OBSERVABILITY_SHA256,
    EXPECTED_GLOBAL_DATASET_SHA256,
    EXPECTED_SOURCE_ANCHOR_SHA256,
    FROZEN_STALENESS_LIMIT_MS,
    FROZEN_WINDOWS_MS,
    REPRESENTATION_IDENTITY,
    normalize_v12_microstructure_snapshot,
    v12_microstructure_candidate_fields,
    v12_microstructure_representation_contract_fingerprint,
    v12_microstructure_representation_contract_payload,
    v12_microstructure_rows_sha256,
)

EXPECTED_ANCHOR_COUNT = 6804


class V12MicrostructureRepresentationError(RuntimeError):
    """Frozen source-only representation construction failed closed."""


def _load_observability(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise V12MicrostructureRepresentationError(
            "anchor observability report must be JSON object"
        )
    payload = cast(dict[str, Any], raw)
    if payload.get("identity") != ANCHOR_OBSERVABILITY_IDENTITY:
        raise V12MicrostructureRepresentationError(
            "anchor observability identity mismatch"
        )
    stored = payload.get("anchor_observability_sha256")
    if stored != EXPECTED_ANCHOR_OBSERVABILITY_SHA256:
        raise V12MicrostructureRepresentationError(
            "anchor observability digest drift"
        )
    digest_payload = dict(payload)
    digest_payload.pop("anchor_observability_sha256", None)
    if v12_anchor_observability_digest(digest_payload) != stored:
        raise V12MicrostructureRepresentationError(
            "anchor observability report failed digest verification"
        )
    if payload.get("status") != "frozen":
        raise V12MicrostructureRepresentationError(
            "anchor observability is not frozen"
        )
    if payload.get("anchor_count") != EXPECTED_ANCHOR_COUNT:
        raise V12MicrostructureRepresentationError(
            "anchor observability population drift"
        )
    if payload.get("selected_staleness_limit_ms") != FROZEN_STALENESS_LIMIT_MS:
        raise V12MicrostructureRepresentationError(
            "frozen staleness limit mismatch"
        )
    if payload.get("microstructure_windows_ms") != list(FROZEN_WINDOWS_MS):
        raise V12MicrostructureRepresentationError(
            "frozen microstructure windows mismatch"
        )
    if payload.get("source_anchor_sha256") != EXPECTED_SOURCE_ANCHOR_SHA256:
        raise V12MicrostructureRepresentationError(
            "source anchor digest mismatch"
        )
    if payload.get("global_dataset_sha256") != EXPECTED_GLOBAL_DATASET_SHA256:
        raise V12MicrostructureRepresentationError(
            "raw dataset digest mismatch"
        )
    for key in (
        "target_or_outcome_read",
        "r6_r5_read",
        "fresh_holdout_opened",
        "shared_methodology_authority",
        "shared_sizing_authority",
        "shared_risk_authority",
        "shared_order_authority",
        "shared_execution_authority",
    ):
        if payload.get(key) is not False:
            raise V12MicrostructureRepresentationError(
                f"forbidden observability state: {key}"
            )
    return payload


def _prefix_variation(prices: list[int]) -> list[int]:
    if not prices:
        return []
    result = [0] * len(prices)
    for index in range(1, len(prices)):
        result[index] = result[index - 1] + abs(prices[index] - prices[index - 1])
    return result


def _side_at_anchor(
    events: list[tuple[datetime, int, int, int]],
    *,
    evaluation_at: datetime,
) -> tuple[int | None, int | None, tuple[tuple[int, int, int], ...]]:
    if not events:
        return None, None, tuple((0, 0, 0) for _ in FROZEN_WINDOWS_MS)
    times = [item[0] for item in events]
    prices = [item[3] for item in events]
    variation_prefix = _prefix_variation(prices)
    right = bisect_right(times, evaluation_at)
    if right <= 0:
        latest_age: int | None = None
        latest_price: int | None = None
    else:
        latest_at = times[right - 1]
        latest_age = int((evaluation_at - latest_at).total_seconds() * 1000)
        if latest_age < 0:
            raise V12MicrostructureRepresentationError(
                "future provider event escaped causal bisect"
            )
        latest_price = prices[right - 1]

    window_values: list[tuple[int, int, int]] = []
    for window_ms in FROZEN_WINDOWS_MS:
        cutoff = evaluation_at - timedelta(milliseconds=window_ms)
        left = bisect_right(times, cutoff, 0, right)
        count = right - left
        if count <= 0:
            window_values.append((0, 0, 0))
            continue
        displacement = prices[right - 1] - prices[left]
        variation = (
            0
            if count == 1
            else variation_prefix[right - 1] - variation_prefix[left]
        )
        window_values.append((count, variation, displacement))
    return latest_age, latest_price, tuple(window_values)


def _imbalance_bps(bid_count: int, ask_count: int) -> int:
    total = bid_count + ask_count
    if total <= 0:
        return 0
    numerator = bid_count - ask_count
    magnitude = abs(numerator) * 10_000 // total
    return magnitude if numerator >= 0 else -magnitude


def _snapshot(
    *,
    evaluation_at: datetime,
    bid: tuple[int | None, int | None, tuple[tuple[int, int, int], ...]],
    ask: tuple[int | None, int | None, tuple[tuple[int, int, int], ...]],
) -> V12CausalMicrostructureSnapshot:
    bid_age, bid_price, bid_windows = bid
    ask_age, ask_price, ask_windows = ask
    if len(bid_windows) != len(FROZEN_WINDOWS_MS) or len(ask_windows) != len(
        FROZEN_WINDOWS_MS
    ):
        raise V12MicrostructureRepresentationError("microstructure window drift")

    both_fresh = (
        bid_age is not None
        and ask_age is not None
        and bid_age <= FROZEN_STALENESS_LIMIT_MS
        and ask_age <= FROZEN_STALENESS_LIMIT_MS
    )
    spread = (
        ask_price - bid_price
        if both_fresh and ask_price is not None and bid_price is not None
        else None
    )
    crossed = None if spread is None else spread < 0
    windows = tuple(
        V12MicrostructureWindowStats(
            window_ms=window_ms,
            bid_update_count=bid_values[0],
            ask_update_count=ask_values[0],
            update_imbalance_bps=_imbalance_bps(
                bid_values[0],
                ask_values[0],
            ),
            bid_path_variation=bid_values[1],
            ask_path_variation=ask_values[1],
            bid_displacement=bid_values[2],
            ask_displacement=ask_values[2],
        )
        for window_ms, bid_values, ask_values in zip(
            FROZEN_WINDOWS_MS,
            bid_windows,
            ask_windows,
            strict=True,
        )
    )
    return V12CausalMicrostructureSnapshot(
        evaluation_at=evaluation_at,
        staleness_limit_ms=FROZEN_STALENESS_LIMIT_MS,
        availability=(
            V12MicrostructureAvailability.AVAILABLE
            if both_fresh
            else V12MicrostructureAvailability.INSUFFICIENT
        ),
        bid_age_ms=bid_age,
        ask_age_ms=ask_age,
        bid_relative_price=bid_price,
        ask_relative_price=ask_price,
        spread_relative_price=spread,
        crossed_quote=crossed,
        side_age_skew_ms=(
            None
            if not both_fresh or bid_age is None or ask_age is None
            else bid_age - ask_age
        ),
        windows=windows,
    )


def _artifact_fingerprint(
    *,
    contract_fingerprint: str,
    rows_sha256: str,
) -> str:
    payload = {
        "identity": REPRESENTATION_IDENTITY,
        "contract_fingerprint_sha256": contract_fingerprint,
        "rows_sha256": rows_sha256,
        "source_anchor_sha256": EXPECTED_SOURCE_ANCHOR_SHA256,
        "anchor_observability_sha256": EXPECTED_ANCHOR_OBSERVABILITY_SHA256,
        "global_dataset_sha256": EXPECTED_GLOBAL_DATASET_SHA256,
        "row_count": EXPECTED_ANCHOR_COUNT,
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def run(
    *,
    raw_root: Path,
    anchor_manifest_path: Path,
    observability_report_path: Path,
) -> dict[str, object]:
    _load_observability(observability_report_path)
    anchors, anchor_digest = _load_anchor_manifest(anchor_manifest_path)
    if anchor_digest != EXPECTED_SOURCE_ANCHOR_SHA256:
        raise V12MicrostructureRepresentationError(
            "source anchor artifact fingerprint drift"
        )

    grouped, bounds = _discover_pages(raw_root)
    assigned = _assign_anchors_to_windows(anchors, bounds)
    rows: list[dict[str, object] | None] = [None] * len(anchors)

    for window_index, window_anchors in sorted(assigned.items()):
        bid_events = _load_side_events(grouped.get((window_index, "BID"), []))
        ask_events = _load_side_events(grouped.get((window_index, "ASK"), []))
        for anchor_index, evaluation_at in window_anchors:
            snapshot = _snapshot(
                evaluation_at=evaluation_at,
                bid=_side_at_anchor(
                    bid_events,
                    evaluation_at=evaluation_at,
                ),
                ask=_side_at_anchor(
                    ask_events,
                    evaluation_at=evaluation_at,
                ),
            )
            rows[anchor_index] = normalize_v12_microstructure_snapshot(snapshot)

    if any(row is None for row in rows):
        raise V12MicrostructureRepresentationError(
            "not every frozen anchor produced a representation row"
        )
    frozen_rows = tuple(cast(dict[str, object], row) for row in rows)
    if len(frozen_rows) != EXPECTED_ANCHOR_COUNT:
        raise V12MicrostructureRepresentationError(
            "representation row population drift"
        )
    times = tuple(str(row["evaluation_at"]) for row in frozen_rows)
    if times != tuple(sorted(times)) or len(times) != len(set(times)):
        raise V12MicrostructureRepresentationError(
            "representation rows lost unique chronological anchor order"
        )

    rows_sha = v12_microstructure_rows_sha256(frozen_rows)
    contract_fingerprint = v12_microstructure_representation_contract_fingerprint()
    artifact_fingerprint = _artifact_fingerprint(
        contract_fingerprint=contract_fingerprint,
        rows_sha256=rows_sha,
    )
    usable_count = sum(
        int(row["causal_pair_available"]) for row in frozen_rows
    )
    crossed_count = sum(int(row["crossed_causal_quote"]) for row in frozen_rows)
    return {
        "identity": REPRESENTATION_IDENTITY,
        "status": "source_only_frozen",
        "partition": "r8",
        "row_count": len(frozen_rows),
        "usable_pair_count": usable_count,
        "usable_pair_coverage_bps": usable_count * 10_000 // len(frozen_rows),
        "insufficient_pair_count": len(frozen_rows) - usable_count,
        "crossed_causal_quote_count": crossed_count,
        "staleness_limit_ms": FROZEN_STALENESS_LIMIT_MS,
        "windows_ms": list(FROZEN_WINDOWS_MS),
        "source_anchor_sha256": EXPECTED_SOURCE_ANCHOR_SHA256,
        "anchor_observability_sha256": EXPECTED_ANCHOR_OBSERVABILITY_SHA256,
        "global_dataset_sha256": EXPECTED_GLOBAL_DATASET_SHA256,
        "contract": v12_microstructure_representation_contract_payload(),
        "contract_fingerprint_sha256": contract_fingerprint,
        "rows_sha256": rows_sha,
        "representation_artifact_fingerprint_sha256": artifact_fingerprint,
        "candidate_fields": {
            name: list(fields)
            for name, fields in v12_microstructure_candidate_fields().items()
        },
        "rows": list(frozen_rows),
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "shared_methodology_authority": False,
        "shared_sizing_authority": False,
        "shared_risk_authority": False,
        "shared_order_authority": False,
        "shared_execution_authority": False,
    }


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
                "usable_pair_count": payload["usable_pair_count"],
                "usable_pair_coverage_bps": payload["usable_pair_coverage_bps"],
                "crossed_causal_quote_count": payload[
                    "crossed_causal_quote_count"
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
