"""Source-only raw integrity audit for WP-05 V12 historical BID/ASK evidence.

This module is deliberately outcome-blind.  It re-reads immutable acquisition
artifacts and verifies raw page framing, hashes, provenance, chronology,
coverage, duplicate/conflict structure and source-only gap diagnostics.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Final, cast

from qore.infrastructure.core_stack_v2.active_perception_v12_full_acquisition import (
    FROZEN_SHARD_COUNT,
    FROZEN_WINDOW_COUNT,
    reduce_v12_full_acquisition_reports,
)

SOURCE_INTEGRITY_IDENTITY: Final = (
    "QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_SOURCE_ONLY_INTEGRITY_001"
)
RAW_SCHEMA: Final = "qore.shared.wp05.v12.historical_quote_side_shard.v2"


class V12SourceIntegrityError(RuntimeError):
    """Raw V12 acquisition evidence failed a frozen source-only integrity law."""


def _canonical_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _aware_iso(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise V12SourceIntegrityError(f"{field} must be ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise V12SourceIntegrityError(f"{field} is invalid ISO-8601") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise V12SourceIntegrityError(f"{field} must be timezone-aware")
    return parsed


def _side(value: object) -> str:
    if not isinstance(value, str):
        raise V12SourceIntegrityError("quote_side must be string")
    normalized = value.upper()
    if normalized not in {"BID", "ASK"}:
        raise V12SourceIntegrityError("quote_side must be BID or ASK")
    return normalized


def _positive_int(value: object, *, field: str) -> int:
    if type(value) is not int or value <= 0:
        raise V12SourceIntegrityError(f"{field} must be positive int")
    return value


def _nonnegative_int(value: object, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise V12SourceIntegrityError(f"{field} must be non-negative int")
    return value


@dataclass(frozen=True, slots=True)
class V12RawPageAudit:
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
    first_event_at: datetime
    last_event_at: datetime
    first_row_sha256: str
    last_row_sha256: str
    max_internal_gap_ms: int
    same_timestamp_multiupdate_groups: int
    same_timestamp_distinct_price_groups: int
    exact_same_timestamp_row_repeat_count: int


def audit_historical_quote_side_page(
    path: Path,
    *,
    expected_window_count: int = FROZEN_WINDOW_COUNT,
) -> V12RawPageAudit:
    """Audit one immutable gzip JSONL provider page without any outcome data."""

    try:
        raw = gzip.decompress(path.read_bytes()).decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise V12SourceIntegrityError(f"invalid gzip/utf8 page: {path}") from error

    lines = raw.splitlines()
    if len(lines) < 2:
        raise V12SourceIntegrityError("historical page must contain header and ticks")
    try:
        first = json.loads(lines[0])
    except json.JSONDecodeError as error:
        raise V12SourceIntegrityError("historical page header is invalid JSON") from error
    if not isinstance(first, dict) or set(first) != {"header"}:
        raise V12SourceIntegrityError("historical page must start with one header object")
    header_raw = first["header"]
    if not isinstance(header_raw, dict):
        raise V12SourceIntegrityError("historical page header must be object")
    header = cast(dict[str, Any], header_raw)

    if header.get("schema") != RAW_SCHEMA:
        raise V12SourceIntegrityError("historical page schema mismatch")
    side = _side(header.get("quote_side"))
    window_index = _nonnegative_int(header.get("window_index"), field="window_index")
    if window_index >= expected_window_count:
        raise V12SourceIntegrityError("window_index escaped frozen manifest")
    page_index = _nonnegative_int(header.get("page_index"), field="page_index")
    request_from_at = _aware_iso(header.get("request_from_at"), field="request_from_at")
    request_to_at = _aware_iso(header.get("request_to_at"), field="request_to_at")
    retrieved_at = _aware_iso(header.get("retrieved_at"), field="retrieved_at")
    if request_to_at <= request_from_at:
        raise V12SourceIntegrityError("historical page request interval is not positive")

    tick_count = _positive_int(header.get("tick_count"), field="tick_count")
    stored_content_sha = header.get("content_sha256")
    stored_provenance_sha = header.get("provenance_sha256")
    if not isinstance(stored_content_sha, str) or len(stored_content_sha) != 64:
        raise V12SourceIntegrityError("content_sha256 missing or malformed")
    if not isinstance(stored_provenance_sha, str) or len(stored_provenance_sha) != 64:
        raise V12SourceIntegrityError("provenance_sha256 missing or malformed")
    try:
        int(stored_content_sha, 16)
        int(stored_provenance_sha, 16)
    except ValueError as error:
        raise V12SourceIntegrityError("page digest is not hexadecimal SHA-256") from error

    path_side = path.parent.name.upper()
    if path_side in {"BID", "ASK"} and path_side != side:
        raise V12SourceIntegrityError("page side disagrees with storage path")
    if stored_provenance_sha not in path.name:
        raise V12SourceIntegrityError("filename does not bind provenance digest")

    tick_rows: list[dict[str, Any]] = []
    previous_at: datetime | None = None
    previous_timestamp: datetime | None = None
    timestamp_rows: set[tuple[tuple[str, object], ...]] = set()
    timestamp_prices: set[int] = set()
    same_timestamp_multiupdate_groups = 0
    same_timestamp_distinct_price_groups = 0
    exact_same_timestamp_row_repeat_count = 0
    group_size = 0
    max_internal_gap_ms = 0

    def close_group() -> None:
        nonlocal same_timestamp_multiupdate_groups
        nonlocal same_timestamp_distinct_price_groups
        if group_size > 1:
            same_timestamp_multiupdate_groups += 1
            if len(timestamp_prices) > 1:
                same_timestamp_distinct_price_groups += 1

    for encoded in lines[1:]:
        try:
            item = json.loads(encoded)
        except json.JSONDecodeError as error:
            raise V12SourceIntegrityError("historical tick row is invalid JSON") from error
        if not isinstance(item, dict) or set(item) != {"tick"}:
            raise V12SourceIntegrityError("historical page contains non-tick row")
        tick_raw = item["tick"]
        if not isinstance(tick_raw, dict):
            raise V12SourceIntegrityError("historical tick must be object")
        tick = cast(dict[str, Any], tick_raw)
        expected_tick_keys = {
            "provider_event_at",
            "provider_wire_timestamp_value",
            "provider_wire_price_value",
            "relative_price",
            "price",
        }
        if set(tick) != expected_tick_keys:
            raise V12SourceIntegrityError("historical tick schema drift")
        event_at = _aware_iso(
            tick.get("provider_event_at"),
            field="provider_event_at",
        )
        if event_at < request_from_at or event_at > request_to_at:
            raise V12SourceIntegrityError("provider event escaped requested interval")
        if event_at > retrieved_at:
            raise V12SourceIntegrityError("provider event occurs after retrieval time")
        relative_price = _positive_int(tick.get("relative_price"), field="relative_price")
        if previous_at is not None:
            if event_at < previous_at:
                raise V12SourceIntegrityError("provider events are not chronological")
            gap_ms = int((event_at - previous_at).total_seconds() * 1000)
            if gap_ms > max_internal_gap_ms:
                max_internal_gap_ms = gap_ms

        row_fingerprint = tuple(
            (key, cast(object, tick[key]))
            for key in sorted(tick)
        )
        if previous_timestamp is None or event_at != previous_timestamp:
            if previous_timestamp is not None:
                close_group()
            previous_timestamp = event_at
            timestamp_rows = set()
            timestamp_prices = set()
            group_size = 0
        group_size += 1
        if row_fingerprint in timestamp_rows:
            exact_same_timestamp_row_repeat_count += 1
        timestamp_rows.add(row_fingerprint)
        timestamp_prices.add(relative_price)

        tick_rows.append(tick)
        previous_at = event_at

    close_group()
    if len(tick_rows) != tick_count:
        raise V12SourceIntegrityError("stored tick_count differs from raw tick rows")

    recomputed_content = _canonical_sha(tick_rows)
    if recomputed_content != stored_content_sha:
        raise V12SourceIntegrityError("raw tick content hash mismatch")

    provenance = {
        key: value
        for key, value in header.items()
        if key not in {"provenance_sha256", "tick_count"}
    }
    recomputed_provenance = _canonical_sha(provenance)
    if recomputed_provenance != stored_provenance_sha:
        raise V12SourceIntegrityError("raw provenance hash mismatch")

    if not tick_rows or previous_at is None:
        raise V12SourceIntegrityError("historical page contains no provider events")
    first_at = _aware_iso(tick_rows[0].get("provider_event_at"), field="first_event_at")
    last_at = previous_at
    return V12RawPageAudit(
        path=path.as_posix(),
        side=side,
        window_index=window_index,
        page_index=page_index,
        request_from_at=request_from_at,
        request_to_at=request_to_at,
        retrieved_at=retrieved_at,
        tick_count=tick_count,
        content_sha256=stored_content_sha,
        provenance_sha256=stored_provenance_sha,
        first_event_at=first_at,
        last_event_at=last_at,
        first_row_sha256=_canonical_sha(tick_rows[0]),
        last_row_sha256=_canonical_sha(tick_rows[-1]),
        max_internal_gap_ms=max_internal_gap_ms,
        same_timestamp_multiupdate_groups=same_timestamp_multiupdate_groups,
        same_timestamp_distinct_price_groups=same_timestamp_distinct_price_groups,
        exact_same_timestamp_row_repeat_count=exact_same_timestamp_row_repeat_count,
    )


def _summary(values: list[int]) -> dict[str, int]:
    if not values:
        raise V12SourceIntegrityError("cannot summarize empty source diagnostic")
    ordered = sorted(values)

    def percentile(percent: int) -> int:
        index = ((len(ordered) - 1) * percent) // 100
        return ordered[index]

    return {
        "min": ordered[0],
        "p50": percentile(50),
        "p95": percentile(95),
        "p99": percentile(99),
        "max": ordered[-1],
    }


def _load_reports(raw_root: Path) -> tuple[list[dict[str, Any]], list[Path]]:
    report_paths = sorted(raw_root.rglob("shard-??-report.json"))
    reports: list[dict[str, Any]] = []
    for path in report_paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise V12SourceIntegrityError("shard report must be JSON object")
        reports.append(cast(dict[str, Any], raw))
    return reports, report_paths


def _artifact_roots(raw_root: Path) -> list[Path]:
    roots = sorted(
        path.parent
        for path in raw_root.rglob("git-sha.txt")
        if path.parent != raw_root
    )
    return roots


def _recompute_shard_dataset_digest(
    pages: list[V12RawPageAudit],
) -> str:
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


def audit_v12_source_only_dataset(
    *,
    raw_root: Path,
    expected_git_sha: str,
    expected_manifest_sha256: str,
    expected_global_dataset_sha256: str,
    expected_artifact_count: int = FROZEN_SHARD_COUNT,
    expected_window_count: int = FROZEN_WINDOW_COUNT,
) -> dict[str, object]:
    """Re-read the complete frozen R8 acquisition without target/outcome data."""

    roots = _artifact_roots(raw_root)
    if len(roots) != expected_artifact_count:
        raise V12SourceIntegrityError(
            f"expected {expected_artifact_count} raw artifacts, found {len(roots)}"
        )
    for root in roots:
        git_sha = (root / "git-sha.txt").read_text(encoding="utf-8").strip()
        if git_sha != expected_git_sha:
            raise V12SourceIntegrityError("raw artifact Git SHA mismatch")

    reports, _report_paths = _load_reports(raw_root)
    if len(reports) != FROZEN_SHARD_COUNT:
        raise V12SourceIntegrityError("source audit requires exactly 16 shard reports")
    reduced = reduce_v12_full_acquisition_reports(
        reports,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_window_count=expected_window_count,
    )
    if reduced["global_dataset_sha256"] != expected_global_dataset_sha256:
        raise V12SourceIntegrityError("global acquisition dataset digest mismatch")

    pages_by_artifact: dict[Path, list[V12RawPageAudit]] = defaultdict(list)
    all_pages: list[V12RawPageAudit] = []
    for root in roots:
        page_paths = sorted((root / "data").rglob("*.jsonl.gz"))
        if not page_paths:
            raise V12SourceIntegrityError("raw acquisition artifact contains no pages")
        for page_path in page_paths:
            page = audit_historical_quote_side_page(
                page_path,
                expected_window_count=expected_window_count,
            )
            pages_by_artifact[root].append(page)
            all_pages.append(page)

    expected_pages = reduced.get("immutable_page_shard_count")
    if type(expected_pages) is not int or len(all_pages) != expected_pages:
        raise V12SourceIntegrityError("raw page count differs from frozen reducer")

    report_by_shard: dict[int, dict[str, Any]] = {}
    for report in reports:
        shard_index = report.get("shard_index")
        if type(shard_index) is not int:
            raise V12SourceIntegrityError("shard report index is invalid")
        report_by_shard[shard_index] = report

    raw_bid = sum(page.tick_count for page in all_pages if page.side == "BID")
    raw_ask = sum(page.tick_count for page in all_pages if page.side == "ASK")
    if raw_bid != reduced.get("bid_tick_count") or raw_ask != reduced.get("ask_tick_count"):
        raise V12SourceIntegrityError("raw tick totals differ from frozen reducer")

    for root, pages in pages_by_artifact.items():
        report_paths = list(root.glob("shard-??-report.json"))
        if len(report_paths) != 1:
            raise V12SourceIntegrityError("artifact must contain exactly one shard report")
        report = json.loads(report_paths[0].read_text(encoding="utf-8"))
        if not isinstance(report, dict):
            raise V12SourceIntegrityError("artifact shard report malformed")
        expected_digest = report.get("shard_dataset_sha256")
        if _recompute_shard_dataset_digest(pages) != expected_digest:
            raise V12SourceIntegrityError("raw pages do not reproduce shard dataset digest")

    page_keys: dict[tuple[str, int, int], str] = {}
    page_key_duplicate_count = 0
    page_key_conflict_count = 0
    content_hash_counts: Counter[str] = Counter()
    grouped: dict[tuple[str, int], list[V12RawPageAudit]] = defaultdict(list)

    for page in all_pages:
        key = (page.side, page.window_index, page.page_index)
        existing = page_keys.get(key)
        if existing is not None:
            if existing == page.content_sha256:
                page_key_duplicate_count += 1
            else:
                page_key_conflict_count += 1
        else:
            page_keys[key] = page.content_sha256
        content_hash_counts[page.content_sha256] += 1
        grouped[(page.side, page.window_index)].append(page)

    strict_page_time_overlap_count = 0
    exact_boundary_row_repeat_count = 0
    window_max_gap_ms: list[int] = []
    leading_gap_ms: list[int] = []
    trailing_gap_ms: list[int] = []
    ticks_per_minute_milli: list[int] = []
    same_timestamp_multiupdate_groups = 0
    same_timestamp_distinct_price_groups = 0
    exact_same_timestamp_row_repeat_count = 0

    for side in ("BID", "ASK"):
        for window_index in range(expected_window_count):
            pages = grouped.get((side, window_index), [])
            if not pages:
                raise V12SourceIntegrityError(
                    f"window {window_index} lacks raw {side} evidence"
                )
            chronological = sorted(
                pages,
                key=lambda item: (item.first_event_at, item.last_event_at, item.page_index),
            )
            total_ticks = sum(item.tick_count for item in chronological)
            first_at = min(item.first_event_at for item in chronological)
            last_at = max(item.last_event_at for item in chronological)
            request_from_at = min(item.request_from_at for item in chronological)
            request_to_at = max(item.request_to_at for item in chronological)
            max_gap = max(item.max_internal_gap_ms for item in chronological)

            for left, right in zip(chronological, chronological[1:], strict=False):
                if right.first_event_at < left.last_event_at:
                    strict_page_time_overlap_count += 1
                boundary_gap = int(
                    (right.first_event_at - left.last_event_at).total_seconds() * 1000
                )
                if boundary_gap > max_gap:
                    max_gap = boundary_gap
                if (
                    right.first_event_at == left.last_event_at
                    and right.first_row_sha256 == left.last_row_sha256
                ):
                    exact_boundary_row_repeat_count += 1

            duration_ms = max(
                1,
                int((request_to_at - request_from_at).total_seconds() * 1000),
            )
            leading_gap_ms.append(int((first_at - request_from_at).total_seconds() * 1000))
            trailing_gap_ms.append(int((request_to_at - last_at).total_seconds() * 1000))
            window_max_gap_ms.append(max_gap)
            ticks_per_minute_milli.append((total_ticks * 60_000_000) // duration_ms)

            same_timestamp_multiupdate_groups += sum(
                item.same_timestamp_multiupdate_groups for item in chronological
            )
            same_timestamp_distinct_price_groups += sum(
                item.same_timestamp_distinct_price_groups for item in chronological
            )
            exact_same_timestamp_row_repeat_count += sum(
                item.exact_same_timestamp_row_repeat_count for item in chronological
            )

    repeated_content_hash_excess = sum(
        count - 1 for count in content_hash_counts.values() if count > 1
    )

    hard_failures = {
        "page_key_duplicate_count": page_key_duplicate_count,
        "page_key_conflict_count": page_key_conflict_count,
        "strict_page_time_overlap_count": strict_page_time_overlap_count,
        "exact_boundary_row_repeat_count": exact_boundary_row_repeat_count,
    }
    status = (
        "green_source_integrity"
        if all(value == 0 for value in hard_failures.values())
        else "blocked_for_review"
    )

    return {
        "identity": SOURCE_INTEGRITY_IDENTITY,
        "status": status,
        "upstream_git_sha": expected_git_sha,
        "manifest_sha256": expected_manifest_sha256,
        "global_dataset_sha256": expected_global_dataset_sha256,
        "artifact_count": len(roots),
        "window_count": expected_window_count,
        "raw_page_count": len(all_pages),
        "raw_bid_tick_count": raw_bid,
        "raw_ask_tick_count": raw_ask,
        **hard_failures,
        "repeated_content_hash_excess": repeated_content_hash_excess,
        "same_timestamp_multiupdate_groups": same_timestamp_multiupdate_groups,
        "same_timestamp_distinct_price_groups": same_timestamp_distinct_price_groups,
        "exact_same_timestamp_row_repeat_count": exact_same_timestamp_row_repeat_count,
        "window_max_interevent_gap_ms": _summary(window_max_gap_ms),
        "window_leading_gap_ms": _summary(leading_gap_ms),
        "window_trailing_gap_ms": _summary(trailing_gap_ms),
        "ticks_per_minute_x1000": _summary(ticks_per_minute_milli),
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "wp05_fresh_holdout_opened": False,
        "shared_certification_holdout_opened": False,
        "shared_methodology_authority": False,
        "shared_sizing_authority": False,
        "shared_risk_authority": False,
        "shared_order_authority": False,
        "shared_execution_authority": False,
    }
