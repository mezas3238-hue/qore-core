"""Audit causal BID/ASK observability at frozen WP-05 V12 R8 anchors."""

from __future__ import annotations

import argparse
import gzip
import json
from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.active_perception_v12_anchor_observability import (
    V12AnchorQuoteState,
    summarize_v12_anchor_observability,
    v12_anchor_observability_digest,
)
from qore.infrastructure.core_stack_v2.active_perception_v12_source_anchors import (
    EXPECTED_ACQUISITION_MANIFEST_SHA256,
    EXPECTED_SOURCE_COUNT,
    SOURCE_ANCHOR_IDENTITY,
    V12SourceAnchorManifest,
)

RAW_SCHEMA = "qore.shared.wp05.v12.historical_quote_side_shard.v2"


class V12AnchorObservabilityError(RuntimeError):
    """Frozen source-only anchor observability audit failed closed."""


@dataclass(frozen=True, slots=True)
class _Page:
    path: Path
    side: str
    window_index: int
    page_index: int
    request_from_at: datetime
    request_to_at: datetime


def _aware(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise V12AnchorObservabilityError(f"{field} must be string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise V12AnchorObservabilityError(f"{field} invalid ISO-8601") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise V12AnchorObservabilityError(f"{field} must be timezone-aware")
    return parsed.astimezone(UTC)


def _read_page_header(path: Path) -> _Page:
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            first = json.loads(handle.readline())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V12AnchorObservabilityError(f"cannot read raw page header: {path}") from error
    if not isinstance(first, dict) or set(first) != {"header"}:
        raise V12AnchorObservabilityError("raw page must start with header")
    header_raw = first["header"]
    if not isinstance(header_raw, dict):
        raise V12AnchorObservabilityError("raw page header must be object")
    header = cast(dict[str, Any], header_raw)
    if header.get("schema") != RAW_SCHEMA:
        raise V12AnchorObservabilityError("raw page schema mismatch")
    side_raw = header.get("quote_side")
    if not isinstance(side_raw, str) or side_raw.upper() not in {"BID", "ASK"}:
        raise V12AnchorObservabilityError("raw page quote side invalid")
    window_index = header.get("window_index")
    page_index = header.get("page_index")
    if type(window_index) is not int or window_index < 0:
        raise V12AnchorObservabilityError("raw page window index invalid")
    if type(page_index) is not int or page_index < 0:
        raise V12AnchorObservabilityError("raw page page index invalid")
    return _Page(
        path=path,
        side=side_raw.upper(),
        window_index=window_index,
        page_index=page_index,
        request_from_at=_aware(header.get("request_from_at"), field="request_from_at"),
        request_to_at=_aware(header.get("request_to_at"), field="request_to_at"),
    )


def _load_anchor_manifest(path: Path) -> tuple[tuple[datetime, ...], str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise V12AnchorObservabilityError("source anchor manifest must be object")
    payload = cast(dict[str, Any], raw)
    if payload.get("identity") != SOURCE_ANCHOR_IDENTITY:
        raise V12AnchorObservabilityError("source anchor identity mismatch")
    if payload.get("acquisition_manifest_sha256") != (
        EXPECTED_ACQUISITION_MANIFEST_SHA256
    ):
        raise V12AnchorObservabilityError("source anchor acquisition binding drift")
    values = payload.get("source_times")
    if not isinstance(values, list) or len(values) != EXPECTED_SOURCE_COUNT:
        raise V12AnchorObservabilityError("source anchor population mismatch")
    anchors = tuple(_aware(value, field="source_time") for value in values)
    manifest = V12SourceAnchorManifest(
        partition="r8",
        acquisition_manifest_sha256=EXPECTED_ACQUISITION_MANIFEST_SHA256,
        source_times=anchors,
    )
    stored_digest = payload.get("source_anchor_sha256")
    if stored_digest != manifest.digest_sha256:
        raise V12AnchorObservabilityError("source anchor digest mismatch")
    return anchors, manifest.digest_sha256


def _discover_pages(
    raw_root: Path,
) -> tuple[
    dict[tuple[int, str], list[_Page]],
    dict[int, tuple[datetime, datetime]],
]:
    grouped: dict[tuple[int, str], list[_Page]] = defaultdict(list)
    bounds: dict[int, tuple[datetime, datetime]] = {}
    paths = sorted(raw_root.rglob("*.jsonl.gz"))
    if not paths:
        raise V12AnchorObservabilityError("no raw provider pages found")
    for path in paths:
        page = _read_page_header(path)
        grouped[(page.window_index, page.side)].append(page)
        current = bounds.get(page.window_index)
        if current is None:
            bounds[page.window_index] = (
                page.request_from_at,
                page.request_to_at,
            )
        else:
            bounds[page.window_index] = (
                min(current[0], page.request_from_at),
                max(current[1], page.request_to_at),
            )
    return grouped, bounds


def _assign_anchors_to_windows(
    anchors: tuple[datetime, ...],
    bounds: dict[int, tuple[datetime, datetime]],
) -> dict[int, list[tuple[int, datetime]]]:
    intervals = sorted(
        (
            start,
            end,
            window_index,
        )
        for window_index, (start, end) in bounds.items()
    )
    for left, right in zip(intervals, intervals[1:], strict=False):
        if right[0] <= left[1]:
            raise V12AnchorObservabilityError("raw acquisition windows overlap")
    assigned: dict[int, list[tuple[int, datetime]]] = defaultdict(list)
    cursor = 0
    for anchor_index, anchor in enumerate(anchors):
        while cursor < len(intervals) and anchor > intervals[cursor][1]:
            cursor += 1
        if cursor >= len(intervals):
            raise V12AnchorObservabilityError("source anchor escaped raw window range")
        start, end, window_index = intervals[cursor]
        if not start <= anchor <= end:
            raise V12AnchorObservabilityError("source anchor is not covered by raw window")
        assigned[window_index].append((anchor_index, anchor))
    return assigned


def _load_side_events(
    pages: list[_Page],
) -> list[tuple[datetime, int, int, int]]:
    events: list[tuple[datetime, int, int, int]] = []
    for page in pages:
        try:
            with gzip.open(page.path, "rt", encoding="utf-8") as handle:
                first = handle.readline()
                if not first:
                    raise V12AnchorObservabilityError("raw page is empty")
                for row_ordinal, encoded in enumerate(handle):
                    item = json.loads(encoded)
                    if not isinstance(item, dict) or set(item) != {"tick"}:
                        raise V12AnchorObservabilityError("raw page contains non-tick row")
                    tick_raw = item["tick"]
                    if not isinstance(tick_raw, dict):
                        raise V12AnchorObservabilityError("raw tick must be object")
                    tick = cast(dict[str, Any], tick_raw)
                    event_at = _aware(
                        tick.get("provider_event_at"),
                        field="provider_event_at",
                    )
                    relative_price = tick.get("relative_price")
                    if type(relative_price) is not int or relative_price <= 0:
                        raise V12AnchorObservabilityError("raw relative price invalid")
                    events.append(
                        (
                            event_at,
                            -page.page_index,
                            row_ordinal,
                            relative_price,
                        )
                    )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise V12AnchorObservabilityError(
                f"cannot decode raw provider page: {page.path}"
            ) from error
    events.sort(key=lambda item: (item[0], item[1], item[2]))
    return events


def _latest_states(
    events: list[tuple[datetime, int, int, int]],
    anchors: list[tuple[int, datetime]],
) -> dict[int, tuple[int, int] | None]:
    result: dict[int, tuple[int, int] | None] = {}
    if not events:
        for anchor_index, _anchor in anchors:
            result[anchor_index] = None
        return result
    event_times = [item[0] for item in events]
    for anchor_index, anchor in anchors:
        position = bisect_right(event_times, anchor) - 1
        if position < 0:
            result[anchor_index] = None
            continue
        event_at, _page_order, _row_order, price = events[position]
        age_ms = int((anchor - event_at).total_seconds() * 1000)
        if age_ms < 0:
            raise V12AnchorObservabilityError("future provider event escaped bisect")
        result[anchor_index] = (age_ms, price)
    return result


def run(
    *,
    raw_root: Path,
    anchor_manifest_path: Path,
    expected_global_dataset_sha256: str,
) -> dict[str, object]:
    anchors, anchor_digest = _load_anchor_manifest(anchor_manifest_path)
    grouped, bounds = _discover_pages(raw_root)
    assigned = _assign_anchors_to_windows(anchors, bounds)

    states: list[V12AnchorQuoteState | None] = [None] * len(anchors)
    for window_index, window_anchors in sorted(assigned.items()):
        bid = _latest_states(
            _load_side_events(grouped.get((window_index, "BID"), [])),
            window_anchors,
        )
        ask = _latest_states(
            _load_side_events(grouped.get((window_index, "ASK"), [])),
            window_anchors,
        )
        for anchor_index, evaluation_at in window_anchors:
            bid_state = bid[anchor_index]
            ask_state = ask[anchor_index]
            states[anchor_index] = V12AnchorQuoteState(
                evaluation_at=evaluation_at,
                bid_age_ms=None if bid_state is None else bid_state[0],
                ask_age_ms=None if ask_state is None else ask_state[0],
                bid_relative_price=None if bid_state is None else bid_state[1],
                ask_relative_price=None if ask_state is None else ask_state[1],
            )

    if any(item is None for item in states):
        raise V12AnchorObservabilityError("not every source anchor was evaluated")
    frozen_states = tuple(item for item in states if item is not None)
    report = summarize_v12_anchor_observability(frozen_states)
    report.update(
        {
            "source_anchor_sha256": anchor_digest,
            "global_dataset_sha256": expected_global_dataset_sha256,
        }
    )
    report["anchor_observability_sha256"] = v12_anchor_observability_digest(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--anchor-manifest", type=Path, required=True)
    parser.add_argument("--expected-global-dataset-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = run(
        raw_root=args.raw_root,
        anchor_manifest_path=args.anchor_manifest,
        expected_global_dataset_sha256=args.expected_global_dataset_sha256,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "anchor_count": report["anchor_count"],
                "selected_staleness_limit_ms": report[
                    "selected_staleness_limit_ms"
                ],
                "bid_age_ms": report["bid_age_ms"],
                "ask_age_ms": report["ask_age_ms"],
                "max_side_age_ms": report["max_side_age_ms"],
                "crossed_causal_quote_count": report[
                    "crossed_causal_quote_count"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
