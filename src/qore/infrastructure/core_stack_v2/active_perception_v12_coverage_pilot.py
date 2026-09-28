"""Outcome-blind temporal coverage pilot for Shared WP-05 V12.

The pilot chooses a small deterministic set of acquisition-manifest windows
spanning the full R8 time range. Selection depends only on manifest ordinal
position and never on a matured target or trade outcome.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class V12CoveragePilotStatus(StrEnum):
    FULL_BID_ASK_HISTORY = "full_bid_ask_history"
    PARTIAL_BID_ASK_HISTORY = "partial_bid_ask_history"
    NO_HISTORY = "no_history"


@dataclass(frozen=True, slots=True)
class V12CoveragePilotWindow:
    manifest_index: int
    from_at: datetime
    to_at: datetime
    source_count: int

    def __post_init__(self) -> None:
        if type(self.manifest_index) is not int or self.manifest_index < 0:
            raise ValueError("pilot manifest_index must be non-negative int")
        for name, value in (("from_at", self.from_at), ("to_at", self.to_at)):
            if (
                not isinstance(value, datetime)
                or value.tzinfo is None
                or value.utcoffset() is None
            ):
                raise ValueError(f"pilot {name} must be timezone-aware")
        if self.to_at <= self.from_at:
            raise ValueError("pilot window must be positive")
        if type(self.source_count) is not int or self.source_count <= 0:
            raise ValueError("pilot source_count must be positive")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.manifest_index,
            self.from_at.astimezone(UTC).isoformat(timespec="microseconds"),
            self.to_at.astimezone(UTC).isoformat(timespec="microseconds"),
            self.source_count,
        )


@dataclass(frozen=True, slots=True)
class V12CoveragePilotSample:
    manifest_index: int
    bid_count: int
    ask_count: int

    def __post_init__(self) -> None:
        if type(self.manifest_index) is not int or self.manifest_index < 0:
            raise ValueError("sample manifest_index must be non-negative int")
        if type(self.bid_count) is not int or self.bid_count < 0:
            raise ValueError("sample bid_count must be non-negative int")
        if type(self.ask_count) is not int or self.ask_count < 0:
            raise ValueError("sample ask_count must be non-negative int")


def _parse_manifest_window(
    value: Sequence[object],
    *,
    manifest_index: int,
) -> V12CoveragePilotWindow:
    if len(value) != 3:
        raise ValueError("manifest window must contain from/to/source_count")
    from_raw, to_raw, source_count = value
    if not isinstance(from_raw, str) or not isinstance(to_raw, str):
        raise ValueError("manifest window timestamps must be ISO strings")
    if type(source_count) is not int:
        raise ValueError("manifest window source_count must be int")
    try:
        from_at = datetime.fromisoformat(from_raw)
        to_at = datetime.fromisoformat(to_raw)
    except ValueError as error:
        raise ValueError("manifest window timestamp is invalid ISO-8601") from error
    return V12CoveragePilotWindow(
        manifest_index=manifest_index,
        from_at=from_at,
        to_at=to_at,
        source_count=source_count,
    )


def select_v12_temporal_coverage_pilot(
    windows: Sequence[Sequence[object]],
) -> tuple[V12CoveragePilotWindow, ...]:
    """Choose deterministic first/Q1/mid/Q3/last windows from the manifest."""

    if not windows:
        raise ValueError("V12 coverage pilot requires manifest windows")
    last = len(windows) - 1
    candidate_indices = (
        0,
        last // 4,
        last // 2,
        (3 * last) // 4,
        last,
    )
    indices = tuple(dict.fromkeys(candidate_indices))
    selected = tuple(
        _parse_manifest_window(windows[index], manifest_index=index)
        for index in indices
    )
    if tuple(sorted(item.manifest_index for item in selected)) != tuple(
        item.manifest_index for item in selected
    ):
        raise ValueError("coverage pilot windows must preserve chronological order")
    return selected


def v12_coverage_pilot_selection_digest(
    *,
    manifest_sha256: str,
    windows: Sequence[V12CoveragePilotWindow],
) -> str:
    if len(manifest_sha256) != 64:
        raise ValueError("manifest_sha256 must be SHA-256 hex")
    int(manifest_sha256, 16)
    if not windows:
        raise ValueError("coverage pilot digest requires selected windows")
    payload = {
        "manifest_sha256": manifest_sha256,
        "selection_rule": "FIRST_Q1_MID_Q3_LAST_BY_MANIFEST_ORDINAL",
        "windows": [item.logical_values() for item in windows],
        "target_or_outcome_used": False,
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def classify_v12_coverage_pilot(
    samples: Sequence[V12CoveragePilotSample],
) -> V12CoveragePilotStatus:
    if not samples:
        raise ValueError("coverage pilot classification requires samples")
    if all(item.bid_count > 0 and item.ask_count > 0 for item in samples):
        return V12CoveragePilotStatus.FULL_BID_ASK_HISTORY
    if any(item.bid_count > 0 or item.ask_count > 0 for item in samples):
        return V12CoveragePilotStatus.PARTIAL_BID_ASK_HISTORY
    return V12CoveragePilotStatus.NO_HISTORY
