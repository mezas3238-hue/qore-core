"""Canonical temporal predicates shared by QORE contracts."""
from __future__ import annotations

from datetime import UTC, datetime


def is_timezone_aware_datetime(value: object) -> bool:
    """Return whether ``value`` is a datetime carrying an effective UTC offset.

    QORE requires temporal contract values to be timezone-aware. This predicate
    deliberately accepts any valid aware offset and performs no silent timezone
    conversion or normalization.
    """

    return (
        isinstance(value, datetime)
        and value.tzinfo is not None
        and value.utcoffset() is not None
    )


def canonical_instant(value: datetime) -> str:
    """Return deterministic UTC microsecond instant material."""
    if not isinstance(value, datetime):
        raise TypeError("canonical instant requires a datetime")
    if not is_timezone_aware_datetime(value):
        raise ValueError(
            "canonical instant requires a timezone-aware datetime"
        )
    return value.astimezone(UTC).isoformat(timespec="microseconds")
