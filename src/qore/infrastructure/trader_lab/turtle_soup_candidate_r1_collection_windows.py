"""Fail-closed overlapping request windows for Turtle Soup R1 market evidence."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError


def build_overlapped_collection_windows(
    *,
    opened_at: datetime,
    checked_at: datetime,
    chunk_span: timedelta,
    bar_span: timedelta,
) -> tuple[tuple[datetime, datetime], ...]:
    """Build bounded windows that overlap by one complete source bar.

    Historical trendbar collectors reject a bar when its close lies after the
    current request boundary.  Starting the next request exactly at that
    boundary would then lose a bar that opened before the boundary and closed
    after it.  Adjacent windows therefore overlap by exactly one bar span; the
    collectors deduplicate returned bars by ``opened_at`` and reject any
    contradictory duplicate.
    """

    for field_name, value in (("opened_at", opened_at), ("checked_at", checked_at)):
        if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
            raise CTraderDemoLabProbeError(f"{field_name} must be timezone-aware")
    if type(chunk_span) is not timedelta or chunk_span <= timedelta(0):
        raise CTraderDemoLabProbeError("chunk_span must be a positive timedelta")
    if type(bar_span) is not timedelta or bar_span <= timedelta(0):
        raise CTraderDemoLabProbeError("bar_span must be a positive timedelta")
    if bar_span >= chunk_span:
        raise CTraderDemoLabProbeError("bar_span must be smaller than chunk_span")

    opened = opened_at.astimezone(UTC)
    checked = checked_at.astimezone(UTC)
    if opened >= checked:
        raise CTraderDemoLabProbeError("opened_at must predate checked_at")

    windows: list[tuple[datetime, datetime]] = []
    cursor = opened
    while cursor < checked:
        window_end = min(cursor + chunk_span, checked)
        windows.append((cursor, window_end))
        if window_end == checked:
            break
        next_cursor = window_end - bar_span
        if next_cursor <= cursor:
            raise CTraderDemoLabProbeError("overlapped collection window failed to advance")
        cursor = next_cursor
    return tuple(windows)
