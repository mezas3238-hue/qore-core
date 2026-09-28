from __future__ import annotations

import pytest

from qore.infrastructure.core_stack_v2.active_perception_v12_full_acquisition import (
    ASSIGNMENT_RULE,
    FROZEN_SHARD_COUNT,
    FULL_ACQUISITION_IDENTITY,
    global_v12_dataset_digest,
    plan_v12_full_acquisition_shard,
    reduce_v12_full_acquisition_reports,
    v12_full_acquisition_assignment_digest,
    validate_complete_v12_shard_plans,
)


def test_sixteen_modulo_shards_cover_all_2948_windows_exactly_once() -> None:
    plans = tuple(
        plan_v12_full_acquisition_shard(
            total_windows=2948,
            shard_index=index,
        )
        for index in range(FROZEN_SHARD_COUNT)
    )

    validate_complete_v12_shard_plans(plans)
    flattened = tuple(index for plan in plans for index in plan.manifest_indices)
    assert tuple(sorted(flattened)) == tuple(range(2948))
    assert len(flattened) == len(set(flattened)) == 2948
    assert sum(plan.window_count for plan in plans) == 2948
    assert all(
        all(index % FROZEN_SHARD_COUNT == plan.shard_index for index in plan.manifest_indices)
        for plan in plans
    )


def test_shard_partition_is_modulo_and_deterministic() -> None:
    first = plan_v12_full_acquisition_shard(
        total_windows=2948,
        shard_index=3,
    )
    repeated = plan_v12_full_acquisition_shard(
        total_windows=2948,
        shard_index=3,
    )

    assert first == repeated
    assert first.manifest_indices[:4] == (3, 19, 35, 51)
    assert first.manifest_indices[-1] == 2947
    assert first.window_count == 185


def test_assignment_digest_is_manifest_and_shard_bound() -> None:
    plan = plan_v12_full_acquisition_shard(
        total_windows=2948,
        shard_index=3,
    )
    other = plan_v12_full_acquisition_shard(
        total_windows=2948,
        shard_index=4,
    )

    first = v12_full_acquisition_assignment_digest(
        manifest_sha256="a" * 64,
        plan=plan,
    )
    repeated = v12_full_acquisition_assignment_digest(
        manifest_sha256="a" * 64,
        plan=plan,
    )
    changed = v12_full_acquisition_assignment_digest(
        manifest_sha256="a" * 64,
        plan=other,
    )

    assert first == repeated
    assert first != changed


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
    digests = tuple(f"{index:064x}" for index in range(1, 17))
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


def _report(shard_index: int, *, total_windows: int = 32) -> dict[str, object]:
    plan = plan_v12_full_acquisition_shard(
        total_windows=total_windows,
        shard_index=shard_index,
    )
    indices = list(plan.manifest_indices)
    window_reports = [
        {
            "manifest_index": index,
            "bid_count": 10,
            "ask_count": 11,
            "bid_page_count": 1,
            "ask_page_count": 1,
        }
        for index in indices
    ]
    return {
        "identity": FULL_ACQUISITION_IDENTITY,
        "partition": "r8",
        "manifest_sha256": "a" * 64,
        "shard_index": shard_index,
        "shard_count": FROZEN_SHARD_COUNT,
        "total_manifest_windows": total_windows,
        "assignment_rule": ASSIGNMENT_RULE,
        "assignment_sha256": v12_full_acquisition_assignment_digest(
            manifest_sha256="a" * 64,
            plan=plan,
        ),
        "attempted_manifest_indices": indices,
        "read_only_message_firewall": True,
        "full_bid_ask_coverage": True,
        "window_reports": window_reports,
        "bid_tick_count": 10 * len(indices),
        "ask_tick_count": 11 * len(indices),
        "provider_page_count": 2 * len(indices),
        "immutable_page_shard_count": 2 * len(indices),
        "shard_dataset_sha256": f"{shard_index + 1:064x}",
        "target_or_outcome_used_for_selection": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "shared_methodology_authority": False,
        "shared_sizing_authority": False,
        "shared_risk_authority": False,
        "shared_order_authority": False,
        "shared_execution_authority": False,
    }


def test_reducer_proves_exact_full_population_before_complete() -> None:
    reports = tuple(_report(index) for index in range(FROZEN_SHARD_COUNT))

    reduced = reduce_v12_full_acquisition_reports(
        reports,
        expected_manifest_sha256="a" * 64,
        expected_window_count=32,
    )

    assert reduced["status"] == "complete"
    assert reduced["window_count"] == 32
    assert reduced["bid_tick_count"] == 320
    assert reduced["ask_tick_count"] == 352
    assert len(str(reduced["global_dataset_sha256"])) == 64


def test_reducer_rejects_wrong_shard_ownership() -> None:
    reports = [_report(index) for index in range(FROZEN_SHARD_COUNT)]
    broken = dict(reports[3])
    broken["attempted_manifest_indices"] = [4, 19]
    broken["window_reports"] = [
        {
            "manifest_index": 4,
            "bid_count": 10,
            "ask_count": 10,
            "bid_page_count": 1,
            "ask_page_count": 1,
        },
        {
            "manifest_index": 19,
            "bid_count": 10,
            "ask_count": 10,
            "bid_page_count": 1,
            "ask_page_count": 1,
        },
    ]
    reports[3] = broken

    with pytest.raises(ValueError, match="wrong shard"):
        reduce_v12_full_acquisition_reports(
            tuple(reports),
            expected_manifest_sha256="a" * 64,
            expected_window_count=32,
        )
