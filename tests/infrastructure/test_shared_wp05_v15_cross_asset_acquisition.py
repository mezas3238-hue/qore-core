from __future__ import annotations

from qore.infrastructure.core_stack_v2.active_perception_v15_cross_asset_acquisition import (
    EXPECTED_MANIFEST_SHA256,
    FROZEN_SHARD_COUNT,
    FROZEN_WINDOW_COUNT,
    V15CrossAssetFamily,
    cross_asset_spec,
    plan_v15_cross_asset_shard,
    reduce_v15_cross_asset_reports,
    v15_assignment_digest,
)


def _report(
    *,
    family: V15CrossAssetFamily,
    shard: int,
    digits: int,
) -> dict[str, object]:
    spec = cross_asset_spec(family)
    plan = plan_v15_cross_asset_shard(
        family=family,
        total_windows=FROZEN_WINDOW_COUNT,
        shard_index=shard,
    )
    return {
        "identity": "QORE_SHARED_WP05_V15_CROSS_ASSET_R8_ACQUISITION_001",
        "partition": "r8_source_only",
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "family": family.value,
        "semantic_role": spec.semantic_role,
        "provider_symbol": spec.provider_symbol,
        "provider_symbol_id": spec.provider_symbol_id,
        "provider_digits": digits,
        "canonical_instrument": spec.canonical_instrument,
        "shard_index": shard,
        "shard_count": FROZEN_SHARD_COUNT,
        "total_manifest_windows": FROZEN_WINDOW_COUNT,
        "assignment_rule": "MANIFEST_INDEX_MOD_16",
        "assignment_sha256": v15_assignment_digest(
            plan=plan,
            manifest_sha256=EXPECTED_MANIFEST_SHA256,
        ),
        "attempted_manifest_indices": list(plan.manifest_indices),
        "read_only_message_firewall": True,
        "bid_tick_count": len(plan.manifest_indices),
        "ask_tick_count": len(plan.manifest_indices),
        "provider_page_count": len(plan.manifest_indices) * 2,
        "immutable_page_shard_count": len(plan.manifest_indices) * 2,
        "empty_bid_window_count": 0,
        "empty_ask_window_count": 0,
        "shard_dataset_sha256": ("%064x" % (shard + 1)),
        "window_reports": [
            {"manifest_index": index}
            for index in plan.manifest_indices
        ],
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "scientific_v15_outcomes_opened": False,
        "shared_methodology_authority": False,
        "shared_sizing_authority": False,
        "shared_risk_authority": False,
        "shared_order_authority": False,
        "shared_execution_authority": False,
    }


def test_v15_specs_match_frozen_post_v14_provider_ids() -> None:
    us2000 = cross_asset_spec(V15CrossAssetFamily.US2000_BREADTH)
    xau = cross_asset_spec(V15CrossAssetFamily.XAUUSD_DEFENSIVE)

    assert us2000.provider_symbol == "US2000"
    assert us2000.provider_symbol_id == 10012
    assert us2000.semantic_role == "EQUITY_BREADTH_PROXY"

    assert xau.provider_symbol == "XAUUSD"
    assert xau.provider_symbol_id == 41
    assert xau.semantic_role == "DEFENSIVE_ASSET_PROXY"


def test_v15_shards_cover_exact_manifest_once() -> None:
    all_indices: list[int] = []
    for shard in range(FROZEN_SHARD_COUNT):
        plan = plan_v15_cross_asset_shard(
            family=V15CrossAssetFamily.US2000_BREADTH,
            total_windows=FROZEN_WINDOW_COUNT,
            shard_index=shard,
        )
        all_indices.extend(plan.manifest_indices)

    assert len(all_indices) == FROZEN_WINDOW_COUNT
    assert len(set(all_indices)) == FROZEN_WINDOW_COUNT
    assert sorted(all_indices) == list(range(FROZEN_WINDOW_COUNT))


def test_v15_reducer_requires_all_shards_and_consistent_provider_digits() -> None:
    reports = tuple(
        _report(
            family=V15CrossAssetFamily.XAUUSD_DEFENSIVE,
            shard=shard,
            digits=2,
        )
        for shard in range(FROZEN_SHARD_COUNT)
    )
    reduced = reduce_v15_cross_asset_reports(
        reports,
        family=V15CrossAssetFamily.XAUUSD_DEFENSIVE,
    )

    assert reduced["status"] == "source_only_complete"
    assert reduced["window_count"] == FROZEN_WINDOW_COUNT
    assert reduced["provider_digits"] == 2
    assert reduced["full_bid_ask_window_coverage"] is True
    assert reduced["target_or_outcome_read"] is False
    assert reduced["r6_r5_read"] is False
    assert reduced["fresh_holdout_opened"] is False
    assert reduced["scientific_v15_outcomes_opened"] is False
