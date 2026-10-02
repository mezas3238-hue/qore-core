from __future__ import annotations

import pytest

from qore.infrastructure.core_stack_v2.active_perception_v14_peer_acquisition import (
    ASSIGNMENT_RULE,
    EXPECTED_MANIFEST_SHA256,
    FROZEN_SHARD_COUNT,
    FROZEN_WINDOW_COUNT,
    V14_PEER_ACQUISITION_IDENTITY,
    V14PeerFamily,
    peer_spec,
    plan_v14_peer_shard,
    reduce_v14_peer_reports,
    v14_peer_assignment_digest,
)


def test_v14_peer_identities_are_frozen_from_source_availability_audit() -> None:
    sp = peer_spec(V14PeerFamily.SP500)
    dow = peer_spec(V14PeerFamily.US30)
    assert (sp.provider_symbol, sp.provider_symbol_id, sp.digits) == (
        "US500",
        10013,
        2,
    )
    assert (dow.provider_symbol, dow.provider_symbol_id, dow.digits) == (
        "US30",
        10015,
        2,
    )


def test_v14_shard_plans_cover_every_manifest_window_once() -> None:
    plans = tuple(
        plan_v14_peer_shard(
            peer=V14PeerFamily.SP500,
            total_windows=FROZEN_WINDOW_COUNT,
            shard_index=index,
        )
        for index in range(FROZEN_SHARD_COUNT)
    )
    flattened = [index for plan in plans for index in plan.manifest_indices]
    assert sorted(flattened) == list(range(FROZEN_WINDOW_COUNT))
    assert len(flattened) == len(set(flattened))


def _report(peer: V14PeerFamily, shard: int) -> dict[str, object]:
    spec = peer_spec(peer)
    plan = plan_v14_peer_shard(
        peer=peer,
        total_windows=FROZEN_WINDOW_COUNT,
        shard_index=shard,
    )
    windows = [
        {
            "manifest_index": index,
            "bid_count": 1,
            "ask_count": 1,
        }
        for index in plan.manifest_indices
    ]
    return {
        "identity": V14_PEER_ACQUISITION_IDENTITY,
        "partition": "r8_source_only",
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "peer_family": peer.value,
        "provider_symbol": spec.provider_symbol,
        "provider_symbol_id": spec.provider_symbol_id,
        "provider_digits": spec.digits,
        "shard_index": shard,
        "shard_count": FROZEN_SHARD_COUNT,
        "assignment_rule": ASSIGNMENT_RULE,
        "assignment_sha256": v14_peer_assignment_digest(plan=plan),
        "attempted_manifest_indices": list(plan.manifest_indices),
        "window_reports": windows,
        "read_only_message_firewall": True,
        "bid_tick_count": len(windows),
        "ask_tick_count": len(windows),
        "provider_page_count": len(windows) * 2,
        "immutable_page_shard_count": len(windows) * 2,
        "empty_bid_window_count": 0,
        "empty_ask_window_count": 0,
        "shard_dataset_sha256": f"{shard + 1:064x}",
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


@pytest.mark.parametrize("peer", list(V14PeerFamily))
def test_v14_peer_reduction_proves_exact_source_population(
    peer: V14PeerFamily,
) -> None:
    reports = tuple(_report(peer, shard) for shard in range(FROZEN_SHARD_COUNT))
    reduced = reduce_v14_peer_reports(reports, peer=peer)
    assert reduced["status"] == "source_only_complete"
    assert reduced["window_count"] == FROZEN_WINDOW_COUNT
    assert reduced["full_bid_ask_window_coverage"] is True
    assert reduced["target_or_outcome_read"] is False
    assert reduced["r6_r5_read"] is False
    assert reduced["fresh_holdout_opened"] is False
    assert reduced["scientific_v14_outcomes_opened"] is False


def test_v14_peer_reduction_fails_on_provider_identity_drift() -> None:
    reports = [_report(V14PeerFamily.SP500, shard) for shard in range(FROZEN_SHARD_COUNT)]
    reports[0]["provider_symbol_id"] = 999
    with pytest.raises(ValueError, match="symbol id drift"):
        reduce_v14_peer_reports(tuple(reports), peer=V14PeerFamily.SP500)
