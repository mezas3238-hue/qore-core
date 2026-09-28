"""Peer-aware source-only raw integrity audit for WP-05 V14."""

from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Final, cast

from qore.infrastructure.core_stack_v2.active_perception_v14_peer_acquisition import (
    FROZEN_SHARD_COUNT,
    FROZEN_WINDOW_COUNT,
    V14PeerFamily,
    peer_spec,
    reduce_v14_peer_reports,
)

V14_SOURCE_INTEGRITY_IDENTITY: Final = (
    "QORE_SHARED_WP05_V14_PEER_MICROSTRUCTURE_SOURCE_INTEGRITY_001"
)
RAW_SCHEMA: Final = "qore.shared.wp05.v12.historical_quote_side_shard.v2"


class V14SourceIntegrityError(RuntimeError):
    """V14 peer source evidence failed a frozen integrity law."""


def _canonical_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _aware(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise V14SourceIntegrityError(f"{field} must be ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise V14SourceIntegrityError(f"{field} invalid ISO-8601") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise V14SourceIntegrityError(f"{field} must be timezone-aware")
    return parsed


def _sha(value: object, *, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise V14SourceIntegrityError(f"{field} must be SHA-256")
    try:
        int(value, 16)
    except ValueError as error:
        raise V14SourceIntegrityError(f"{field} must be SHA-256 hex") from error
    return value


@dataclass(frozen=True, slots=True)
class V14RawPageAudit:
    path: str
    side: str
    window_index: int
    page_index: int
    request_from_at: datetime
    request_to_at: datetime
    retrieved_at: datetime
    tick_count: int
    content_sha256: str
    provenance_sha256: str
    first_event_at: datetime | None
    last_event_at: datetime | None
    first_row_sha256: str | None
    last_row_sha256: str | None
    max_internal_gap_ms: int
    provider_identity_verified: bool
    exact_same_timestamp_row_repeat_count: int


def audit_v14_peer_page(
    path: Path,
    *,
    peer: V14PeerFamily,
) -> V14RawPageAudit:
    """Re-read one immutable raw page, including empty provider pages."""

    try:
        raw = gzip.decompress(path.read_bytes()).decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise V14SourceIntegrityError(f"invalid gzip/utf8 page: {path}") from error
    lines = raw.splitlines()
    if not lines:
        raise V14SourceIntegrityError("raw page is empty")

    try:
        first = json.loads(lines[0])
    except json.JSONDecodeError as error:
        raise V14SourceIntegrityError("raw page header invalid JSON") from error
    if not isinstance(first, dict) or set(first) != {"header"}:
        raise V14SourceIntegrityError("raw page must begin with one header")
    header_raw = first["header"]
    if not isinstance(header_raw, dict):
        raise V14SourceIntegrityError("raw page header must be object")
    header = cast(dict[str, Any], header_raw)

    if header.get("schema") != RAW_SCHEMA:
        raise V14SourceIntegrityError("raw page schema drift")
    side_raw = header.get("quote_side")
    if not isinstance(side_raw, str) or side_raw.upper() not in {"BID", "ASK"}:
        raise V14SourceIntegrityError("raw page side invalid")
    side = side_raw.upper()
    path_side = path.parent.name.upper()
    if path_side in {"BID", "ASK"} and path_side != side:
        raise V14SourceIntegrityError("raw page side disagrees with path")

    window_index = header.get("window_index")
    page_index = header.get("page_index")
    tick_count = header.get("tick_count")
    if type(window_index) is not int or not 0 <= window_index < FROZEN_WINDOW_COUNT:
        raise V14SourceIntegrityError("raw page window index invalid")
    if type(page_index) is not int or page_index < 0:
        raise V14SourceIntegrityError("raw page page index invalid")
    if type(tick_count) is not int or tick_count < 0:
        raise V14SourceIntegrityError("raw page tick_count invalid")

    request_from = _aware(header.get("request_from_at"), field="request_from_at")
    request_to = _aware(header.get("request_to_at"), field="request_to_at")
    retrieved_at = _aware(header.get("retrieved_at"), field="retrieved_at")
    if request_to <= request_from:
        raise V14SourceIntegrityError("raw page request interval invalid")

    content_sha = _sha(header.get("content_sha256"), field="content_sha256")
    provenance_sha = _sha(
        header.get("provenance_sha256"),
        field="provenance_sha256",
    )
    if provenance_sha not in path.name:
        raise V14SourceIntegrityError("filename does not bind provenance SHA")

    tick_rows: list[dict[str, Any]] = []
    previous_at: datetime | None = None
    previous_timestamp: datetime | None = None
    rows_at_timestamp: set[str] = set()
    repeated_same_timestamp = 0
    max_internal_gap_ms = 0
    spec = peer_spec(peer)

    for encoded in lines[1:]:
        try:
            item = json.loads(encoded)
        except json.JSONDecodeError as error:
            raise V14SourceIntegrityError("raw tick invalid JSON") from error
        if not isinstance(item, dict) or set(item) != {"tick"}:
            raise V14SourceIntegrityError("raw page contains non-tick row")
        raw_tick = item["tick"]
        if not isinstance(raw_tick, dict):
            raise V14SourceIntegrityError("raw tick must be object")
        tick = cast(dict[str, Any], raw_tick)
        expected_keys = {
            "provider_event_at",
            "provider_wire_timestamp_value",
            "provider_wire_price_value",
            "relative_price",
            "price",
        }
        if set(tick) != expected_keys:
            raise V14SourceIntegrityError("raw tick schema drift")
        event_at = _aware(tick.get("provider_event_at"), field="provider_event_at")
        if event_at < request_from or event_at > request_to:
            raise V14SourceIntegrityError("provider event escaped request interval")
        if event_at > retrieved_at:
            raise V14SourceIntegrityError("provider event occurs after retrieval")
        if type(tick.get("provider_wire_timestamp_value")) is not int:
            raise V14SourceIntegrityError("wire timestamp must be int")
        if type(tick.get("provider_wire_price_value")) is not int:
            raise V14SourceIntegrityError("wire price must be int")
        if type(tick.get("relative_price")) is not int or tick["relative_price"] <= 0:
            raise V14SourceIntegrityError("relative price must be positive int")
        if not isinstance(tick.get("price"), str) or not tick["price"]:
            raise V14SourceIntegrityError("normalized price must be string")

        if previous_at is not None:
            if event_at < previous_at:
                raise V14SourceIntegrityError("provider events are not chronological")
            max_internal_gap_ms = max(
                max_internal_gap_ms,
                int((event_at - previous_at).total_seconds() * 1000),
            )

        row_sha = _canonical_sha(tick)
        if previous_timestamp is None or event_at != previous_timestamp:
            previous_timestamp = event_at
            rows_at_timestamp = set()
        elif row_sha in rows_at_timestamp:
            repeated_same_timestamp += 1
        rows_at_timestamp.add(row_sha)
        tick_rows.append(tick)
        previous_at = event_at

    if len(tick_rows) != tick_count:
        raise V14SourceIntegrityError("header tick_count differs from raw rows")
    if _canonical_sha(tick_rows) != content_sha:
        raise V14SourceIntegrityError("raw content SHA mismatch")

    provenance = {
        key: value
        for key, value in header.items()
        if key not in {"provenance_sha256", "tick_count"}
    }
    if _canonical_sha(provenance) != provenance_sha:
        raise V14SourceIntegrityError("raw provenance SHA mismatch")

    provider_verified = False
    if tick_count > 0:
        if header.get("provider_symbol") != spec.provider_symbol:
            raise V14SourceIntegrityError("raw provider symbol drift")
        if header.get("provider_symbol_id") != spec.provider_symbol_id:
            raise V14SourceIntegrityError("raw provider symbol id drift")
        provider_verified = True
    else:
        if header.get("provider_symbol") is not None:
            raise V14SourceIntegrityError("empty page unexpectedly carries symbol")
        if header.get("provider_symbol_id") is not None:
            raise V14SourceIntegrityError("empty page unexpectedly carries symbol id")

    first_at = (
        None
        if not tick_rows
        else _aware(tick_rows[0]["provider_event_at"], field="first_event_at")
    )
    last_at = previous_at
    return V14RawPageAudit(
        path=path.as_posix(),
        side=side,
        window_index=window_index,
        page_index=page_index,
        request_from_at=request_from,
        request_to_at=request_to,
        retrieved_at=retrieved_at,
        tick_count=tick_count,
        content_sha256=content_sha,
        provenance_sha256=provenance_sha,
        first_event_at=first_at,
        last_event_at=last_at,
        first_row_sha256=None if not tick_rows else _canonical_sha(tick_rows[0]),
        last_row_sha256=None if not tick_rows else _canonical_sha(tick_rows[-1]),
        max_internal_gap_ms=max_internal_gap_ms,
        provider_identity_verified=provider_verified,
        exact_same_timestamp_row_repeat_count=repeated_same_timestamp,
    )


def _artifact_roots(raw_root: Path) -> list[Path]:
    return sorted(
        path.parent
        for path in raw_root.rglob("git-sha.txt")
        if path.parent != raw_root
    )


def _recompute_shard_digest(pages: list[V14RawPageAudit]) -> str:
    ordered = sorted(
        pages,
        key=lambda item: (
            item.side.lower(),
            item.request_from_at,
            item.window_index,
            item.page_index,
        ),
    )
    payload = [
        (
            item.side.lower(),
            item.window_index,
            item.page_index,
            item.tick_count,
            item.content_sha256,
        )
        for item in ordered
    ]
    return _canonical_sha(payload)


def _summary(values: list[int]) -> dict[str, int] | None:
    if not values:
        return None
    ordered = sorted(values)

    def pct(value: int) -> int:
        return ordered[((len(ordered) - 1) * value) // 100]

    return {
        "min": ordered[0],
        "p50": pct(50),
        "p95": pct(95),
        "p99": pct(99),
        "max": ordered[-1],
    }


def audit_v14_peer_source_dataset(
    *,
    raw_root: Path,
    peer: V14PeerFamily,
    expected_git_sha: str,
    expected_global_dataset_sha256: str,
) -> dict[str, object]:
    """Re-read the full peer dataset without labels or outcome artifacts."""

    roots = _artifact_roots(raw_root)
    if len(roots) != FROZEN_SHARD_COUNT:
        raise V14SourceIntegrityError(
            f"expected {FROZEN_SHARD_COUNT} raw artifacts, found {len(roots)}"
        )
    for root in roots:
        if (root / "git-sha.txt").read_text(encoding="utf-8").strip() != expected_git_sha:
            raise V14SourceIntegrityError("raw artifact Git SHA mismatch")

    pattern = f"{peer.value.lower()}-shard-??-report.json"
    report_paths = sorted(raw_root.rglob(pattern))
    if len(report_paths) != FROZEN_SHARD_COUNT:
        raise V14SourceIntegrityError("peer integrity requires exactly 16 reports")
    reports: list[dict[str, Any]] = []
    for path in report_paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise V14SourceIntegrityError("peer shard report malformed")
        reports.append(cast(dict[str, Any], raw))

    reduced = reduce_v14_peer_reports(tuple(reports), peer=peer)
    if reduced["global_dataset_sha256"] != expected_global_dataset_sha256:
        raise V14SourceIntegrityError("global peer dataset SHA mismatch")

    pages_by_root: dict[Path, list[V14RawPageAudit]] = defaultdict(list)
    all_pages: list[V14RawPageAudit] = []
    for root in roots:
        for page_path in sorted((root / "data").rglob("*.jsonl.gz")):
            page = audit_v14_peer_page(page_path, peer=peer)
            pages_by_root[root].append(page)
            all_pages.append(page)
        if not pages_by_root[root]:
            raise V14SourceIntegrityError("peer artifact contains no raw pages")

    expected_page_count = reduced.get("immutable_page_shard_count")
    if type(expected_page_count) is not int or len(all_pages) != expected_page_count:
        raise V14SourceIntegrityError("raw page count differs from reducer")

    raw_bid = sum(item.tick_count for item in all_pages if item.side == "BID")
    raw_ask = sum(item.tick_count for item in all_pages if item.side == "ASK")
    if raw_bid != reduced.get("bid_tick_count") or raw_ask != reduced.get("ask_tick_count"):
        raise V14SourceIntegrityError("raw tick totals differ from reducer")

    for root, pages in pages_by_root.items():
        matches = list(root.glob(pattern))
        if len(matches) != 1:
            raise V14SourceIntegrityError("artifact must carry exactly one peer report")
        report_raw = json.loads(matches[0].read_text(encoding="utf-8"))
        if not isinstance(report_raw, dict):
            raise V14SourceIntegrityError("artifact report malformed")
        if _recompute_shard_digest(pages) != report_raw.get("shard_dataset_sha256"):
            raise V14SourceIntegrityError("raw pages do not reproduce shard digest")

    page_keys: dict[tuple[str, int, int], str] = {}
    duplicate_count = 0
    conflict_count = 0
    content_counts: Counter[str] = Counter()
    grouped: dict[tuple[str, int], list[V14RawPageAudit]] = defaultdict(list)

    for page in all_pages:
        key = (page.side, page.window_index, page.page_index)
        previous = page_keys.get(key)
        if previous is not None:
            if previous == page.content_sha256:
                duplicate_count += 1
            else:
                conflict_count += 1
        else:
            page_keys[key] = page.content_sha256
        content_counts[page.content_sha256] += 1
        grouped[(page.side, page.window_index)].append(page)

    strict_overlap_count = 0
    boundary_repeat_count = 0
    missing_side_window_count = 0
    empty_page_count = 0
    max_gap_values: list[int] = []
    exact_same_timestamp_row_repeat_count = 0

    for side in ("BID", "ASK"):
        for window_index in range(FROZEN_WINDOW_COUNT):
            pages = grouped.get((side, window_index), [])
            if not pages:
                missing_side_window_count += 1
                continue
            chronological = sorted(
                pages,
                key=lambda item: (
                    item.request_from_at,
                    item.page_index,
                ),
            )
            empty_page_count += sum(item.tick_count == 0 for item in chronological)
            nonempty = [
                item
                for item in chronological
                if item.first_event_at is not None and item.last_event_at is not None
            ]
            max_gap = max(
                (item.max_internal_gap_ms for item in nonempty),
                default=0,
            )
            for left, right in zip(nonempty, nonempty[1:], strict=False):
                assert left.last_event_at is not None
                assert right.first_event_at is not None
                if right.first_event_at < left.last_event_at:
                    strict_overlap_count += 1
                gap = int(
                    (right.first_event_at - left.last_event_at).total_seconds()
                    * 1000
                )
                max_gap = max(max_gap, gap)
                if (
                    right.first_event_at == left.last_event_at
                    and right.first_row_sha256 == left.last_row_sha256
                ):
                    boundary_repeat_count += 1
            max_gap_values.append(max_gap)
            exact_same_timestamp_row_repeat_count += sum(
                item.exact_same_timestamp_row_repeat_count
                for item in chronological
            )

    repeated_content_hash_excess = sum(
        count - 1 for count in content_counts.values() if count > 1
    )
    hard_failures = {
        "page_key_duplicate_count": duplicate_count,
        "page_key_conflict_count": conflict_count,
        "strict_page_time_overlap_count": strict_overlap_count,
        "exact_boundary_row_repeat_count": boundary_repeat_count,
        "missing_side_window_count": missing_side_window_count,
    }
    status = (
        "green_source_integrity"
        if all(value == 0 for value in hard_failures.values())
        else "blocked_for_review"
    )
    spec = peer_spec(peer)
    return {
        "identity": V14_SOURCE_INTEGRITY_IDENTITY,
        "status": status,
        "peer_family": peer.value,
        "provider_symbol": spec.provider_symbol,
        "provider_symbol_id": spec.provider_symbol_id,
        "provider_digits": spec.digits,
        "upstream_git_sha": expected_git_sha,
        "global_dataset_sha256": expected_global_dataset_sha256,
        "raw_artifact_count": len(roots),
        "raw_provider_page_count": len(all_pages),
        "raw_bid_tick_count": raw_bid,
        "raw_ask_tick_count": raw_ask,
        "empty_page_count": empty_page_count,
        "provider_verified_nonempty_page_count": sum(
            item.provider_identity_verified for item in all_pages
        ),
        "page_key_duplicate_count": duplicate_count,
        "page_key_conflict_count": conflict_count,
        "strict_page_time_overlap_count": strict_overlap_count,
        "exact_boundary_row_repeat_count": boundary_repeat_count,
        "missing_side_window_count": missing_side_window_count,
        "repeated_content_hash_excess": repeated_content_hash_excess,
        "exact_same_timestamp_row_repeat_count": (
            exact_same_timestamp_row_repeat_count
        ),
        "window_max_interevent_gap_ms": _summary(max_gap_values),
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
