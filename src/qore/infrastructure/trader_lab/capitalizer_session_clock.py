"""DST-aware research session segmentation for QORE Capitalizer.

These are broad Atlas-compatible research buckets, not ICT killzones and not proof of edge.
They exist so every market is segmented consistently across the consumed ten-year corpus.
"""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession


NEW_YORK = ZoneInfo("America/New_York")


def capitalizer_session_at(moment: datetime) -> CapitalizerSession | None:
    """Map an aware instant to the broad research session bucket."""

    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("session classification requires timezone-aware datetime")
    wall = moment.astimezone(NEW_YORK).timetz().replace(tzinfo=None)
    if wall >= time(20, 0) or wall < time(2, 0):
        return CapitalizerSession.ASIA
    if time(2, 0) <= wall < time(8, 30):
        return CapitalizerSession.LONDON
    if time(8, 30) <= wall < time(16, 0):
        return CapitalizerSession.NEW_YORK
    return None
