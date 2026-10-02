"""Build the frozen source-only WP-05 V14 peer M3 representation."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from shared_wp05_active_perception_v12_anchor_observability import (
    _assign_anchors_to_windows,
    _discover_pages,
    _load_anchor_manifest,
    _load_side_events,
)
from shared_wp05_active_perception_v13_sequential_representation import (
    _series,
    _side_state,
)

from qore.infrastructure.core_stack_v2.active_perception_v12_microstructure_foundation import (
    V12CausalMicrostructureSnapshot,
    V12MicrostructureAvailability,
    V12MicrostructureWindowStats,
)
from qore.infrastructure.core_stack_v2.active_perception_v12_microstructure_representation import (
    FROZEN_WINDOWS_MS,
)
from qore.infrastructure.core_stack_v2.active_perception_v14_observability import (
    V14_CHECKPOINTS_MINUTES,
    V14_EXPECTED_SOURCE_ANCHOR_SHA256,
    V14_EXPECTED_SOURCE_COUNT,
    V14_MIN_PEER_CHECKPOINT_COVERAGE_BPS,
    V14_OBSERVABILITY_IDENTITY,
    v14_observability_digest,
)
from qore.infrastructure.core_stack_v2.active_perception_v14_peer_acquisition import (
    V14PeerFamily,
)
from qore.infrastructure.core_stack_v2.active_perception_v14_representation import (
    V14_BASE_FEATURES,
    V14_REPRESENTATION_IDENTITY,
    normalize_v14_peer_snapshot,
    v14_representation_artifact_fingerprint,
    v14_representation_contract_fingerprint,
    v14_representation_contract_payload,
    v14_rows_sha256,
)
from qore.infrastructure.core_stack_v2.active_perception_v14_source_integrity import (
    V14_SOURCE_INTEGRITY_IDENTITY,
)


class V14RepresentationError(RuntimeError):
    """V14 source-only representation construction failed closed."""


def _load_observability(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise V14RepresentationError("V14 observability report must be object")
    payload = cast(dict[str, Any], raw)
    if payload.get("identity") != V14_OBSERVABILITY_IDENTITY:
        raise V14RepresentationError("V14 observability identity mismatch")
    stored = payload.get("observability_sha256")
    if not isinstance(stored, str) or len(stored) != 64:
        raise V14RepresentationError("V14 observability SHA missing")
    digest_payload = dict(payload)
    digest_payload.pop("observability_sha256", None)
    if v14_observability_digest(digest_payload) != stored:
        raise V14RepresentationError("V14 observability SHA verification failed")
    if payload.get("status") != "source_only_frozen":
        raise V14RepresentationError("V14 observability did not freeze")
    if payload.get("source_count") != V14_EXPECTED_SOURCE_COUNT:
        raise V14RepresentationError("V14 observability source count drift")
    if payload.get("source_anchor_sha256") != V14_EXPECTED_SOURCE_ANCHOR_SHA256:
        raise V14RepresentationError("V14 observability anchor digest drift")
    selected = payload.get("selected_staleness_limit_ms")
    if type(selected) is not int:
        raise V14RepresentationError("V14 observability omitted frozen staleness")
    for key in (
        "target_or_outcome_read",
        "r6_r5_read",
        "fresh_holdout_opened",
        "scientific_v14_outcomes_opened",
        "shared_methodology_authority",
        "shared_sizing_authority",
        "shared_risk_authority",
        "shared_order_authority",
        "shared_execution_authority",
    ):
        if payload.get(key) is not False:
            raise V14RepresentationError(f"forbidden observability state: {key}")
    return payload


def _load_integrity(path: Path, *, peer: V14PeerFamily) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise V14RepresentationError("V14 integrity report must be object")
    payload = cast(dict[str, Any], raw)
    if payload.get("identity") != V14_SOURCE_INTEGRITY_IDENTITY:
        raise V14RepresentationError("V14 integrity identity mismatch")
    if payload.get("status") != "green_source_integrity":
        raise V14RepresentationError("V14 integrity did not pass")
    if payload.get("peer_family") != peer.value:
        raise V14RepresentationError("V14 integrity peer mismatch")
    for key in (
        "target_or_outcome_read",
        "r6_r5_read",
        "fresh_holdout_opened",
        "scientific_v14_outcomes_opened",
        "shared_methodology_authority",
        "shared_sizing_authority",
        "shared_risk_authority",
        "shared_order_authority",
        "shared_execution_authority",
    ):
        if payload.get(key) is not False:
            raise V14RepresentationError(f"forbidden integrity state: {key}")
    digest = payload.get("global_dataset_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise V14RepresentationError("V14 integrity dataset SHA missing")
    return payload


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
    selected_staleness_limit_ms: int,
    bid: tuple[int | None, int | None, tuple[tuple[int, int, int], ...]],
    ask: tuple[int | None, int | None, tuple[tuple[int, int, int], ...]],
) -> V12CausalMicrostructureSnapshot:
    bid_age, bid_price, bid_windows = bid
    ask_age, ask_price, ask_windows = ask
    if len(bid_windows) != len(FROZEN_WINDOWS_MS) or len(ask_windows) != len(
        FROZEN_WINDOWS_MS
    ):
        raise V14RepresentationError("V14 microstructure window drift")
    both_fresh = (
        bid_age is not None
        and ask_age is not None
        and bid_age <= selected_staleness_limit_ms
        and ask_age <= selected_staleness_limit_ms
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
        staleness_limit_ms=selected_staleness_limit_ms,
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


def _fill_peer(
    *,
    peer: V14PeerFamily,
    raw_root: Path,
    anchors: tuple[datetime, ...],
    selected_staleness_limit_ms: int,
    rows: list[dict[str, object]],
    usable_counts: dict[str, list[int]],
    crossed_counts: dict[str, list[int]],
) -> None:
    grouped, bounds = _discover_pages(raw_root)
    assigned = _assign_anchors_to_windows(anchors, bounds)
    for window_index, window_anchors in sorted(assigned.items()):
        bid_series = _series(
            _load_side_events(grouped.get((window_index, "BID"), []))
        )
        ask_series = _series(
            _load_side_events(grouped.get((window_index, "ASK"), []))
        )
        window_end = bounds[window_index][1]
        for source_index, source_at in window_anchors:
            for checkpoint_index, minute in enumerate(V14_CHECKPOINTS_MINUTES):
                evaluation_at = source_at + timedelta(minutes=minute)
                if evaluation_at > window_end:
                    raise V14RepresentationError(
                        "V14 acquisition does not cover frozen checkpoint"
                    )
                snapshot = _snapshot(
                    evaluation_at=evaluation_at,
                    selected_staleness_limit_ms=selected_staleness_limit_ms,
                    bid=_side_state(bid_series, evaluation_at=evaluation_at),
                    ask=_side_state(ask_series, evaluation_at=evaluation_at),
                )
                normalized = normalize_v14_peer_snapshot(
                    snapshot,
                    selected_staleness_limit_ms=selected_staleness_limit_ms,
                )
                if normalized["causal_pair_available"] == 1:
                    usable_counts[peer.value][checkpoint_index] += 1
                if normalized["crossed_causal_quote"] == 1:
                    crossed_counts[peer.value][checkpoint_index] += 1
                prefix = f"{peer.value.lower()}_t{minute}_"
                for field in V14_BASE_FEATURES:
                    rows[source_index][prefix + field] = normalized[field]


def run(
    *,
    sp500_raw_root: Path,
    us30_raw_root: Path,
    anchor_manifest_path: Path,
    observability_report_path: Path,
    sp500_integrity_path: Path,
    us30_integrity_path: Path,
) -> dict[str, object]:
    observability = _load_observability(observability_report_path)
    selected = cast(int, observability["selected_staleness_limit_ms"])
    sp500_integrity = _load_integrity(
        sp500_integrity_path,
        peer=V14PeerFamily.SP500,
    )
    us30_integrity = _load_integrity(
        us30_integrity_path,
        peer=V14PeerFamily.US30,
    )
    anchors, anchor_digest = _load_anchor_manifest(anchor_manifest_path)
    if anchor_digest != V14_EXPECTED_SOURCE_ANCHOR_SHA256:
        raise V14RepresentationError("V14 source anchor digest drift")

    rows: list[dict[str, object]] = [
        {
            "source_at": source_at.astimezone(UTC).isoformat(
                timespec="microseconds"
            )
        }
        for source_at in anchors
    ]
    usable_counts = {
        peer.value: [0] * len(V14_CHECKPOINTS_MINUTES)
        for peer in V14PeerFamily
    }
    crossed_counts = {
        peer.value: [0] * len(V14_CHECKPOINTS_MINUTES)
        for peer in V14PeerFamily
    }

    _fill_peer(
        peer=V14PeerFamily.SP500,
        raw_root=sp500_raw_root,
        anchors=anchors,
        selected_staleness_limit_ms=selected,
        rows=rows,
        usable_counts=usable_counts,
        crossed_counts=crossed_counts,
    )
    _fill_peer(
        peer=V14PeerFamily.US30,
        raw_root=us30_raw_root,
        anchors=anchors,
        selected_staleness_limit_ms=selected,
        rows=rows,
        usable_counts=usable_counts,
        crossed_counts=crossed_counts,
    )

    if len(rows) != V14_EXPECTED_SOURCE_COUNT:
        raise V14RepresentationError("V14 row population drift")
    expected_width = 1 + len(V14PeerFamily) * len(V14_CHECKPOINTS_MINUTES) * len(
        V14_BASE_FEATURES
    )
    if any(len(row) != expected_width for row in rows):
        raise V14RepresentationError("V14 row feature width drift")
    source_times = tuple(str(row["source_at"]) for row in rows)
    if source_times != tuple(sorted(source_times)) or len(source_times) != len(
        set(source_times)
    ):
        raise V14RepresentationError("V14 source rows lost unique chronology")

    coverage_bps = {
        peer.value: [
            count * 10_000 // V14_EXPECTED_SOURCE_COUNT
            for count in usable_counts[peer.value]
        ]
        for peer in V14PeerFamily
    }
    if any(
        value < V14_MIN_PEER_CHECKPOINT_COVERAGE_BPS
        for values in coverage_bps.values()
        for value in values
    ):
        raise V14RepresentationError(
            "V14 representation violates frozen peer/checkpoint coverage gate"
        )

    peer_dataset_sha = {
        V14PeerFamily.SP500.value: cast(
            str,
            sp500_integrity["global_dataset_sha256"],
        ),
        V14PeerFamily.US30.value: cast(
            str,
            us30_integrity["global_dataset_sha256"],
        ),
    }
    observability_sha = cast(str, observability["observability_sha256"])
    contract = v14_representation_contract_payload(
        selected_staleness_limit_ms=selected,
        observability_sha256=observability_sha,
        peer_dataset_sha256=peer_dataset_sha,
    )
    contract_fp = v14_representation_contract_fingerprint(contract)
    frozen_rows = tuple(rows)
    rows_sha = v14_rows_sha256(frozen_rows)
    artifact_fp = v14_representation_artifact_fingerprint(
        contract_fingerprint=contract_fp,
        rows_sha256=rows_sha,
        coverage_bps=coverage_bps,
    )
    return {
        "identity": V14_REPRESENTATION_IDENTITY,
        "status": "source_only_frozen",
        "partition": "r8_source_only",
        "row_count": len(rows),
        "peer_families": [peer.value for peer in V14PeerFamily],
        "checkpoints_minutes": list(V14_CHECKPOINTS_MINUTES),
        "base_feature_count": len(V14_BASE_FEATURES),
        "raw_feature_cell_count": (
            len(V14PeerFamily)
            * len(V14_CHECKPOINTS_MINUTES)
            * len(V14_BASE_FEATURES)
        ),
        "selected_staleness_limit_ms": selected,
        "peer_checkpoint_usable_count": usable_counts,
        "peer_checkpoint_coverage_bps": coverage_bps,
        "peer_checkpoint_crossed_count": crossed_counts,
        "source_anchor_sha256": V14_EXPECTED_SOURCE_ANCHOR_SHA256,
        "observability_sha256": observability_sha,
        "peer_dataset_sha256": peer_dataset_sha,
        "contract": contract,
        "contract_fingerprint_sha256": contract_fp,
        "rows_sha256": rows_sha,
        "representation_artifact_fingerprint_sha256": artifact_fp,
        "rows": rows,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "scientific_v14_outcomes_opened": False,
        "shared_methodology_authority": False,
        "shared_sizing_authority": False,
        "shared_risk_authority": False,
        "shared_order_authority": False,
        "shared_execution_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sp500-raw-root", type=Path, required=True)
    parser.add_argument("--us30-raw-root", type=Path, required=True)
    parser.add_argument("--anchor-manifest", type=Path, required=True)
    parser.add_argument("--observability-report", type=Path, required=True)
    parser.add_argument("--sp500-integrity", type=Path, required=True)
    parser.add_argument("--us30-integrity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        sp500_raw_root=args.sp500_raw_root,
        us30_raw_root=args.us30_raw_root,
        anchor_manifest_path=args.anchor_manifest,
        observability_report_path=args.observability_report,
        sp500_integrity_path=args.sp500_integrity,
        us30_integrity_path=args.us30_integrity,
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
                "selected_staleness_limit_ms": payload[
                    "selected_staleness_limit_ms"
                ],
                "peer_checkpoint_coverage_bps": payload[
                    "peer_checkpoint_coverage_bps"
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
