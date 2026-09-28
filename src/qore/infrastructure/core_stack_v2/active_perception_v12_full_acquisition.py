"""Pure partition/reduction contracts for WP-05 V12 full R8 acquisition.

The boundary is provider-free and source-only. It cannot inspect target/outcome
labels and cannot open R6/R5 or any fresh holdout.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, cast

FULL_ACQUISITION_IDENTITY: Final = (
    "QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_R8_FULL_ACQUISITION_001"
)
FROZEN_SHARD_COUNT: Final = 16
FROZEN_WINDOW_COUNT: Final = 2948
ASSIGNMENT_RULE: Final = "MANIFEST_INDEX_MOD_16"


@dataclass(frozen=True, slots=True)
class V12FullAcquisitionShardPlan:
    shard_index: int
    shard_count: int
    total_windows: int
    manifest_indices: tuple[int, ...]

    def __post_init__(self) -> None:
        if type(self.shard_count) is not int or self.shard_count <= 0:
            raise ValueError("shard_count must be positive int")
        if type(self.shard_index) is not int or not 0 <= self.shard_index < self.shard_count:
            raise ValueError("shard_index must be within shard_count")
        if type(self.total_windows) is not int or self.total_windows <= 0:
            raise ValueError("total_windows must be positive int")
        if not self.manifest_indices:
            raise ValueError("logical acquisition shard cannot be empty")
        if self.manifest_indices != tuple(sorted(self.manifest_indices)):
            raise ValueError("manifest_indices must be sorted")
        if len(self.manifest_indices) != len(set(self.manifest_indices)):
            raise ValueError("manifest_indices must be unique")
        if any(
            type(index) is not int
            or not 0 <= index < self.total_windows
            or index % self.shard_count != self.shard_index
            for index in self.manifest_indices
        ):
            raise ValueError("manifest index ownership drift")

    @property
    def window_count(self) -> int:
        return len(self.manifest_indices)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.shard_index,
            self.shard_count,
            self.total_windows,
            self.manifest_indices,
        )


def plan_v12_full_acquisition_shard(
    *,
    total_windows: int,
    shard_index: int,
    shard_count: int = FROZEN_SHARD_COUNT,
) -> V12FullAcquisitionShardPlan:
    """Assign windows using frozen manifest ordinal modulo only."""

    if type(total_windows) is not int or total_windows <= 0:
        raise ValueError("total_windows must be positive int")
    if type(shard_count) is not int or shard_count <= 0:
        raise ValueError("shard_count must be positive int")
    if shard_count > total_windows:
        raise ValueError("shard_count must not exceed total_windows")
    if type(shard_index) is not int or not 0 <= shard_index < shard_count:
        raise ValueError("shard_index must be within shard_count")
    indices = tuple(
        index
        for index in range(total_windows)
        if index % shard_count == shard_index
    )
    return V12FullAcquisitionShardPlan(
        shard_index=shard_index,
        shard_count=shard_count,
        total_windows=total_windows,
        manifest_indices=indices,
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
    flattened = tuple(
        index
        for item in ordered
        for index in item.manifest_indices
    )
    if len(flattened) != len(set(flattened)):
        raise ValueError("full acquisition shard plans overlap")
    if tuple(sorted(flattened)) != tuple(range(total_windows)):
        raise ValueError("full acquisition shard plans leave gaps")


def v12_full_acquisition_assignment_digest(
    *,
    manifest_sha256: str,
    plan: V12FullAcquisitionShardPlan,
) -> str:
    if len(manifest_sha256) != 64:
        raise ValueError("manifest_sha256 must be SHA-256 hex")
    int(manifest_sha256, 16)
    payload = {
        "identity": FULL_ACQUISITION_IDENTITY,
        "manifest_sha256": manifest_sha256,
        "assignment_rule": ASSIGNMENT_RULE,
        "plan": plan.logical_values(),
        "target_or_outcome_used": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def global_v12_dataset_digest(
    *,
    manifest_sha256: str,
    ordered_shard_dataset_sha256: tuple[str, ...],
) -> str:
    if len(manifest_sha256) != 64:
        raise ValueError("manifest_sha256 must be SHA-256 hex")
    int(manifest_sha256, 16)
    if len(ordered_shard_dataset_sha256) != FROZEN_SHARD_COUNT:
        raise ValueError("global dataset digest requires exactly 16 shard digests")
    for value in ordered_shard_dataset_sha256:
        if len(value) != 64:
            raise ValueError("shard dataset digest must be SHA-256 hex")
        int(value, 16)
    payload = {
        "identity": FULL_ACQUISITION_IDENTITY,
        "manifest_sha256": manifest_sha256,
        "ordered_shard_dataset_sha256": ordered_shard_dataset_sha256,
        "shard_count": FROZEN_SHARD_COUNT,
        "assignment_rule": ASSIGNMENT_RULE,
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _sha256(value: object, *, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field} must be SHA-256 hex")
    int(value, 16)
    return value


def reduce_v12_full_acquisition_reports(
    reports: Sequence[Mapping[str, object]],
    *,
    expected_manifest_sha256: str,
    expected_window_count: int = FROZEN_WINDOW_COUNT,
) -> dict[str, object]:
    """Prove exact 16-shard coverage before COMPLETE can exist."""

    _sha256(expected_manifest_sha256, field="expected_manifest_sha256")
    if len(reports) != FROZEN_SHARD_COUNT:
        raise ValueError("full acquisition requires exactly 16 shard reports")
    if type(expected_window_count) is not int or expected_window_count <= 0:
        raise ValueError("expected_window_count must be positive int")

    by_shard: dict[int, Mapping[str, object]] = {}
    all_indices: list[int] = []
    ordered_dataset: list[tuple[int, str]] = []
    total_bid = 0
    total_ask = 0
    total_pages = 0
    total_page_shards = 0

    for report in reports:
        if report.get("identity") != FULL_ACQUISITION_IDENTITY:
            raise ValueError("full acquisition report identity mismatch")
        if report.get("partition") != "r8":
            raise ValueError("full acquisition report escaped R8")
        if report.get("manifest_sha256") != expected_manifest_sha256:
            raise ValueError("full acquisition manifest digest mismatch")
        if report.get("shard_count") != FROZEN_SHARD_COUNT:
            raise ValueError("full acquisition shard_count mismatch")
        if report.get("total_manifest_windows") != expected_window_count:
            raise ValueError("full acquisition window universe mismatch")
        if report.get("assignment_rule") != ASSIGNMENT_RULE:
            raise ValueError("full acquisition assignment rule mismatch")

        shard_index = report.get("shard_index")
        if type(shard_index) is not int or not 0 <= shard_index < FROZEN_SHARD_COUNT:
            raise ValueError("full acquisition shard_index invalid")
        if shard_index in by_shard:
            raise ValueError("duplicate logical full-acquisition shard report")
        by_shard[shard_index] = report

        if report.get("read_only_message_firewall") is not True:
            raise ValueError("full acquisition lost read-only message firewall")
        if report.get("full_bid_ask_coverage") is not True:
            raise ValueError("full acquisition shard lacks complete BID/ASK coverage")
        for key in (
            "target_or_outcome_used_for_selection",
            "target_or_outcome_read",
            "r6_r5_read",
            "fresh_holdout_opened",
            "shared_methodology_authority",
            "shared_sizing_authority",
            "shared_risk_authority",
            "shared_order_authority",
            "shared_execution_authority",
        ):
            if report.get(key) is not False:
                raise ValueError(f"full acquisition governance violation: {key}")

        _sha256(report.get("assignment_sha256"), field="assignment_sha256")
        dataset_sha = _sha256(
            report.get("shard_dataset_sha256"),
            field="shard_dataset_sha256",
        )
        ordered_dataset.append((shard_index, dataset_sha))

        raw_indices = report.get("attempted_manifest_indices")
        if not isinstance(raw_indices, list) or not raw_indices:
            raise ValueError("full acquisition shard omitted manifest indices")
        indices: list[int] = []
        for raw_index in raw_indices:
            if type(raw_index) is not int or raw_index < 0:
                raise ValueError("full acquisition manifest index invalid")
            if raw_index % FROZEN_SHARD_COUNT != shard_index:
                raise ValueError("full acquisition index owned by wrong shard")
            indices.append(raw_index)
        if indices != sorted(indices) or len(indices) != len(set(indices)):
            raise ValueError("shard manifest indices must be sorted and unique")
        all_indices.extend(indices)

        raw_windows = report.get("window_reports")
        if not isinstance(raw_windows, list) or len(raw_windows) != len(indices):
            raise ValueError("full acquisition window report cardinality mismatch")
        reported_indices: list[int] = []
        for raw_window in raw_windows:
            if not isinstance(raw_window, dict):
                raise ValueError("full acquisition window report must be object")
            window = cast(dict[str, object], raw_window)
            manifest_index = window.get("manifest_index")
            bid_count = window.get("bid_count")
            ask_count = window.get("ask_count")
            bid_pages = window.get("bid_page_count")
            ask_pages = window.get("ask_page_count")
            if type(manifest_index) is not int:
                raise ValueError("window manifest_index must be int")
            if type(bid_count) is not int or bid_count <= 0:
                raise ValueError("full acquisition window requires BID evidence")
            if type(ask_count) is not int or ask_count <= 0:
                raise ValueError("full acquisition window requires ASK evidence")
            if type(bid_pages) is not int or bid_pages <= 0:
                raise ValueError("full acquisition window requires BID pages")
            if type(ask_pages) is not int or ask_pages <= 0:
                raise ValueError("full acquisition window requires ASK pages")
            reported_indices.append(manifest_index)
        if reported_indices != indices:
            raise ValueError("window reports do not match assigned manifest indices")

        bid_total = report.get("bid_tick_count")
        ask_total = report.get("ask_tick_count")
        provider_pages = report.get("provider_page_count")
        page_shards = report.get("immutable_page_shard_count")
        if type(bid_total) is not int or bid_total <= 0:
            raise ValueError("full acquisition shard requires BID ticks")
        if type(ask_total) is not int or ask_total <= 0:
            raise ValueError("full acquisition shard requires ASK ticks")
        if type(provider_pages) is not int or provider_pages <= 0:
            raise ValueError("full acquisition shard requires provider pages")
        if type(page_shards) is not int or page_shards <= 0:
            raise ValueError("full acquisition shard requires immutable page shards")
        total_bid += bid_total
        total_ask += ask_total
        total_pages += provider_pages
        total_page_shards += page_shards

    if sorted(by_shard) != list(range(FROZEN_SHARD_COUNT)):
        raise ValueError("full acquisition logical shard set is incomplete")
    if len(all_indices) != len(set(all_indices)):
        raise ValueError("manifest index appears in multiple acquisition shards")
    if sorted(all_indices) != list(range(expected_window_count)):
        raise ValueError("full acquisition did not cover exact frozen manifest")

    ordered_dataset_sha = tuple(
        digest for _index, digest in sorted(ordered_dataset)
    )
    return {
        "identity": FULL_ACQUISITION_IDENTITY,
        "status": "complete",
        "partition": "r8",
        "manifest_sha256": expected_manifest_sha256,
        "assignment_rule": ASSIGNMENT_RULE,
        "shard_count": FROZEN_SHARD_COUNT,
        "window_count": expected_window_count,
        "bid_tick_count": total_bid,
        "ask_tick_count": total_ask,
        "provider_page_count": total_pages,
        "immutable_page_shard_count": total_page_shards,
        "global_dataset_sha256": global_v12_dataset_digest(
            manifest_sha256=expected_manifest_sha256,
            ordered_shard_dataset_sha256=ordered_dataset_sha,
        ),
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "shared_methodology_authority": False,
        "shared_sizing_authority": False,
        "shared_risk_authority": False,
        "shared_order_authority": False,
        "shared_execution_authority": False,
    }
