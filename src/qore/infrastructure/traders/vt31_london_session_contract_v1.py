"""VT31_LONDON experimental operating-session clock: causal pure-edge V0.

Time contract only. Does NOT copy NY clock, calculate entries, authorize trading,
override shared cognition, certify London, or grant LIVE/real-capital access.

Research hypothesis (Europe/London local):
  07:00..08:00 = complete reference; 08:00..09:00 = execution;
  09:00 = final pending-entry expiry; extant positions remain under canonical
  position management beyond 09:00 until a causal methodology exit.

All moments are timezone-aware and compared on UTC instants. UK DST is
handled through IANA Europe/London, never hardcoded UTC offsets.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

SESSION_MODEL_ID = "VT31_LONDON"
LONDON = ZoneInfo("Europe/London")
REFERENCE_START = time(7, 0)
EXECUTION_START = time(8, 0)
PENDING_CUTOFF = time(9, 0)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("aware timestamp required")
    return value.astimezone(UTC)


def _local_boundary(day: date, local_time: time) -> datetime:
    return datetime.combine(day, local_time, tzinfo=LONDON).astimezone(UTC)


@dataclass(frozen=True, slots=True)
class LondonSessionWindow:
    local_day: date
    reference_start_utc: datetime
    execution_start_utc: datetime
    entry_cutoff_utc: datetime

    @classmethod
    def for_date(cls, day: date) -> "LondonSessionWindow":
        ref = _local_boundary(day, REFERENCE_START)
        execute = _local_boundary(day, EXECUTION_START)
        end = _local_boundary(day, PENDING_CUTOFF)
        if execute - ref != timedelta(hours=1):
            raise ValueError("reference must be one real closed hour")
        if end - execute != timedelta(hours=1):
            raise ValueError("execution must be one real causal hour")
        return cls(day, ref, execute, end)

    @classmethod
    def for_utc(cls, timestamp: datetime) -> "LondonSessionWindow":
        return cls.for_date(_utc(timestamp).astimezone(LONDON).date())

    @property
    def session_model_id(self) -> str:
        return SESSION_MODEL_ID

    def phase(self, timestamp: datetime) -> str:
        when = _utc(timestamp)
        if when < self.reference_start_utc:
            return "BEFORE_REFERENCE"
        if when < self.execution_start_utc:
            return "REFERENCE"
        if when < self.entry_cutoff_utc:
            return "EXECUTION"
        return "AFTER_ENTRY_CUTOFF"

    def reference_complete(
        self,
        bars: tuple[tuple[datetime, datetime], ...],
    ) -> bool:
        """Require 60 consecutive closed M1 candles in reference, no partials."""
        if len(bars) != 60:
            return False
        for minute, (opened_at, closed_at) in enumerate(bars):
            expected_open = self.reference_start_utc + timedelta(minutes=minute)
            if _utc(opened_at) != expected_open:
                return False
            if _utc(closed_at) != expected_open + timedelta(minutes=1):
                return False
        return True

    def prospective_entry_time_is_causal(
        self,
        *,
        as_of: datetime,
        last_source_bar_close: datetime,
        thesis_confirmed_at: datetime,
        prospective_fill_open: datetime,
    ) -> bool:
        """Only the physical clock/readiness surface; not entry-policy authority.

        All observations used to accept a prospective fill must be closed by
        as_of; a fill can occur at or after as_of and inside London execution.
        Requires confirmation no earlier than the completed reference.
        """
        observed = _utc(as_of)
        source_close = _utc(last_source_bar_close)
        confirmed = _utc(thesis_confirmed_at)
        fill = _utc(prospective_fill_open)
        return (
            self.execution_start_utc <= confirmed <= observed <= fill
            and self.execution_start_utc <= fill < self.entry_cutoff_utc
            and source_close <= observed
            and observed <= self.entry_cutoff_utc
        )


def self_test() -> None:
    # UK moves clocks on dates DIFFERENT from US, so NY-based UTC shifts
    # cannot be used to infer a real Europe/London session.
    winter = LondonSessionWindow.for_date(date(2026, 3, 27))
    summer = LondonSessionWindow.for_date(date(2026, 3, 30))
    fall_bst = LondonSessionWindow.for_date(date(2026, 10, 23))
    fall_gmt = LondonSessionWindow.for_date(date(2026, 10, 26))
    assert winter.reference_start_utc.hour == 7
    assert summer.reference_start_utc.hour == 6
    assert fall_bst.reference_start_utc.hour == 6
    assert fall_gmt.reference_start_utc.hour == 7
    assert winter.phase(winter.reference_start_utc) == "REFERENCE"
    assert winter.phase(winter.execution_start_utc) == "EXECUTION"
    assert winter.phase(winter.entry_cutoff_utc) == "AFTER_ENTRY_CUTOFF"

    bars = tuple(
        (summer.reference_start_utc + timedelta(minutes=i),
         summer.reference_start_utc + timedelta(minutes=i + 1))
        for i in range(60)
    )
    assert summer.reference_complete(bars)
    assert not summer.reference_complete(bars[:-1])
    assert not summer.reference_complete(bars[:-1] + (bars[-2],))

    source_closed = summer.execution_start_utc + timedelta(minutes=10)
    next_open = source_closed + timedelta(minutes=1)
    assert summer.prospective_entry_time_is_causal(
        as_of=source_closed,
        last_source_bar_close=source_closed,
        thesis_confirmed_at=source_closed,
        prospective_fill_open=next_open,
    )
    assert not summer.prospective_entry_time_is_causal(
        as_of=source_closed,
        last_source_bar_close=next_open,  # unclosed future bar
        thesis_confirmed_at=source_closed,
        prospective_fill_open=next_open,
    )
    assert not summer.prospective_entry_time_is_causal(
        as_of=source_closed,
        last_source_bar_close=source_closed,
        thesis_confirmed_at=source_closed,
        prospective_fill_open=summer.entry_cutoff_utc,
    )
    try:
        LondonSessionWindow.for_utc(datetime(2026, 4, 2))
    except ValueError:
        pass
    else:
        raise AssertionError("naive timestamp allowed")


if __name__ == "__main__":
    self_test()
    print("VT31_LONDON causal clock self-test: PASS")
