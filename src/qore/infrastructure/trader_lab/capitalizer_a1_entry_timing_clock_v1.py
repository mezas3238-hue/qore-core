"""Exact pure A2 scalper NY/DST clock + PARTIAL H1 price position functions.

Copied from A2 methodological diagnostics without its POST-HOC MFE/MAE
economic modules. These functions consult only completed M1 bars and the
published New York session clock, so they can run inside A1 cognition.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)

NY = ZoneInfo("America/New_York")


def session_end_at(moment: datetime, session: str) -> datetime:
    """Fixed NY research-session clock, DST-aware, NOT a future price."""

    if moment.utcoffset() is None:
        raise ValueError("session clock needs aware datetime")
    local = moment.astimezone(NY)
    wall = local.timetz().replace(tzinfo=None)
    if session == "ASIA":
        if wall >= time(20):
            end_date = local.date() + timedelta(days=1)
        elif wall < time(2):
            end_date = local.date()
        else:
            raise ValueError("timestamp outside ASIA research session")
        end_time = time(2)
    elif session == "LONDON":
        if not time(2) <= wall < time(8, 30):
            raise ValueError("timestamp outside LONDON research session")
        end_date, end_time = local.date(), time(8, 30)
    elif session == "NEW_YORK":
        if not time(8, 30) <= wall < time(16):
            raise ValueError("timestamp outside NY research session")
        end_date, end_time = local.date(), time(16)
    else:
        raise ValueError("unknown research session")
    end = datetime.combine(end_date, end_time, tzinfo=NY)
    if end <= moment:
        raise ValueError("session runway must be positive")
    return end


def h1_observed_position(
    bars: tuple[CapitalizerM1Bar, ...],
    at: datetime,
    entry: Decimal,
    direction: str,
) -> tuple[Decimal | None, Decimal, int]:
    """Directional price rank in H1 seen so far, never terminal high/low."""

    h1_open = at.replace(minute=0, second=0, microsecond=0)
    elapsed = Decimal(str((at - h1_open).total_seconds())) / Decimal(3600)
    if not Decimal(0) <= elapsed < 1:
        raise ValueError("bad H1 clock phase")
    observed = tuple(
        bar for bar in bars
        if h1_open <= bar.opened_at and bar.closed_at <= at
    )
    if not observed:
        return None, elapsed, 0
    low = min(x.low for x in observed)
    high = max(x.high for x in observed)
    if entry < low or entry > high:
        raise ValueError("entry lies outside the as-of observed H1 range")
    if high == low:
        return None, elapsed, len(observed)
    if direction == "LONG":
        rank = (entry - low) / (high - low)
    elif direction == "SHORT":
        rank = (high - entry) / (high - low)
    else:
        raise ValueError("unsupported H1 bias direction")
    if not 0 <= rank <= 1:
        raise ValueError("invalid H1 observed range fraction")
    return rank, elapsed, len(observed)
