"""Source-only full R8 acquisition contract for WP-05 V15 cross-asset sensors."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, cast

V15_CROSS_ASSET_ACQUISITION_IDENTITY: Final = (
    "QORE_SHARED_WP05_V15_CROSS_ASSET_R8_ACQUISITION_001"
)
FROZEN_SHARD_COUNT: Final = 16
FROZEN_WINDOW_COUNT: Final = 2948
ASSIGNMENT_RULE: Final = "MANIFEST_INDEX_MOD_16"
EXPECTED_MANIFEST_SHA256: Final = (
    "2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191"
)


class V15CrossAssetFamily(StrEnum):
    US2000_BREADTH = "US2000_BREADTH_PROXY"
    XAUUSD_DEFENSIVE = "XAUUSD_DEFENSIVE_PROXY"


@dataclass(frozen=True, slots=True)
class V15CrossAssetSpec:
    family: V15CrossAssetFamily
    semantic_role: str
    provider_symbol: str
    provider_symbol_id: int
    canonical_instrument: str

    def __post_init__(self) -> None:
        if not self.semantic_role.strip():
            raise ValueError("V15 semantic role must be non-empty")
        if not self.provider_symbol.strip():
            raise ValueError("V15 provider symbol must be non-empty")
        if type(self.provider_symbol_id) is not int or self.provider_symbol_id <= 0:
            raise ValueError("V15 provider_symbol_id must be positive")
        if not self.canonical_instrument.strip():
            raise ValueError("V15 canonical instrument must be non-empty")


CROSS_ASSET_SPECS: Final = {
    V15CrossAssetFamily.US2000_BREADTH: V15CrossAssetSpec(
        family=V15CrossAssetFamily.US2000_BREADTH,
        semantic_role="EQUITY_BREADTH_PROXY",
        provider_symbol="US2000",
        provider_symbol_id=10012,
        canonical_instrument="US2000",
    ),
    V15CrossAssetFamily.XAUUSD_DEFENSIVE: V15CrossAssetSpec(
        family=V15CrossAssetFamily.XAUUSD_DEFENSIVE,
        semantic_role="DEFENSIVE_ASSET_PROXY",
        provider_symbol="XAUUSD",
        provider_symbol_id=41,
        canonical_instrument="XAUUSD",
    ),
}


@dataclass(frozen=True, slots=True)
class V15CrossAssetShardPlan:
    family: V15CrossAssetFamily
    shard_index: int
    shard_count: int
    total_windows: int
    manifest_indices: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.family, V15CrossAssetFamily):
            raise ValueError("V15 family invalid")
        if type(self.shard_count) is not int or self.shard_count <= 0:
            raise ValueError("V15 shard_count must be positive")
        if type(self.shard_index) is not int or not 0 <= self.shard_index < self.shard_count:
            raise ValueError("V15 shard_index outside shard_count")
        if type(self.total_windows) is not int or self.total_windows <= 0:
            raise ValueError("V15 total_windows must be positive")
        if not self.manifest_indices:
            raise ValueError("V15 shard cannot be empty")
        if self.manifest_indices != tuple(sorted(self.manifest_indices)):
            raise ValueError("V15 manifest indices must be sorted")


def cross_asset_spec(family: V15CrossAssetFamily) -> V15CrossAssetSpec:
    return CROSS_ASSET_SPECS[family]


def plan_v15_cross_asset_shard(
    *,
    family: V15CrossAssetFamily,
    total_windows: int,
    shard_index: int,
    shard_count: int = FROZEN_SHARD_COUNT,
) -> V15CrossAssetShardPlan:
    if total_windows != FROZEN_WINDOW_COUNT:
        raise ValueError("V15 requires exact 2948-window source manifest")
    if shard_count != FROZEN_SHARD_COUNT:
        raise ValueError("V15 shard_count is frozen at 16")
    indices = tuple(
        index
        for index in range(total_windows)
        if index % shard_count == shard_index
    )
    return V15CrossAssetShardPlan(
        family=family,
        shard_index=shard_index,
        shard_count=shard_count,
        total_windows=total_windows,
        manifest_indices=indices,
    )


def v15_assignment_digest(
    *,
    plan: V15CrossAssetShardPlan,
    manifest_sha256: str,
) -> str:
    payload = {
        "identity": V15_CROSS_ASSET_ACQUISITION_IDENTITY,
        "family": plan.family.value,
        "shard_index": plan.shard_index,
        "shard_count": plan.shard_count,
        "total_windows": plan.total_windows,
        "manifest_indices": plan.manifest_indices,
        "manifest_sha256": manifest_sha256,
        "assignment_rule": ASSIGNMENT_RULE,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _sha256(value: object, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{name} must be sha256 hex")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be sha256 hex") from exc
    return value


def reduce_v15_cross_asset_reports(
    reports: Sequence[Mapping[str, object]],
    *,
    family: V15CrossAssetFamily,
    expected_manifest_sha256: str = EXPECTED_MANIFEST_SHA256,
) -> dict[str, object]:
    _sha256(expected_manifest_sha256, "expected_manifest_sha256")
    if len(reports) != FROZEN_SHARD_COUNT:
        raise ValueError("V15 reduction requires exactly 16 reports")
    spec = cross_asset_spec(family)
    by_shard: dict[int, Mapping[str, object]] = {}
    all_indices: list[int] = []
    shard_digests: list[tuple[int, str]] = []
    provider_digits: set[int] = set()
    bid_ticks = ask_ticks = provider_pages = page_shards = 0
    empty_bid = empty_ask = 0

    for report in reports:
        if report.get("identity") != V15_CROSS_ASSET_ACQUISITION_IDENTITY:
            raise ValueError("V15 acquisition identity mismatch")
        if report.get("family") != family.value:
            raise ValueError("V15 family mismatch")
        if report.get("semantic_role") != spec.semantic_role:
            raise ValueError("V15 semantic role drift")
        if report.get("provider_symbol") != spec.provider_symbol:
            raise ValueError("V15 provider symbol drift")
        if report.get("provider_symbol_id") != spec.provider_symbol_id:
            raise ValueError("V15 provider symbol id drift")
        digits = report.get("provider_digits")
        if type(digits) is not int or digits < 0:
            raise ValueError("V15 provider digits invalid")
        provider_digits.add(cast(int, digits))
        if report.get("manifest_sha256") != expected_manifest_sha256:
            raise ValueError("V15 manifest digest mismatch")
        if report.get("partition") != "r8_source_only":
            raise ValueError("V15 acquisition escaped R8 source-only")
        if report.get("read_only_message_firewall") is not True:
            raise ValueError("V15 read-only firewall missing")
        for key in (
            "target_or_outcome_read",
            "r6_r5_read",
            "fresh_holdout_opened",
            "scientific_v15_outcomes_opened",
            "shared_methodology_authority",
            "shared_sizing_authority",
            "shared_risk_authority",
            "shared_order_authority",
            "shared_execution_authority",
        ):
            if report.get(key) is not False:
                raise ValueError(f"V15 governance violation: {key}")

        shard = report.get("shard_index")
        if type(shard) is not int or not 0 <= shard < FROZEN_SHARD_COUNT:
            raise ValueError("V15 shard index invalid")
        if shard in by_shard:
            raise ValueError("duplicate V15 shard report")
        by_shard[cast(int, shard)] = report
        _sha256(report.get("assignment_sha256"), "assignment_sha256")
        shard_digests.append(
            (
                cast(int, shard),
                _sha256(
                    report.get("shard_dataset_sha256"),
                    "shard_dataset_sha256",
                ),
            )
        )

        raw_indices = report.get("attempted_manifest_indices")
        if not isinstance(raw_indices, list) or not raw_indices:
            raise ValueError("V15 report omitted manifest indices")
        indices: list[int] = []
        for value in raw_indices:
            if type(value) is not int:
                raise ValueError("V15 manifest index must be int")
            if value % FROZEN_SHARD_COUNT != shard:
                raise ValueError("V15 manifest index owned by wrong shard")
            indices.append(value)
        if indices != sorted(indices) or len(indices) != len(set(indices)):
            raise ValueError("V15 manifest index order/uniqueness drift")
        all_indices.extend(indices)

        windows = report.get("window_reports")
        if not isinstance(windows, list) or len(windows) != len(indices):
            raise ValueError("V15 window report cardinality mismatch")
        if [item.get("manifest_index") for item in windows if isinstance(item, dict)] != indices:
            raise ValueError("V15 window report indices drift")

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
                raise ValueError(f"V15 {field} invalid")
        bid_ticks += cast(int, report["bid_tick_count"])
        ask_ticks += cast(int, report["ask_tick_count"])
        provider_pages += cast(int, report["provider_page_count"])
        page_shards += cast(int, report["immutable_page_shard_count"])
        empty_bid += cast(int, report["empty_bid_window_count"])
        empty_ask += cast(int, report["empty_ask_window_count"])

    if sorted(by_shard) != list(range(FROZEN_SHARD_COUNT)):
        raise ValueError("V15 shard set incomplete")
    if len(provider_digits) != 1:
        raise ValueError("V15 provider digits drift across shards")
    if len(all_indices) != len(set(all_indices)):
        raise ValueError("V15 manifest window acquired more than once")
    if sorted(all_indices) != list(range(FROZEN_WINDOW_COUNT)):
        raise ValueError("V15 acquisition did not cover exact manifest")

    ordered = tuple(digest for _, digest in sorted(shard_digests))
    global_payload = {
        "identity": V15_CROSS_ASSET_ACQUISITION_IDENTITY,
        "family": family.value,
        "provider_symbol": spec.provider_symbol,
        "manifest_sha256": expected_manifest_sha256,
        "shard_digests": ordered,
    }
    global_sha = hashlib.sha256(
        json.dumps(global_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "identity": V15_CROSS_ASSET_ACQUISITION_IDENTITY,
        "status": "source_only_complete",
        "family": family.value,
        "semantic_role": spec.semantic_role,
        "provider_symbol": spec.provider_symbol,
        "provider_symbol_id": spec.provider_symbol_id,
        "provider_digits": next(iter(provider_digits)),
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
        "scientific_v15_outcomes_opened": False,
    }
