"""Primary-ICT Silver Bullet London clock (2023 lesson, source anchored).

Primary lesson by The Inner Circle Trader:
https://www.youtube.com/watch?v=tRq1hyGGtl4
London Silver Bullet forms 03:00-04:00 *America/New_York*, regardless
of the local civil time in London (UK/US DST mismatch matters).

This module checks the clock and causal timestamps only. It does NOT assert
a preceding fixed H1 range is a universal ICT entry rule, nor does it
authorize setups, entries, portfolio exposures, certifications or LIVE.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

SESSION_MODEL_ID = "VT31_LONDON"
SOURCE_VIDEO = "https://www.youtube.com/watch?v=tRq1hyGGtl4"
NEW_YORK = ZoneInfo("America/New_York")
LONDON = ZoneInfo("Europe/London")

# Only these time windows are attested by the 2023 ICT lesson.
SILVER_BULLET_SOURCE_HOURS_NY = {
    "VT31_LONDON": (3, 4),
    "VT31_NY_AM": (10, 11),
    "VT31_NY_PM": (14, 15),
}


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("aware timestamp required")
    return value.astimezone(UTC)


def _ny_boundary(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour, 0), tzinfo=NEW_YORK).astimezone(UTC)


@dataclass(frozen=True, slots=True)
class LondonSessionWindow:
    """03:00-04:00 New York Silver Bullet, using the NY civil business day.

    The preceding 02:00-03:00 NY hour is ONLY OPTIONAL CONTEXT. ICT's
    Silver Bullet lesson does not require a 60-bar preceding range or a
    mandatory raid of that range. Calling reference_complete never
    authorizes a trade; the full methodology/source producers must decide.
    """

    ny_date: date
    reference_start_utc: datetime
    execution_start_utc: datetime
    entry_cutoff_utc: datetime

    @classmethod
    def for_date(cls, day: date) -> "LondonSessionWindow":
        ref = _ny_boundary(day, 2)
        start = _ny_boundary(day, 3)
        end = _ny_boundary(day, 4)
        if start - ref != timedelta(hours=1):
            raise ValueError("context hour is not a physical hour")
        if end - start != timedelta(hours=1):
            raise ValueError("ICT Silver Bullet window must be one real hour")
        return cls(day, ref, start, end)

    @classmethod
    def for_utc(cls, instant: datetime) -> "LondonSessionWindow":
        return cls.for_date(_utc(instant).astimezone(NEW_YORK).date())

    @property
    def session_model_id(self) -> str:
        return SESSION_MODEL_ID

    def london_wall_clock(self) -> dict[str, str]:
        """Observable civil clock may be 07:00 or 08:00 in London."""
        start = self.execution_start_utc.astimezone(LONDON)
        end = self.entry_cutoff_utc.astimezone(LONDON)
        return {
            "start_local": start.isoformat(),
            "end_local": end.isoformat(),
            "source_timezone": "America/New_York",
            "display_timezone": "Europe/London",
        }

    def phase(self, instant: datetime) -> str:
        when = _utc(instant)
        if when < self.reference_start_utc:
            return "BEFORE_CONTEXT"
        if when < self.execution_start_utc:
            return "OPTIONAL_CONTEXT"
        if when < self.entry_cutoff_utc:
            return "SILVER_BULLET_FORMATION_AND_ENTRY"
        return "AFTER_SILVER_BULLET_ENTRY_CUTOFF"

    def reference_complete(
        self, bars: tuple[tuple[datetime, datetime], ...]
    ) -> bool:
        """Optional preceding hour observational completeness, NOT a veto."""
        if len(bars) != 60:
            return False
        return all(
            _utc(opened) == self.reference_start_utc + timedelta(minutes=i)
            and _utc(closed) == self.reference_start_utc + timedelta(minutes=i + 1)
            for i, (opened, closed) in enumerate(bars)
        )

    def prospective_entry_time_is_causal(
        self,
        *,
        as_of: datetime,
        last_source_bar_close: datetime,
        thesis_confirmed_at: datetime,
        prospective_fill_open: datetime,
    ) -> bool:
        """Prevent a same-bar/future fill and late gap being called Silver Bullet.

        The time gate is necessary but INSUFFICIENT: a valid ICT FVG formed
        during the window, causal DOL and adequate price delivery framework
        must also be proven by an independent methodology producer.
        """
        observed = _utc(as_of)
        source_close = _utc(last_source_bar_close)
        confirmed = _utc(thesis_confirmed_at)
        fill = _utc(prospective_fill_open)
        return (
            self.execution_start_utc <= confirmed <= observed <= fill
            and self.execution_start_utc <= source_close <= observed
            and self.execution_start_utc <= fill < self.entry_cutoff_utc
        )


def source_window_for_utc(instant: datetime, *, session_model_id: str) -> tuple[datetime, datetime]:
    """All three actual source-lesson windows, strictly as America/New_York."""
    if session_model_id not in SILVER_BULLET_SOURCE_HOURS_NY:
        raise ValueError("unsupported primary ICT source session")
    day = _utc(instant).astimezone(NEW_YORK).date()
    start, end = SILVER_BULLET_SOURCE_HOURS_NY[session_model_id]
    return _ny_boundary(day, start), _ny_boundary(day, end)


def self_test() -> None:
    # UK and USA change daylight saving on different dates.
    for day, utc_hour, london_hour in (
        (date(2026, 3, 2), 8, 8),
        (date(2026, 3, 10), 7, 7),
        (date(2026, 3, 30), 7, 8),
        (date(2026, 10, 23), 7, 8),
        (date(2026, 10, 26), 7, 7),
        (date(2026, 11, 2), 8, 8),
    ):
        window = LondonSessionWindow.for_date(day)
        assert window.execution_start_utc.hour == utc_hour
        assert window.entry_cutoff_utc - window.execution_start_utc == timedelta(hours=1)
        assert window.execution_start_utc.astimezone(LONDON).hour == london_hour
        assert window.london_wall_clock()["source_timezone"] == "America/New_York"
    winter = LondonSessionWindow.for_date(date(2026, 3, 2))
    assert winter.phase(winter.reference_start_utc) == "OPTIONAL_CONTEXT"
    assert winter.phase(winter.execution_start_utc) == "SILVER_BULLET_FORMATION_AND_ENTRY"
    assert winter.phase(winter.entry_cutoff_utc) == "AFTER_SILVER_BULLET_ENTRY_CUTOFF"
    context = tuple(
        (winter.reference_start_utc + timedelta(minutes=i),
         winter.reference_start_utc + timedelta(minutes=i + 1))
        for i in range(60)
    )
    assert winter.reference_complete(context)
    assert not winter.reference_complete(context[:-1])
    event = winter.execution_start_utc + timedelta(minutes=10)
    assert winter.prospective_entry_time_is_causal(
        as_of=event, last_source_bar_close=event,
        thesis_confirmed_at=event, prospective_fill_open=event
    )
    assert not winter.prospective_entry_time_is_causal(
        as_of=event, last_source_bar_close=event + timedelta(minutes=1),
        thesis_confirmed_at=event, prospective_fill_open=event
    )
    assert not winter.prospective_entry_time_is_causal(
        as_of=event, last_source_bar_close=event,
        thesis_confirmed_at=event, prospective_fill_open=winter.entry_cutoff_utc
    )
    for model, (start, end) in SILVER_BULLET_SOURCE_HOURS_NY.items():
        got_start, got_end = source_window_for_utc(
            winter.execution_start_utc, session_model_id=model
        )
        assert got_start.astimezone(NEW_YORK).hour == start
        assert got_end.astimezone(NEW_YORK).hour == end
    try:
        LondonSessionWindow.for_utc(datetime(2026, 3, 2))
    except ValueError:
        pass
    else:
        raise AssertionError("naive timestamp accepted")


if __name__ == "__main__":
    self_test()
    print("ICT Silver Bullet London NY-clock DST and causal timing: PASS")
