"""Pure planning and identity contracts for WP-05 V12 full R8 acquisition."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


FULL_ACQUISITION_IDENTITY = (
    "QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_FULL_R8_ACQUISITION_001"
)
FROZEN_SHARD_COUNT = 8


@dataclass(frozen=True, slots=True)
class V12FullAcquisitionShardPlan:
    shard_index: int
    shard_count: int
    total_windows: int
    start_index: int
    end_index_exclusive: int

    def __post_init__(self) -> None:
        if type(self.shard_count) is not int or self.shard_count <= 0:
            raise ValueError("shard_count must be positive int")
        if type(self.shard_index) is not int or not 0 <= self.shard_index < self.shard_count:
            raise ValueError("shard_index must be within shard_count")
        if type(self.total_windows) is not int or self.total_windows <= 0:
            raise ValueError("total_windows must be positive int")
        if not 0 <= self.start_index < self.end_index_exclusive <= self.total_windows:
            raise ValueError("shard bounds must be non-empty and inside manifest")

    @property
    def window_count(self) -> int:
        return self.end_index_exclusive - self.start_index

    @property
    def manifest_indices(self) -> tuple[int, ...]:
        return tuple(range(self.start_index, self.end_index_exclusive))

    def logical_values(self) -> tuple[int, ...]:
        return (
            self.shard_index,
            self.shard_count,
            self.total_windows,
            self.start_index,
            self.end_index_exclusive,
        )


def plan_v12_full_acquisition_shard(
    *,
    total_windows: int,
    shard_index: int,
    shard_count: int = FROZEN_SHARD_COUNT,
) -> V12FullAcquisitionShardPlan:
    """Partition manifest ordinal space into deterministic contiguous shards."""

    if type(total_windows) is not int or total_windows <= 0:
        raise ValueError("total_windows must be positive int")
    if type(shard_count) is not int or shard_count <= 0:
        raise ValueError("shard_count must be positive int")
    if shard_count > total_windows:
        raise ValueError("shard_count must not exceed total_windows")
    if type(shard_index) is not int or not 0 <= shard_index < shard_count:
        raise ValueError("shard_index must be within shard_count")
    start = total_windows * shard_index // shard_count
    end = total_windows * (shard_index + 1) // shard_count
    return V12FullAcquisitionShardPlan(
        shard_index=shard_index,
        shard_count=shard_count,
        total_windows=total_windows,
        start_index=start,
        end_index_exclusive=end,
    )


def validate_complete_v12_shard_plans(
    plans: tuple[V12FullAcquisitionShardPlan, ...],
) -> None:
    if not plans:
        raise ValueError("full acquisition requires shard plans")
    ordered = tuple(sorted(plans, key=lambda item: item.shard_index))
    shard_count = ordered[0].shard_count
    total_windows = ordered[0].total_windows
    if len(ordered) != shard_count:
        raise ValueError("full acquisition requires every shard exactly once")
    if tuple(item.shard_index for item in ordered) != tuple(range(shard_count)):
        raise ValueError("full acquisition shard indices are incomplete")
    if any(
        item.shard_count != shard_count or item.total_windows != total_windows
        for item in ordered
    ):
        raise ValueError("full acquisition shard plans disagree on universe")
    flattened = tuple(index for item in ordered for index in item.manifest_indices)
    if flattened != tuple(range(total_windows)):
        raise ValueError("full acquisition shard plans overlap or leave gaps")


def global_v12_dataset_digest(
    *,
    manifest_sha256: str,
    ordered_shard_dataset_sha256: tuple[str, ...],
) -> str:
    if len(manifest_sha256) != 64:
        raise ValueError("manifest_sha256 must be SHA-256 hex")
    int(manifest_sha256, 16)
    if len(ordered_shard_dataset_sha256) != FROZEN_SHARD_COUNT:
        raise ValueError("global dataset digest requires exactly 8 shard digests")
    for value in ordered_shard_dataset_sha256:
        if len(value) != 64:
            raise ValueError("shard dataset digest must be SHA-256 hex")
        int(value, 16)
    payload = {
        "identity": FULL_ACQUISITION_IDENTITY,
        "manifest_sha256": manifest_sha256,
        "ordered_shard_dataset_sha256": ordered_shard_dataset_sha256,
        "shard_count": FROZEN_SHARD_COUNT,
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
