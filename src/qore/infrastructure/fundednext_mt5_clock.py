"""Canonical FundedNext MT5 server-clock normalization.

MetaTrader 5 exposes FundedNext bar/tick timestamps using the broker server wall
clock encoded as an epoch-like integer. QORE converts that pseudo-UTC value back
through the FundedNext server timezone before any strategy consumes it.

Strategy clocks remain separate. VT08 and R34 use America/New_York after this
normalization, so both server DST and New York DST are handled by zoneinfo.
"""
from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

FUNDEDNEXT_SERVER_TZ = ZoneInfo("Europe/Helsinki")
NEW_YORK_TZ = ZoneInfo("America/New_York")


def normalise_fundednext_server_epoch(value: int) -> datetime:
    """Convert broker server wall-clock epoch encoding to a real UTC instant."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("FundedNext server timestamp must be int")
    pseudo_utc = datetime.fromtimestamp(value, tz=UTC).replace(tzinfo=None)
    return pseudo_utc.replace(tzinfo=FUNDEDNEXT_SERVER_TZ).astimezone(UTC)


def fundednext_server_epoch_to_new_york(value: int) -> datetime:
    """Convert broker server timestamp directly to DST-aware New York time."""
    return normalise_fundednext_server_epoch(value).astimezone(NEW_YORK_TZ)
