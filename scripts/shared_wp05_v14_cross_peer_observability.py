"""Build the source-only WP-05 V14 cross-peer observability freeze."""

from __future__ import annotations

import argparse
import json
from datetime import timedelta
from pathlib import Path

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

from qore.infrastructure.core_stack_v2.active_perception_v14_observability import (
    V14_CHECKPOINTS_MINUTES,
    V14_EXPECTED_SOURCE_ANCHOR_SHA256,
    V14PeerCheckpointQuoteState,
    summarize_v14_cross_peer_observability,
    v14_observability_digest,
)
from qore.infrastructure.core_stack_v2.active_perception_v14_peer_acquisition import (
    V14PeerFamily,
)


class V14ObservabilityError(RuntimeError):
    """V14 source-only cross-peer observability failed closed."""


def _peer_states(
    *,
    peer: V14PeerFamily,
    raw_root: Path,
    anchors: tuple,
) -> list[V14PeerCheckpointQuoteState]:
    grouped, bounds = _discover_pages(raw_root)
    assigned = _assign_anchors_to_windows(anchors, bounds)
    result: list[V14PeerCheckpointQuoteState | None] = [
        None
    ] * (len(anchors) * len(V14_CHECKPOINTS_MINUTES))

    for window_index, window_anchors in sorted(assigned.items()):
        bid_series = _series(
            _load_side_events(grouped.get((window_index, "BID"), []))
        )
        ask_series = _series(
            _load_side_events(grouped.get((window_index, "ASK"), []))
        )
        window_end = bounds[window_index][1]
        for source_index, source_at in window_anchors:
            for checkpoint_position, minute in enumerate(V14_CHECKPOINTS_MINUTES):
                evaluation_at = source_at + timedelta(minutes=minute)
                if evaluation_at > window_end:
                    raise V14ObservabilityError(
                        "raw peer acquisition does not cover frozen checkpoint"
                    )
                bid_age, bid_price, _ = _side_state(
                    bid_series,
                    evaluation_at=evaluation_at,
                )
                ask_age, ask_price, _ = _side_state(
                    ask_series,
                    evaluation_at=evaluation_at,
                )
                position = source_index * len(V14_CHECKPOINTS_MINUTES) + checkpoint_position
                result[position] = V14PeerCheckpointQuoteState(
                    peer=peer,
                    source_index=source_index,
                    checkpoint_minutes=minute,
                    evaluation_at=evaluation_at,
                    bid_age_ms=bid_age,
                    ask_age_ms=ask_age,
                    bid_relative_price=bid_price,
                    ask_relative_price=ask_price,
                )

    if any(item is None for item in result):
        raise V14ObservabilityError("not every peer/checkpoint state was evaluated")
    return [item for item in result if item is not None]


def run(
    *,
    sp500_raw_root: Path,
    us30_raw_root: Path,
    anchor_manifest_path: Path,
) -> dict[str, object]:
    anchors, anchor_digest = _load_anchor_manifest(anchor_manifest_path)
    if anchor_digest != V14_EXPECTED_SOURCE_ANCHOR_SHA256:
        raise V14ObservabilityError("source anchor digest drift")

    states = tuple(
        _peer_states(
            peer=V14PeerFamily.SP500,
            raw_root=sp500_raw_root,
            anchors=anchors,
        )
        + _peer_states(
            peer=V14PeerFamily.US30,
            raw_root=us30_raw_root,
            anchors=anchors,
        )
    )
    report = summarize_v14_cross_peer_observability(states)
    report["observability_sha256"] = v14_observability_digest(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sp500-raw-root", type=Path, required=True)
    parser.add_argument("--us30-raw-root", type=Path, required=True)
    parser.add_argument("--anchor-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = run(
        sp500_raw_root=args.sp500_raw_root,
        us30_raw_root=args.us30_raw_root,
        anchor_manifest_path=args.anchor_manifest,
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
                "selected_staleness_limit_ms": report[
                    "selected_staleness_limit_ms"
                ],
                "observability_sha256": report["observability_sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
