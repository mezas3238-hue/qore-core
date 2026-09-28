from __future__ import annotations

import pytest

from qore.infrastructure.core_stack_v2.active_perception_v12_full_acquisition import (
    FROZEN_SHARD_COUNT,
    global_v12_dataset_digest,
    plan_v12_full_acquisition_shard,
    validate_complete_v12_shard_plans,
)


def test_eight_shards_cover_all_2948_manifest_windows_exactly_once() -> None:
    plans = tuple(
        plan_v12_full_acquisition_shard(
            total_windows=2948,
            shard_index=index,
        )
        for index in range(FROZEN_SHARD_COUNT)
    )

    validate_complete_v12_shard_plans(plans)
    flattened = tuple(index for plan in plans for index in plan.manifest_indices)
    assert flattened == tuple(range(2948))
    assert sum(plan.window_count for plan in plans) == 2948


def test_shard_partition_is_contiguous_and_deterministic() -> None:
    first = plan_v12_full_acquisition_shard(
        total_windows=2948,
        shard_index=3,
    )
    second = plan_v12_full_acquisition_shard(
        total_windows=2948,
        shard_index=3,
    )

    assert first == second
    assert first.start_index == 1105
    assert first.end_index_exclusive == 1474


def test_complete_plan_validation_rejects_missing_shard() -> None:
    plans = tuple(
        plan_v12_full_acquisition_shard(
            total_windows=2948,
            shard_index=index,
        )
        for index in range(FROZEN_SHARD_COUNT - 1)
    )

    with pytest.raises(ValueError, match="every shard"):
        validate_complete_v12_shard_plans(plans)


def test_global_dataset_digest_is_ordered_and_manifest_bound() -> None:
    digests = tuple(f"{index:064x}" for index in range(1, 9))
    first = global_v12_dataset_digest(
        manifest_sha256="a" * 64,
        ordered_shard_dataset_sha256=digests,
    )
    repeated = global_v12_dataset_digest(
        manifest_sha256="a" * 64,
        ordered_shard_dataset_sha256=digests,
    )
    reordered = global_v12_dataset_digest(
        manifest_sha256="a" * 64,
        ordered_shard_dataset_sha256=tuple(reversed(digests)),
    )

    assert first == repeated
    assert first != reordered
