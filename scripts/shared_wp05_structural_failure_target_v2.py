"""Preregistered WP-05 higher-timeframe structural-failure target V2.

This module builds a corrected historical training/evaluation target from the
same source trajectories used by WP-05, but orients the matured 30-minute
failure label by the higher-timeframe H1/H4/D1 anchor instead of M15.

The module is preregistered pending the target-semantics audit. It does not
activate itself, open fresh evidence, fit a decision model or promote
knowledge.
"""

from __future__ import annotations

from pathlib import Path

from shared_wp03_historical_causal_discovery import _load_bars
from shared_wp05_temporal_hierarchy_absorption_v3 import _prepare_partition

from qore.infrastructure.core_stack_v2.temporal_hierarchy_target_contract import (
    higher_timeframe_anchor_direction,
    higher_timeframe_structural_failure_target,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_transition_v2 import (
    TemporalHierarchyTrajectoryTrainingEpisode,
)


def _source_key(item: TemporalHierarchyTrajectoryTrainingEpisode) -> str:
    return item.trajectory.snapshots[-1].as_of.strftime("%Y-%m-%dT%H:%M:%S")


def relabel_partition_with_structural_failure_v2(
    *,
    partition: str,
    evidence_paths: dict[str, Path],
) -> tuple[
    tuple[TemporalHierarchyTrajectoryTrainingEpisode, ...],
    dict[str, int | str | None],
]:
    """Build V2 targets without changing source trajectories or timestamps."""

    original, partition_range = _prepare_partition(
        partition=partition,
        evidence_paths=evidence_paths,
    )
    nas = _load_bars(evidence_paths["NAS100"])
    index_by_key = {bar.closed_key: index for index, bar in enumerate(nas)}

    corrected: list[TemporalHierarchyTrajectoryTrainingEpisode] = []
    changed = 0
    old_terminal = 0
    new_terminal = 0
    unidentifiable_anchor = 0

    for item in original:
        key = _source_key(item)
        index = index_by_key.get(key)
        if index is None:
            raise ValueError("source snapshot missing from NAS100 evidence")
        if index < 19 or index + 30 >= len(nas):
            raise ValueError("source snapshot lacks target boundary evidence")

        snapshot = item.trajectory.snapshots[-1]
        anchor = higher_timeframe_anchor_direction(snapshot)
        if anchor == 0:
            unidentifiable_anchor += 1

        prior = nas[index - 19 : index + 1]
        future = nas[index + 1 : index + 31]
        if len(prior) != 20 or len(future) != 30:
            raise ValueError("structural target requires 20m prior and 30m future")

        target = higher_timeframe_structural_failure_target(
            anchor_direction=anchor,
            prior_peak=max(bar.high for bar in prior),
            prior_floor=min(bar.low for bar in prior),
            future_high=max(bar.high for bar in future),
            future_low=min(bar.low for bar in future),
            future_final_close=future[-1].close,
        )

        old_terminal += int(item.terminal_failure)
        new_terminal += int(target)
        changed += int(bool(item.terminal_failure) != target)
        corrected.append(
            TemporalHierarchyTrajectoryTrainingEpisode(
                trajectory=item.trajectory,
                observed_at=item.observed_at,
                terminal_failure=target,
            )
        )

    return tuple(corrected), {
        **partition_range,
        "original_terminal_count": old_terminal,
        "v2_terminal_count": new_terminal,
        "changed_target_count": changed,
        "unidentifiable_anchor_count": unidentifiable_anchor,
        "target_contract": "HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2",
        "target_runtime_allowed": 0,
        "fresh_holdout_opened": 0,
    }
