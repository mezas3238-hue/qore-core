"""Zero-legacy DTO contract shared by OPS and COG architects.

No imports of old VT31/TTrades/COMP scripts. Research-only, pure stdlib.
Every market fact is timestamped so the replay cannot ask the future.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")
MIN_INDEX_POINTS = Decimal("10")


class SessionId(StrEnum):
    LONDON = "VT31_LONDON"
    NY_AM = "VT31_NY_AM"
    NY_PM = "VT31_NY_PM"


class Side(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class MethodologyDecision(StrEnum):
    AWAIT_COGNITION = "AWAIT_COGNITION"
    AWAIT_FVG = "AWAIT_FVG"
    RESEARCH_PENDING_CE = "RESEARCH_PENDING_CE"
    RESEARCH_TOUCH_NOT_FILL = "RESEARCH_TOUCH_NOT_FILL"
    AMBIGUOUS_PRICE_PATH = "AMBIGUOUS_PRICE_PATH"
    SOURCE_INVALIDATED = "SOURCE_INVALIDATED"
    WINDOW_EXPIRED = "WINDOW_EXPIRED"


def utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware datetime required")
    return value.astimezone(UTC)


def price(value: Decimal) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise ValueError("finite positive Decimal index-price required")
    return value


def window_bounds(local_day_at: datetime, session: SessionId) -> tuple[datetime, datetime]:
    """All original Silver Bullet windows are based on US/New York DST."""
    if not isinstance(session, SessionId):
        raise ValueError("source-session ID required")
    d = utc(local_day_at).astimezone(NEW_YORK).date()
    h = {SessionId.LONDON: 3, SessionId.NY_AM: 10, SessionId.NY_PM: 14}[session]
    first = datetime.combine(d, time(h), tzinfo=NEW_YORK).astimezone(UTC)
    last = datetime.combine(d, time(h + 1), tzinfo=NEW_YORK).astimezone(UTC)
    if last - first != timedelta(hours=1):
        raise ValueError("a real 60-minute source window required")
    return first, last


@dataclass(frozen=True, slots=True)
class M1Bar:
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def __post_init__(self) -> None:
        if utc(self.closed_at) - utc(self.opened_at) != timedelta(minutes=1):
            raise ValueError("exact closed M1 required")
        if utc(self.opened_at).second or utc(self.opened_at).microsecond:
            raise ValueError("minute aligned M1 required")
        o, h, lo, c = (price(self.open), price(self.high),
                      price(self.low), price(self.close))
        if lo > min(o, c) or h < max(o, c):
            raise ValueError("M1 OHLC price bounds invalid")


@dataclass(frozen=True, slots=True)
class CognitiveDecision:
    """COG-owned producer payload: independent source, bias, level and MSS.

    `observed_at` is the time at which cognition actually knew its thesis,
    not a historical terminal-market timestamp. Never backdate its receipt.
    """
    session: SessionId
    side: Side
    observed_at: datetime
    draw_target: Decimal
    draw_family: str
    draw_level_observed_at: datetime
    structure_level: Decimal
    structure_level_confirmed_at: datetime
    structure_break_confirmed_at: datetime
    source_provenance: str
    cognitive_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.session, SessionId) or not isinstance(self.side, Side):
            raise ValueError("explicit session and side required")
        observed = utc(self.observed_at)
        for stamp in (self.draw_level_observed_at,
                      self.structure_level_confirmed_at,
                      self.structure_break_confirmed_at):
            if utc(stamp) > observed:
                raise ValueError("cognition must not include future source facts")
        if utc(self.structure_level_confirmed_at) > utc(self.structure_break_confirmed_at):
            raise ValueError("MSS swing pivot must be known before swing break")
        price(self.draw_target)
        price(self.structure_level)
        if not self.draw_family or not self.source_provenance or not self.cognitive_version:
            raise ValueError("cognitive lineage and draw family required")


@dataclass(frozen=True, slots=True)
class FvgCandidate:
    session: SessionId
    side: Side
    formed_at: datetime
    first_candle_open: datetime
    lower: Decimal
    upper: Decimal
    consequent_encroachment: Decimal
    target_price: Decimal
    projected_index_points: Decimal
    observed_context_at: datetime

    def __post_init__(self) -> None:
        if not price(self.lower) < price(self.consequent_encroachment) < price(self.upper):
            raise ValueError("no valid directional FVG geometry")
        price(self.target_price)
        if self.projected_index_points < MIN_INDEX_POINTS:
            raise ValueError("target cannot provide source research framework")
        if utc(self.observed_context_at) > utc(self.formed_at):
            raise ValueError("post-formation cognition is lookahead")
