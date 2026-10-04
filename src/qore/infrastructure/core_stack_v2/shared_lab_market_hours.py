"""Instrument-aware market-hours reality harness."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SessionState(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    HOLIDAY = "HOLIDAY"
    PARTIAL = "PARTIAL"
    EARLY_CLOSE = "EARLY_CLOSE"
    WEEKEND = "WEEKEND"
    SESSION_BREAK = "SESSION_BREAK"
    OVERNIGHT = "OVERNIGHT"


@dataclass(frozen=True, slots=True)
class MarketHoursReceipt:
    instrument_id: str
    expected_state: SessionState
    provider_reported_open: bool
    compatible: bool
    reason: str

    @property
    def passed(self) -> bool:
        return self.compatible


def assess_market_hours(instrument_id: str, expected_state: SessionState, provider_reported_open: bool) -> MarketHoursReceipt:
    should_be_open = expected_state in {SessionState.OPEN, SessionState.PARTIAL, SessionState.OVERNIGHT}
    compatible = provider_reported_open is should_be_open
    reason = "MATCH" if compatible else "PROVIDER_SESSION_CONTRADICTION"
    return MarketHoursReceipt(instrument_id, expected_state, provider_reported_open, compatible, reason)
