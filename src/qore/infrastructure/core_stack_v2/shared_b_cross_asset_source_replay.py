"""Deterministic replay verification for Architect-B source evidence."""

from __future__ import annotations

import gzip
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from qore.infrastructure.core_stack_v2.active_perception_post_v13_sensor_availability import (
    HistoricalPeerCoverageStatus,
    HistoricalWindowCoverage,
    classify_historical_peer_coverage,
)

SHARED_B_CROSS_ASSET_RAW_IDENTITY: Final = (
    "SHARED_B_WP05_CROSS_ASSET_AVAILABILITY_RAW_001"
)
SHARED_B_CROSS_ASSET_REPLAY_IDENTITY: Final = (
    "SHARED_B_WP05_CROSS_ASSET_AVAILABILITY_REPLAY_001"
)
FROZEN_PILOT_INDICES: Final = (0, 736, 1473, 2210, 2947)


class SharedBCrossAssetReplayError(ValueError):
    """Architect-B raw source evidence failed deterministic verification."""


@dataclass(frozen=True, slots=True)
class VerifiedShard:
    quote_side: str
    window_index: int
    page_index: int
    request_from_at: datetime
    request_to_at: datetime
    tick_count: int
    content_sha256: str
    provenance_sha256: str
    relative_path: str


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _parse_utc(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise SharedBCrossAssetReplayError(f"{field} must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SharedBCrossAssetReplayError(
            f"{field} must be an ISO timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SharedBCrossAssetReplayError(f"{field} must be timezone-aware")
    return parsed.astimezone(UTC)


def _digest_json(value: object) -> str:
    return _sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    )


def verify_historical_quote_shard(
    *,
    path: Path,
    expected: Mapping[str, object],
) -> VerifiedShard:
    """Verify one immutable gzip JSONL quote-side shard from raw bytes."""

    if not path.is_file():
        raise SharedBCrossAssetReplayError(f"raw shard missing: {path}")
    try:
        raw = gzip.decompress(path.read_bytes()).decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise SharedBCrossAssetReplayError(
            f"raw shard cannot be decoded: {path}"
        ) from exc
    lines = [line for line in raw.splitlines() if line]
    if not lines:
        raise SharedBCrossAssetReplayError("raw shard is empty")
    try:
        first = json.loads(lines[0])
        rows = [json.loads(line) for line in lines[1:]]
    except json.JSONDecodeError as exc:
        raise SharedBCrossAssetReplayError("raw shard JSON is invalid") from exc
    if not isinstance(first, dict) or set(first) != {"header"}:
        raise SharedBCrossAssetReplayError("raw shard header envelope invalid")
    header = first["header"]
    if not isinstance(header, dict):
        raise SharedBCrossAssetReplayError("raw shard header invalid")

    tick_rows: list[dict[str, object]] = []
    previous_event_at: datetime | None = None
    request_from_at = _parse_utc(
        header.get("request_from_at"),
        field="request_from_at",
    )
    request_to_at = _parse_utc(
        header.get("request_to_at"),
        field="request_to_at",
    )
    if request_to_at <= request_from_at:
        raise SharedBCrossAssetReplayError("raw shard request interval invalid")

    for envelope in rows:
        if not isinstance(envelope, dict) or set(envelope) != {"tick"}:
            raise SharedBCrossAssetReplayError("raw shard tick envelope invalid")
        tick = envelope["tick"]
        if not isinstance(tick, dict):
            raise SharedBCrossAssetReplayError("raw shard tick invalid")
        observed_at = _parse_utc(
            tick.get("provider_event_at"),
            field="provider_event_at",
        )
        if observed_at < request_from_at or observed_at > request_to_at:
            raise SharedBCrossAssetReplayError(
                "provider event escaped its historical request interval"
            )
        if previous_event_at is not None and observed_at < previous_event_at:
            raise SharedBCrossAssetReplayError(
                "raw shard provider events are out of order"
            )
        previous_event_at = observed_at
        tick_rows.append(tick)

    tick_count = header.get("tick_count")
    if type(tick_count) is not int or tick_count != len(tick_rows):
        raise SharedBCrossAssetReplayError("raw shard tick count mismatch")
    content_sha256 = header.get("content_sha256")
    if not isinstance(content_sha256, str) or content_sha256 != _digest_json(
        tick_rows
    ):
        raise SharedBCrossAssetReplayError("raw shard content digest mismatch")

    provenance_sha256 = header.get("provenance_sha256")
    if not isinstance(provenance_sha256, str):
        raise SharedBCrossAssetReplayError("raw shard provenance digest missing")
    provenance = {
        key: value
        for key, value in header.items()
        if key not in {"provenance_sha256", "tick_count"}
    }
    if provenance_sha256 != _digest_json(provenance):
        raise SharedBCrossAssetReplayError(
            "raw shard provenance digest mismatch"
        )

    quote_side = header.get("quote_side")
    if quote_side not in {"BID", "ASK"}:
        raise SharedBCrossAssetReplayError("raw shard quote side invalid")
    window_index = header.get("window_index")
    page_index = header.get("page_index")
    if type(window_index) is not int or window_index < 0:
        raise SharedBCrossAssetReplayError("raw shard window index invalid")
    if type(page_index) is not int or page_index < 0:
        raise SharedBCrossAssetReplayError("raw shard page index invalid")

    checks = {
        "quote_side": quote_side,
        "window_index": window_index,
        "page_index": page_index,
        "tick_count": tick_count,
        "content_sha256": content_sha256,
        "provenance_sha256": provenance_sha256,
        "relative_path": path.name
        if expected.get("relative_path") == path.name
        else expected.get("relative_path"),
    }
    for key in (
        "quote_side",
        "window_index",
        "page_index",
        "tick_count",
        "content_sha256",
        "provenance_sha256",
    ):
        if expected.get(key) != checks[key]:
            raise SharedBCrossAssetReplayError(
                f"raw shard manifest mismatch: {key}"
            )

    relative_path = expected.get("relative_path")
    if not isinstance(relative_path, str) or not relative_path:
        raise SharedBCrossAssetReplayError(
            "raw shard relative_path missing from manifest"
        )
    return VerifiedShard(
        quote_side=quote_side,
        window_index=window_index,
        page_index=page_index,
        request_from_at=request_from_at,
        request_to_at=request_to_at,
        tick_count=tick_count,
        content_sha256=content_sha256,
        provenance_sha256=provenance_sha256,
        relative_path=relative_path,
    )


def classify_verified_window_counts(
    counts: Mapping[int, Mapping[str, int]],
    *,
    required_indices: Sequence[int] = FROZEN_PILOT_INDICES,
) -> HistoricalPeerCoverageStatus:
    rows: list[HistoricalWindowCoverage] = []
    if tuple(required_indices) != tuple(sorted(set(required_indices))):
        raise SharedBCrossAssetReplayError(
            "required pilot indices must be unique and sorted"
        )
    if set(counts) != set(required_indices):
        raise SharedBCrossAssetReplayError(
            "verified coverage does not match frozen pilot windows"
        )
    for index in required_indices:
        sides = counts[index]
        if set(sides) != {"BID", "ASK"}:
            raise SharedBCrossAssetReplayError(
                "verified coverage must contain BID and ASK"
            )
        bid_count = sides["BID"]
        ask_count = sides["ASK"]
        if type(bid_count) is not int or bid_count < 0:
            raise SharedBCrossAssetReplayError("verified BID count invalid")
        if type(ask_count) is not int or ask_count < 0:
            raise SharedBCrossAssetReplayError("verified ASK count invalid")
        rows.append(
            HistoricalWindowCoverage(
                manifest_index=index,
                bid_count=bid_count,
                ask_count=ask_count,
            )
        )
    return classify_historical_peer_coverage(rows)


def raw_dataset_digest(
    *,
    provider_symbol: str,
    shards: Sequence[VerifiedShard],
) -> str:
    if not provider_symbol:
        raise SharedBCrossAssetReplayError("provider_symbol must be non-empty")
    payload = [
        (
            provider_symbol,
            shard.quote_side,
            shard.window_index,
            shard.page_index,
            shard.tick_count,
            shard.content_sha256,
        )
        for shard in sorted(
            shards,
            key=lambda item: (
                item.quote_side,
                item.window_index,
                item.page_index,
            ),
        )
    ]
    return _digest_json(payload)
