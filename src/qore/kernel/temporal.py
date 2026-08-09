"""Canonical temporal predicates shared by QORE contracts."""
from __future__ import annotations

from datetime import datetime


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
