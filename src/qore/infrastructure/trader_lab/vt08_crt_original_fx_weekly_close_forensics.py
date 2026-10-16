"""R7 descriptive original-Atlas FX weekly-close/gap witness; never GM4 PASS.

Conventional New York 17:00 Friday is NOT authenticated cTrader broker schedule.
Uses only exact original M5 timestamps from the archived, SHA-verified Atlas.
No price fills, PnL, trades, sizing, rearm authority or synthetic bars.
"""
from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

SCHEMA = "qore.vt08.crt.original_fx_close_gap_forensic.r7.v1"
NY = ZoneInfo("America/New_York")
M5 = timedelta(minutes=5)
HOUR = timedelta(hours=1)
WEEK = timedelta(weeks=1)
WINDOW_WEEKS = 8
GAP_TARGETS: dict[CrtPureMarket, tuple[str, ...]] = {
    CrtPureMarket.AUDUSD: ("2025-04-25T21:00:00+00:00",),
    CrtPureMarket.USDJPY: (
        "2025-02-12T22:30:00+00:00",
        "2026-06-19T21:00:00+00:00",
    ),
}


def _stamp(value: str) -> datetime:
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("R7 requires timezone-aware source clock")
    return stamp.astimezone(UTC)


def _ny_friday_close(candidate: datetime) -> datetime:
    """NY Friday at 17:00 converted using IANA DST for that exact week."""
    ny = candidate.astimezone(NY)
    friday = ny.date() + timedelta(days=(4 - ny.weekday()))
    return datetime.combine(friday, time(17), NY).astimezone(UTC)


def _window_samples(
    observed: set[datetime], center: datetime,
) -> tuple[dict[str, Any], ...]:
    samples: list[dict[str, Any]] = []
    for n in range(-WINDOW_WEEKS, WINDOW_WEEKS + 1):
        # Iterate local calendar weeks, not naive fixed-UTC offsets across DST.
        friday = center.astimezone(NY).date() + timedelta(
            days=4 - center.astimezone(NY).weekday() + 7 * n
        )
        cut = datetime.combine(friday, time(17), NY).astimezone(UTC)
        earlier = cut - M5 in observed
        at_cut = cut in observed
        after = any(cut + i * M5 in observed for i in range(1, 13))
        samples.append({
            "week_friday_ny": friday.isoformat(),
            "expected_friday_close_utc": cut.isoformat(),
            "last_m5_before_close_present": earlier,
            "m5_at_conventional_close_present": at_cut,
            "any_m5_next_hour_present": after,
            "convention_pattern_match": earlier and not at_cut and not after,
        })
    return tuple(samples)


def examine_original_fx_weekly_close_gaps(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
    gm4_forensic_rows: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    """Classify R6's three gaps WITHOUT using post-decision prices for G7."""
    if market not in GAP_TARGETS:
        raise ValueError("R7 source market not in frozen Atlas")
    timestamps: set[datetime] = set()
    for bar in bars:
        opened = bar.opened_at
        if opened.tzinfo is None or opened.utcoffset() is None:
            raise ValueError("R7 original M5 timezone absent")
        stamp = opened.astimezone(UTC)
        if stamp in timestamps:
            raise ValueError("R7 duplicate original M5 timestamp")
        timestamps.add(stamp)
    if not timestamps:
        raise ValueError("R7 original market timestamps absent")
    gaps = tuple(
        row for row in gm4_forensic_rows if row["observed_issue"] == "SOURCE_M5_GAP"
    )
    expected = set(GAP_TARGETS[market])
    actual = {row["first_missing_original_m5_opened_at_utc"] for row in gaps}
    if actual != expected or len(gaps) != len(expected):
        raise ValueError("R7 frozen R6 gap identity/date has changed")
    if len({row["source_event_id"] for row in gaps}) != len(gaps):
        raise ValueError("R7 duplicate frozen source event ID")
    results = []
    aggregate: Counter[str] = Counter()
    for row in gaps:
        if (
            row["market"] != market.value
            or row["gm4_terminal_remains_UNKNOWN"] is not True
            or row["forensics_is_expost_only"] is not True
            or row["no_sizing"] is not True
            or row["G_M4_PASS"] is not False
        ):
            raise ValueError("R7 cannot accept forged market / GM4 terminal")
        absent = _stamp(row["first_missing_original_m5_opened_at_utc"])
        if absent in timestamps:
            raise ValueError("R7 supposed missing source M5 actually exists")
        before = absent - M5 in timestamps
        after = absent + M5 in timestamps
        when_ny = absent.astimezone(NY)
        friday_close = (
            when_ny.weekday() == 4
            and when_ny.hour == 17
            and when_ny.minute == 0
        )
        reference_week = _window_samples(timestamps, absent) if friday_close else ()
        sample_matches = sum(x["convention_pattern_match"] for x in reference_week)
        comparable = sum(x["last_m5_before_close_present"] for x in reference_week)
        next_hour = any(absent + i * M5 in timestamps for i in range(1, 13))
        if friday_close and before and not next_hour and comparable >= 3:
            status = "CONVENTION_CONSISTENT_PROVIDER_CALENDAR_UNVERIFIED"
        elif not friday_close and before and after:
            status = "INTERNAL_ONE_BAR_GAP_PROVIDER_SOURCE_REQUIRED"
        else:
            status = "NOT_CONSISTENT_NEEDS_PROVIDER_CALENDAR"
        aggregate[status] += 1
        results.append({
            "schema": SCHEMA,
            "market": market.value,
            "source_event_id": row["source_event_id"],
            "original_m5_missing_at_utc": absent.isoformat(),
            "original_m5_missing_at_new_york": when_ny.isoformat(),
            "conventional_ny_friday_1700": friday_close,
            "previous_m5_present": before,
            "next_m5_present": after,
            "any_m5_in_next_hour": next_hour,
            "neighbor_fridays_measured": len(reference_week),
            "neighbor_fridays_with_preclose_m5": comparable,
            "neighbor_fridays_convention_pattern_matches": sample_matches,
            "neighbor_friday_audit": reference_week,
            "diagnostic_status": status,
            "broker_specific_historical_calendar_authenticated": False,
            "gm4_original_terminal_remains_unknown": True,
            "terminal_adjudicated": False,
            "no_rearm_authority": True,
            "not_a_trade": True,
            "no_sizing": True,
            "G_M4_PASS": False,
            "G_M5_ISSUED": False,
            "GLOBAL_CERTIFIED": False,
        })
    return {
        "schema": SCHEMA,
        "market": market.value,
        "original_m5_count": len(bars),
        "forensic_gaps": len(results),
        "diagnostics": dict(sorted(aggregate.items())),
        "source_broker_schedule_verification": "MISSING",
        "terminal_adjudicated": False,
        "G_M4_PASS": False,
        "GLOBAL_CERTIFIED": False,
        "no_sizing": True,
        "no_orders": True,
    }, tuple(results)
