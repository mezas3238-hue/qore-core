"""Source-only full acquisition contracts for WP-05 V14 peer microstructure."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, cast

V14_PEER_ACQUISITION_IDENTITY: Final = (
    "QORE_SHARED_WP05_V14_PEER_MICROSTRUCTURE_R8_ACQUISITION_001"
)
FROZEN_SHARD_COUNT: Final = 16
FROZEN_WINDOW_COUNT: Final = 2948
ASSIGNMENT_RULE: Final = "MANIFEST_INDEX_MOD_16"
EXPECTED_MANIFEST_SHA256: Final = (
    "2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191"
)


class V14PeerFamily(StrEnum):
    SP500 = "SP500_PEER"
    US30 = "US30_PEER"


@dataclass(frozen=True, slots=True)
class V14PeerSpec:
    family: V14PeerFamily
    provider_symbol: str
    provider_symbol_id: int
    digits: int
    canonical_instrument: str


PEER_SPECS: Final = {
    V14PeerFamily.SP500: V14PeerSpec(
        family=V14PeerFamily.SP500,
        provider_symbol="US500",
        provider_symbol_id=10013,
        digits=2,
        canonical_instrument="SP500",
    ),
    V14PeerFamily.US30: V14PeerSpec(
        family=V14PeerFamily.US30,
        provider_symbol="US30",
        provider_symbol_id=10015,
        digits=2,
        canonical_instrument="US30",
    ),
}


@dataclass(frozen=True, slots=True)
class V14PeerShardPlan:
    peer: V14PeerFamily
    shard_index: int
    shard_count: int
    total_windows: int
    manifest_indices: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.peer, V14PeerFamily):
            raise ValueError("V14 peer plan family invalid")
        if type(self.shard_count) is not int or self.shard_count <= 0:
            raise ValueError("V14 shard_count must be positive")
        if type(self.shard_index) is not int or not 0 <= self.shard_index < self.shard_count:
            raise ValueError("V14 shard_index outside shard_count")
        if type(self.total_windows) is not int or self.total_windows <= 0:
            raise ValueError("V14 total_windows must be positive")
        if not self.manifest_indices:
            raise ValueError("V14 peer shard cannot be empty")
        if self.manifest_indices != tuple(sorted(self.manifest_indices)):
            raise ValueError("V14 manifest indices must be sorted")
        if len(self.manifest_indices) != len(set(self.manifest_indices)):
            raise ValueError("V14 manifest indices must be unique")
        if any(
            index < 0
            or index >= self.total_windows
            or index % self.shard_count != self.shard_index
            for index in self.manifest_indices
        ):
            raise ValueError("V14 manifest index ownership drift")


def peer_spec(peer: V14PeerFamily) -> V14PeerSpec:
    try:
        return PEER_SPECS[peer]
    except KeyError as error:  # pragma: no cover
        raise ValueError("unknown V14 peer family") from error


def plan_v14_peer_shard(
    *,
    peer: V14PeerFamily,
    total_windows: int,
    shard_index: int,
    shard_count: int = FROZEN_SHARD_COUNT,
) -> V14PeerShardPlan:
    if type(total_windows) is not int or total_windows <= 0:
        raise ValueError("V14 total_windows must be positive")
    if type(shard_count) is not int or shard_count <= 0 or shard_count > total_windows:
        raise ValueError("V14 shard_count invalid")
    if type(shard_index) is not int or not 0 <= shard_index < shard_count:
        raise ValueError("V14 shard_index invalid")
    indices = tuple(
        index for index in range(total_windows) if index % shard_count == shard_index
    )
    return V14PeerShardPlan(
        peer=peer,
        shard_index=shard_index,
        shard_count=shard_count,
        total_windows=total_windows,
        manifest_indices=indices,
    )


def v14_peer_assignment_digest(
    *,
    plan: V14PeerShardPlan,
    manifest_sha256: str = EXPECTED_MANIFEST_SHA256,
) -> str:
    if len(manifest_sha256) != 64:
        raise ValueError("V14 manifest digest must be SHA-256")
    int(manifest_sha256, 16)
    payload = {
        "identity": V14_PEER_ACQUISITION_IDENTITY,
        "peer": plan.peer.value,
        "provider_symbol": peer_spec(plan.peer).provider_symbol,
        "manifest_sha256": manifest_sha256,
        "assignment_rule": ASSIGNMENT_RULE,
        "shard_index": plan.shard_index,
        "shard_count": plan.shard_count,
        "total_windows": plan.total_windows,
        "manifest_indices": plan.manifest_indices,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field} must be SHA-256")
    int(value, 16)
    return value


def reduce_v14_peer_reports(
    reports: Sequence[Mapping[str, object]],
    *,
    peer: V14PeerFamily,
    expected_manifest_sha256: str = EXPECTED_MANIFEST_SHA256,
) -> dict[str, object]:
    _sha256(expected_manifest_sha256, "expected_manifest_sha256")
    if len(reports) != FROZEN_SHARD_COUNT:
        raise ValueError("V14 peer reduction requires exactly 16 reports")
    spec = peer_spec(peer)
    by_shard: dict[int, Mapping[str, object]] = {}
    all_indices: list[int] = []
    shard_digests: list[tuple[int, str]] = []
    bid_ticks = 0
    ask_ticks = 0
    provider_pages = 0
    page_shards = 0
    empty_bid = 0
    empty_ask = 0

    for report in reports:
        if report.get("identity") != V14_PEER_ACQUISITION_IDENTITY:
            raise ValueError("V14 peer acquisition identity mismatch")
        if report.get("peer_family") != peer.value:
            raise ValueError("V14 peer report family mismatch")
        if report.get("provider_symbol") != spec.provider_symbol:
            raise ValueError("V14 provider symbol drift")
        if report.get("provider_symbol_id") != spec.provider_symbol_id:
            raise ValueError("V14 provider symbol id drift")
        if report.get("provider_digits") != spec.digits:
            raise ValueError("V14 provider digits drift")
        if report.get("manifest_sha256") != expected_manifest_sha256:
            raise ValueError("V14 manifest digest mismatch")
        if report.get("partition") != "r8_source_only":
            raise ValueError("V14 peer acquisition escaped R8 source-only")
        if report.get("read_only_message_firewall") is not True:
            raise ValueError("V14 peer acquisition lost read-only firewall")
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
            if report.get(key) is not False:
                raise ValueError(f"V14 governance violation: {key}")

        shard = report.get("shard_index")
        if type(shard) is not int or not 0 <= shard < FROZEN_SHARD_COUNT:
            raise ValueError("V14 shard index invalid")
        if shard in by_shard:
            raise ValueError("duplicate V14 peer shard report")
        by_shard[shard] = report
        _sha256(report.get("assignment_sha256"), "assignment_sha256")
        shard_digests.append(
            (shard, _sha256(report.get("shard_dataset_sha256"), "shard_dataset_sha256"))
        )

        raw_indices = report.get("attempted_manifest_indices")
        if not isinstance(raw_indices, list) or not raw_indices:
            raise ValueError("V14 report omitted manifest indices")
        indices: list[int] = []
        for value in raw_indices:
            if type(value) is not int:
                raise ValueError("V14 manifest index must be int")
            if value % FROZEN_SHARD_COUNT != shard:
                raise ValueError("V14 manifest index owned by wrong shard")
            indices.append(value)
        if indices != sorted(indices) or len(indices) != len(set(indices)):
            raise ValueError("V14 manifest index order/uniqueness drift")
        all_indices.extend(indices)

        windows = report.get("window_reports")
        if not isinstance(windows, list) or len(windows) != len(indices):
            raise ValueError("V14 window report cardinality mismatch")
        if [item.get("manifest_index") for item in windows if isinstance(item, dict)] != indices:
            raise ValueError("V14 window report indices drift")

        for field in (
            "bid_tick_count",
            "ask_tick_count",
            "provider_page_count",
            "immutable_page_shard_count",
            "empty_bid_window_count",
            "empty_ask_window_count",
        ):
            value = report.get(field)
            if type(value) is not int or value < 0:
                raise ValueError(f"V14 {field} invalid")
        bid_ticks += cast(int, report["bid_tick_count"])
        ask_ticks += cast(int, report["ask_tick_count"])
        provider_pages += cast(int, report["provider_page_count"])
        page_shards += cast(int, report["immutable_page_shard_count"])
        empty_bid += cast(int, report["empty_bid_window_count"])
        empty_ask += cast(int, report["empty_ask_window_count"])

    if sorted(by_shard) != list(range(FROZEN_SHARD_COUNT)):
        raise ValueError("V14 peer shard set incomplete")
    if len(all_indices) != len(set(all_indices)):
        raise ValueError("V14 manifest window acquired more than once")
    if sorted(all_indices) != list(range(FROZEN_WINDOW_COUNT)):
        raise ValueError("V14 peer acquisition did not cover exact manifest")

    ordered = tuple(digest for _, digest in sorted(shard_digests))
    global_payload = {
        "identity": V14_PEER_ACQUISITION_IDENTITY,
        "peer": peer.value,
        "provider_symbol": spec.provider_symbol,
        "manifest_sha256": expected_manifest_sha256,
        "shard_digests": ordered,
    }
    global_sha = hashlib.sha256(
        json.dumps(global_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "identity": V14_PEER_ACQUISITION_IDENTITY,
        "status": "source_only_complete",
        "peer_family": peer.value,
        "provider_symbol": spec.provider_symbol,
        "provider_symbol_id": spec.provider_symbol_id,
        "provider_digits": spec.digits,
        "canonical_instrument": spec.canonical_instrument,
        "manifest_sha256": expected_manifest_sha256,
        "shard_count": FROZEN_SHARD_COUNT,
        "window_count": FROZEN_WINDOW_COUNT,
        "bid_tick_count": bid_ticks,
        "ask_tick_count": ask_ticks,
        "provider_page_count": provider_pages,
        "immutable_page_shard_count": page_shards,
        "empty_bid_window_count": empty_bid,
        "empty_ask_window_count": empty_ask,
        "full_bid_ask_window_coverage": empty_bid == 0 and empty_ask == 0,
        "global_dataset_sha256": global_sha,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "scientific_v14_outcomes_opened": False,
    }
