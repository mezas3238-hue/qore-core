"""Build the WP-05 V12 R8 tick acquisition manifest without target labels.

The source population is reconstructed only from causal pre-source OHLC state:
the frozen 30-minute grid, source-aligned NAS100/SP500/US30 evidence, the
pre-existing hierarchy trajectory, local-vs-higher opposition, identifiable
higher-timeframe anchor, and complete V7 source evidence.

No matured terminal label, +30m structural-failure future, R6/R5 or fresh
holdout is read to select tick windows.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from shared_wp03_historical_causal_discovery import (
    MARKETS,
    SAMPLE_MINUTES,
    _load_bars,
    _parse_key,
)
from shared_wp05_temporal_hierarchy_absorption_v3 import (
    MAX_SEQUENCE_LOOKBACK,
    TRAJECTORY_OFFSETS_MINUTES,
)
from shared_wp05_temporal_hierarchy_v1 import (
    MAX_LOOKBACK,
    SCALE_HORIZONS,
    _scale_state,
)

from qore.infrastructure.core_stack_v2.active_perception_v12_acquisition_manifest import (
    build_v12_tick_acquisition_manifest,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_competing_survival_features_v7 import (
    build_competing_survival_source_state,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_engine import (
    TemporalHierarchySnapshot,
    baseline_local_opposition,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_target_contract import (
    higher_timeframe_anchor_direction,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_transition_v2 import (
    TemporalHierarchyTrajectory,
)

IDENTITY = "QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_ACQUISITION_MANIFEST_001"
SCHEMA = "qore.shared.wp05.active_perception.v12.acquisition_manifest.v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _causal_source_times(
    *,
    evidence_paths: dict[str, Path],
) -> tuple[datetime, ...]:
    bars = {market: _load_bars(evidence_paths[market]) for market in MARKETS}
    peer_indexes = {
        market: {bar.closed_key: index for index, bar in enumerate(bars[market])}
        for market in ("SP500", "US30")
    }
    nas = bars["NAS100"]
    sources: list[datetime] = []

    for nas_index in range(MAX_SEQUENCE_LOOKBACK, len(nas)):
        key = nas[nas_index].closed_key
        if int(key[14:16]) not in SAMPLE_MINUTES:
            continue

        indexes = {"NAS100": nas_index}
        missing = False
        for market in ("SP500", "US30"):
            peer_index = peer_indexes[market].get(key)
            if peer_index is None:
                missing = True
                break
            indexes[market] = peer_index
        if missing:
            continue

        snapshots: list[TemporalHierarchySnapshot] = []
        snapshot_times = []
        valid = True
        for offset in TRAJECTORY_OFFSETS_MINUTES:
            windows: dict[str, tuple[Any, ...]] = {}
            for market in MARKETS:
                end_index = indexes[market] - offset
                if end_index < MAX_LOOKBACK - 1:
                    valid = False
                    break
                rows = tuple(
                    bars[market][
                        end_index - MAX_LOOKBACK + 1 : end_index + 1
                    ]
                )
                if len(rows) != MAX_LOOKBACK:
                    valid = False
                    break
                windows[market] = rows
            if not valid:
                break

            source_at = _parse_key(windows["NAS100"][-1].closed_key)
            levels = tuple(
                _scale_state(
                    scale=scale,
                    horizon=horizon,
                    windows=windows,
                )
                for scale, horizon in SCALE_HORIZONS
            )
            snapshots.append(
                TemporalHierarchySnapshot(
                    episode_id=f"r8:{source_at.isoformat()}:state",
                    as_of=source_at,
                    levels=levels,
                )
            )
            snapshot_times.append(source_at)

        if not valid or len(snapshots) != len(TRAJECTORY_OFFSETS_MINUTES):
            continue

        gaps = [
            (right - left).total_seconds() / 60.0
            for left, right in zip(
                snapshot_times,
                snapshot_times[1:],
                strict=False,
            )
        ]
        expected_gaps = [
            left - right
            for left, right in zip(
                TRAJECTORY_OFFSETS_MINUTES,
                TRAJECTORY_OFFSETS_MINUTES[1:],
                strict=False,
            )
        ]
        if any(
            gap < max(5, expected - 5) or gap > expected + 10
            for gap, expected in zip(gaps, expected_gaps, strict=True)
        ):
            continue

        current = snapshots[-1]
        if not baseline_local_opposition(current):
            continue
        anchor = higher_timeframe_anchor_direction(current)
        if anchor == 0:
            continue

        trajectory = TemporalHierarchyTrajectory(
            episode_id=f"r8:{current.as_of.isoformat()}",
            snapshots=tuple(snapshots),
        )
        source = build_competing_survival_source_state(
            trajectory=trajectory,
            anchor_direction=anchor,
            nas_bars=bars["NAS100"],
            nas_index=indexes["NAS100"],
            sp500_bars=bars["SP500"],
            sp500_index=indexes["SP500"],
            us30_bars=bars["US30"],
            us30_index=indexes["US30"],
        )
        if not source.evidence_complete:
            continue
        sources.append(current.as_of)

    del bars
    del peer_indexes
    gc.collect()
    return tuple(sources)


def run(
    *,
    evidence_paths: dict[str, Path],
    provider_symbol: str,
) -> dict[str, object]:
    sources = _causal_source_times(evidence_paths=evidence_paths)
    evidence_sha256 = {
        market: _sha256(path)
        for market, path in evidence_paths.items()
    }
    manifest = build_v12_tick_acquisition_manifest(
        source_times=sources,
        provider_symbol=provider_symbol,
        evidence_sha256=evidence_sha256,
    )
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        **manifest.logical_payload(),
        "manifest_sha256": manifest.digest_sha256,
        "selection_contract": "CAUSAL_SOURCE_ONLY_NO_MATURED_TARGET",
        "r8_only": True,
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
    parser.add_argument("--r8-nas", type=Path, required=True)
    parser.add_argument("--r8-sp", type=Path, required=True)
    parser.add_argument("--r8-us", type=Path, required=True)
    parser.add_argument("--provider-symbol", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        evidence_paths={
            "NAS100": args.r8_nas,
            "SP500": args.r8_sp,
            "US30": args.r8_us,
        },
        provider_symbol=args.provider_symbol,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "source_count": payload["source_count"],
                "window_count": len(payload["windows"]),
                "source_min": payload["source_min"],
                "source_max": payload["source_max"],
                "manifest_sha256": payload["manifest_sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
