"""M1-only execution timeframe for the ICT Silver Bullet cleanroom trader.

This module is the PRIMARY source of entry-shape evidence. M15/H1/H4 are
context-only, never the triggering FVG or the structural execution chart.
No old VT31 imports, no generated orders, no broker fills.

All-three-M1-in-hour is a QORE research formality, not an unequivocally
quoted rule from ICT's 2023 lecture. CE is a research candidate, not the
only price ICT ever described inside a FVG.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Final, Literal

from .contracts import M1Bar, SessionId, Side, utc, window_bounds

ENTRY_TIMEFRAME: Final[Literal["M1"]] = "M1"
STRUCTURE_TIMEFRAME: Final[Literal["M1"]] = "M1"
FVG_TIMEFRAME: Final[Literal["M1"]] = "M1"
HTF_CONTEXT_ONLY: Final[tuple[str, ...]] = ("M15", "H1", "H4")
M1_BAR_SECONDS: Final[int] = 60


@dataclass(frozen=True, slots=True)
class ClosedM1Fvg:
    """Three exact closed M1 candles; no tick fill or extra timeframe."""

    session: SessionId
    side: Side
    first_m1_opened_at: datetime
    middle_m1_opened_at: datetime
    third_m1_opened_at: datetime
    confirmed_at: datetime
    zone_low: Decimal
    zone_high: Decimal
    consequent_encroachment: Decimal
    entry_timeframe: Literal["M1"] = "M1"
    source_kind: str = "THREE_CONTIGUOUS_CLOSED_M1"

    def __post_init__(self) -> None:
        if not self.zone_low < self.consequent_encroachment < self.zone_high:
            raise ValueError("nonexistent 3-M1 price delivery imbalance")
        start, end = window_bounds(self.confirmed_at, self.session)
        if not start <= utc(self.first_m1_opened_at):
            raise ValueError("first M1 candle outside strict source hour")
        if not utc(self.first_m1_opened_at) < utc(self.middle_m1_opened_at):
            raise ValueError("nonmonotonic first and middle M1")
        if not utc(self.middle_m1_opened_at) < utc(self.third_m1_opened_at):
            raise ValueError("nonmonotonic middle and third M1")
        if utc(self.confirmed_at) > end:
            raise ValueError("third M1 confirmed after ICT source hour")
        if utc(self.confirmed_at) <= utc(self.third_m1_opened_at):
            raise ValueError("unclosed third M1")


def confirmed_m1_fvg(
    *,
    session: SessionId,
    first: M1Bar,
    middle: M1Bar,
    third: M1Bar,
) -> ClosedM1Fvg | None:
    """Observe only a completed strict three-candle M1 directional gap.

    A returned FVG still needs independently causal DOL, MSS, and a
    suitable entry zone. This function NEVER infers a trade.
    """
    if not isinstance(session, SessionId):
        raise ValueError("only original ICT source windows")
    if not all(isinstance(x, M1Bar) for x in (first, middle, third)):
        raise TypeError("Silver Bullet execution bars MUST be M1Bar")
    if (
        utc(first.closed_at) != utc(middle.opened_at)
        or utc(middle.closed_at) != utc(third.opened_at)
    ):
        raise ValueError("missing M1 or invalid 3-candle source order")
    start, end = window_bounds(first.opened_at, session)
    if utc(first.opened_at) < start or utc(third.closed_at) > end:
        # Research policy: require all three complete M1 candles within
        # the ORIGINAL time-based source hour in New York local time.
        return None

    bull = third.low > first.high
    bear = third.high < first.low
    if not bull and not bear:
        return None
    side = Side.LONG if bull else Side.SHORT
    lower, upper = (
        (first.high, third.low) if bull else (third.high, first.low)
    )
    midpoint = (lower + upper) / Decimal(2)
    return ClosedM1Fvg(
        session=session,
        side=side,
        first_m1_opened_at=utc(first.opened_at),
        middle_m1_opened_at=utc(middle.opened_at),
        third_m1_opened_at=utc(third.opened_at),
        confirmed_at=utc(third.closed_at),
        zone_low=lower,
        zone_high=upper,
        consequent_encroachment=midpoint,
    )


def required_timeframe_contract() -> dict[str, object]:
    """Machine-readable handshake for both architects and Trader Lab."""
    return {
        "trader_id": "VT31",
        "instrument": "NAS100",
        "session_models": ("LONDON", "NEW_YORK"),
        "source_window_count": 3,
        "primary_execution_timeframe": ENTRY_TIMEFRAME,
        "mss_and_displacement_execution_timeframe": STRUCTURE_TIMEFRAME,
        "fvg_creation_timeframe": FVG_TIMEFRAME,
        "source_candle_size_seconds": M1_BAR_SECONDS,
        "m1_fvg_confirmation": "AT_THIRD_M1_CLOSE",
        "htf_context_only": HTF_CONTEXT_ONLY,
        "m15_h1_h4_are_entry_triggers": False,
        "source_requires_cognition_for_orders": True,
        "intrabar_m1_touch_proves_broker_fill": False,
        "broker_bid_ask_tick_or_ack_needed_for_fill": True,
        "exact_stop_and_ce_are_research_policy_not_universal_ict": True,
        "live_authorized": False,
    }
