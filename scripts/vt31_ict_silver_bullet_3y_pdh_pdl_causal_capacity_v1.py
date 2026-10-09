#!/usr/bin/env python3
"""Streaming 3Y original-ICT hour + causal PDH/PDL *hypothesis* capacity lab.

PDH/PDL is ONE candidate draw on liquidity (DOL), not a universal ICT
requirement. Selection uses only already CLOSED NY-local prior-day M1 data.
A classic 3-bar FVG must close in the original 03/10/14 NY source hour.
10 NAS100 points are PROJECTED price-to-liquidity, not realized profit.
The FIRST viable FVG per NY-local source window is selected without outcomes.
Later intrahour midpoint TOUCH is measured ex-post ONLY FOR RESEARCH;
touch is neither verified fill nor tradable execution. No Sharpe/PF inferred.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

BASE_ID = "VT31_NAS100_OWNER_3Y_BASE_001"
SCHEMA = "qore.vt31.ict_silver_bullet_3y_pdh_pdl_causal_capacity.v1"
NY = ZoneInfo("America/New_York")
START = datetime(2023, 10, 1, tzinfo=UTC)
END = datetime(2026, 10, 1, tzinfo=UTC)
SOURCE_HOURS = {"VT31_LONDON": 3, "VT31_NY_AM": 10, "VT31_NY_PM": 14}
MIN_PROJECTED_POINTS = Decimal("10")
MIN_PRIOR_DAY_M1 = 720
MAX_PRIOR_DAY_AGE_DAYS = 4
COMPLETE_HOUR = (1 << 60) - 1


def _dt(raw: object) -> datetime:
    stamp = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("unaware M1 time")
    return stamp.astimezone(UTC)


def _d(raw: object) -> Decimal:
    value = Decimal(str(raw))
    if not value.is_finite() or value <= 0:
        raise ValueError("invalid M1 price")
    return value


def _s(value: Decimal) -> str:
    return format(value, "f")


@dataclass(frozen=True, slots=True)
class Bar:
    opened: datetime
    closed: datetime
    high: Decimal
    low: Decimal
    close_price: Decimal

    @classmethod
    def parse(cls, row: dict[str, Any]) -> "Bar":
        opened, closed = _dt(row["opened_at"]), _dt(row["closed_at"])
        if closed - opened != timedelta(minutes=1) or opened.second:
            raise ValueError("M1 candle duration/alignment")
        high, low, price = _d(row["high"]), _d(row["low"]), _d(row["close"])
        if not low <= price <= high:
            raise ValueError("close outside high-low")
        return cls(opened, closed, high, low, price)


@dataclass(frozen=True, slots=True)
class CompletedPriorDay:
    day: date
    high: Decimal
    low: Decimal
    bar_count: int
    available_at: datetime


@dataclass(slots=True)
class Chosen:
    side: str
    formed_at: datetime
    raw_fvg_first_at: datetime
    gap_low: Decimal
    gap_high: Decimal
    midpoint: Decimal
    dol_family: str
    dol_price: Decimal
    dol_available_at: datetime
    pd_source_day: date
    framework: Decimal
    later_midpoint_touch_at: datetime | None = None
    later_bar_open: datetime | None = None


@dataclass(slots=True)
class Window:
    mask: int = 0
    raw_fvg: int = 0
    first_raw_fvg_at: datetime | None = None
    first_candidate: Chosen | None = None
    first_by_side: dict[str, Chosen] = field(default_factory=dict)
    rejected: Counter[str] = field(default_factory=Counter)


def _new_york_midnight(day: date) -> datetime:
    return datetime.combine(day, time(0), tzinfo=NY).astimezone(UTC)


def _candidate_at_close(
    *,
    day: date,
    model: str,
    bar1: Bar,
    bar3: Bar,
    prev: CompletedPriorDay | None,
) -> tuple[Chosen | None, str]:
    side = (
        "LONG" if bar3.low > bar1.high else
        "SHORT" if bar3.high < bar1.low else None
    )
    if side is None:
        return None, "NOT_FVG"
    at = bar3.closed
    if at <= bar1.closed or at.astimezone(NY).date() != day:
        raise AssertionError("FVG temporal contradiction")
    if prev is None:
        return None, "NO_COMPLETED_PRIOR_NY_TRADING_DAY"
    age = (day - prev.day).days
    if age <= 0 or age > MAX_PRIOR_DAY_AGE_DAYS:
        return None, "PRIOR_NY_DAY_STALE"
    if prev.available_at > at:
        raise AssertionError("future previous-day high-low")
    if prev.bar_count < MIN_PRIOR_DAY_M1:
        return None, "PRIOR_DAY_COVERAGE_INSUFFICIENT"

    # Classic 3-bar displacement leaves a wick-to-wick price gap.
    gap_low, gap_high = (
        (bar1.high, bar3.low) if side == "LONG" else (bar3.high, bar1.low)
    )
    midpoint = (gap_low + gap_high) / Decimal("2")
    if side == "LONG":
        dol_family, target = "PREVIOUS_DAY_HIGH", prev.high
        room = target - bar3.close_price
        target_beyond_entry = target > midpoint
    else:
        dol_family, target = "PREVIOUS_DAY_LOW", prev.low
        room = bar3.close_price - target
        target_beyond_entry = target < midpoint
    if room <= 0 or not target_beyond_entry:
        return None, "PDH_PDL_BEHIND_PRICE_OR_FVG_ENTRY"
    if room < MIN_PROJECTED_POINTS:
        return None, "PDH_PDL_PROJECTED_ROOM_LT_10_INDEX_POINTS"
    if at.astimezone(NY).hour != SOURCE_HOURS[model]:
        # A third candle closing at 04:00/11:00/15:00 has zero time left
        # for a prospective entry in that same original-ICT hour.
        return None, "FVG_FORMED_AT_OR_AFTER_SOURCE_EXPIRY"
    return (
        Chosen(
            side=side, formed_at=at, raw_fvg_first_at=at,
            gap_low=gap_low, gap_high=gap_high, midpoint=midpoint,
            dol_family=dol_family, dol_price=target,
            dol_available_at=prev.available_at, pd_source_day=prev.day,
            framework=room,
        ),
        "FIRST_CAUSAL_PDH_PDL_HYPOTHESIS_FVG",
    )



def _candidate_record(model: str, day: str, cand: Chosen) -> dict[str, object]:
    """Standalone immutable snapshot of as-of selected research hypothesis."""
        return {
            "ny_date": day,
            "model": model,
            "side": cand.side,
            "source_fvg_closed_at_utc": cand.formed_at.isoformat(),
            "first_raw_fvg_closed_at_utc": cand.raw_fvg_first_at.isoformat(),
            "gap_lower": _s(cand.gap_low),
            "gap_upper": _s(cand.gap_high),
            "gap_midpoint": _s(cand.midpoint),
            "causal_draw_family": cand.dol_family,
            "causal_draw_target": _s(cand.dol_price),
            "draw_available_at_utc": cand.dol_available_at.isoformat(),
            "draw_prior_ny_day": cand.pd_source_day.isoformat(),
            "projected_index_points_to_pdh_pdl": _s(cand.framework),
            "research_only_later_midpoint_touch": (
                cand.later_midpoint_touch_at is not None
            ),
            "research_only_touch_observed_at_utc": (
                None if cand.later_midpoint_touch_at is None
                else cand.later_midpoint_touch_at.isoformat()
            ),
            "mt5_or_bid_ask_fill_proven": False,
            "cognitive_dol_thesis_proven": False,
            "mss_displacement_proven": False,
            "structural_stop_proven": False,
            "ict_trade_certified": False,
        }

def analyze(rows: Iterable[dict[str, Any]]) -> dict[str, object]:
    windows: dict[str, dict[str, Window]] = {
        model: {} for model in SOURCE_HOURS
    }
    current_ny_day: date | None = None
    current_day_high: Decimal | None = None
    current_day_low: Decimal | None = None
    current_day_count = 0
    last_complete_prior: CompletedPriorDay | None = None
    previous_three: deque[Bar] = deque(maxlen=3)
    last_open: datetime | None = None
    total_m1 = 0
    for raw in rows:
        bar = Bar.parse(raw)
        if not START <= bar.opened < END or bar.closed > END:
            raise ValueError("M1 outside immutable 3Y UTC range")
        if last_open is not None and bar.opened <= last_open:
            raise ValueError("M1 is duplicated / reversed")
        day = bar.opened.astimezone(NY).date()
        if current_ny_day is None:
            current_ny_day = day
        if day != current_ny_day:
            # Once NY-local midnight passes, yesterday's high/low
            # becomes causally knowable; it could never be known earlier.
            assert current_day_high is not None and current_day_low is not None
            if current_day_count >= MIN_PRIOR_DAY_M1:
                last_complete_prior = CompletedPriorDay(
                    day=current_ny_day,
                    high=current_day_high, low=current_day_low,
                    bar_count=current_day_count,
                    available_at=_new_york_midnight(
                        current_ny_day + timedelta(days=1)
                    ),
                )
            current_ny_day = day
            current_day_high = None
            current_day_low = None
            current_day_count = 0
        current_day_high = (
            bar.high if current_day_high is None
            else max(current_day_high, bar.high)
        )
        current_day_low = (
            bar.low if current_day_low is None
            else min(current_day_low, bar.low)
        )
        current_day_count += 1
        total_m1 += 1

        if last_open is None or bar.opened - last_open != timedelta(minutes=1):
            previous_three.clear()
        last_open = bar.opened
        previous_three.append(bar)
        local_open = bar.opened.astimezone(NY)
        hour = local_open.hour
        for model, model_hour in SOURCE_HOURS.items():
            if hour != model_hour:
                continue
            key = day.isoformat()
            window = windows[model].setdefault(key, Window())
            minute = local_open.minute
            bit = 1 << minute
            if window.mask & bit:
                raise ValueError("ambiguous local M1 minute inside ICT source hour")
            window.mask |= bit

            # Only a PREVIOUSLY selected candidate can be touched. The
            # entire current M1 candle is used AFTER its close as a
            # retrospective touch outcome; not an at-open decision.
            for chosen in window.first_by_side.values():
                if (
                    chosen.later_midpoint_touch_at is None
                    and bar.opened >= chosen.formed_at
                    and bar.low <= chosen.midpoint <= bar.high
                ):
                    chosen.later_midpoint_touch_at = bar.closed
                    chosen.later_bar_open = bar.opened

            if len(previous_three) != 3:
                continue
            first, middle, third = previous_three
            if first.closed != middle.opened or middle.closed != third.opened:
                raise AssertionError("noncausal gap sequence")
            if not (third.low > first.high or third.high < first.low):
                continue
            window.raw_fvg += 1
            if window.first_raw_fvg_at is None:
                window.first_raw_fvg_at = third.closed
            # FIRST qualified event PER SIDE. The original model needs a
            # directional DOL BEFORE source selection; choosing one global
            # first-gap side would silently impose a hindsight bias.
            forming_side = "LONG" if third.low > first.high else "SHORT"
            if forming_side in window.first_by_side:
                continue
            candidate, classification = _candidate_at_close(
                day=day, model=model, bar1=first, bar3=third,
                prev=last_complete_prior,
            )
            window.rejected[classification] += 1
            if candidate is not None:
                candidate.raw_fvg_first_at = window.first_raw_fvg_at
                window.first_by_side[candidate.side] = candidate
                if window.first_candidate is None:
                    # Retain earlier global-first candidate for audit
                    # compatibility, but NOT as directional trade authority.
                    window.first_candidate = candidate

    if total_m1 == 0:
        raise ValueError("no 3Y M1 evidence")
    payload: dict[str, object] = {}
    for model, by_day in windows.items():
        full = sorted(day for day, item in by_day.items() if item.mask == COMPLETE_HOUR)
        partial = sorted(day for day, item in by_day.items() if item.mask != COMPLETE_HOUR)
        reasons: Counter[str] = Counter()
        eligible: list[dict[str, object]] = []
        directional: list[dict[str, object]] = []
        for day in full:
            item = by_day[day]
            reasons.update(item.rejected)
            for direction in ("LONG", "SHORT"):
                chosen_for_side = item.first_by_side.get(direction)
                if chosen_for_side is not None:
                    directional.append(_candidate_record(
                        model, day, chosen_for_side
                    ))
            cand = item.first_candidate
            if cand is None:
                continue
            eligible.append(_candidate_record(model, day, cand))
        touched = sum(x["research_only_later_midpoint_touch"] for x in eligible)
        payload[model] = {
            "original_ict_ny_hour": f"{SOURCE_HOURS[model]:02d}:00-"
            f"{SOURCE_HOURS[model]+1:02d}:00 America/New_York",
            "complete_source_hour_days": len(full),
            "incomplete_source_hour_days": len(partial),
            "complete_days_with_raw_fvg": sum(
                by_day[day].raw_fvg > 0 for day in full
            ),
            "total_raw_fvg_events_on_complete_days": sum(
                by_day[day].raw_fvg for day in full
            ),
            "days_with_first_pdh_pdl_10point_fvg_hypothesis": len(eligible),
            "days_with_subsequent_intrawindow_midpoint_touch": touched,
            "days_without_later_touch": len(eligible) - touched,
            "rejection_reason_occurrences_before_first_candidate": dict(
                sorted(reasons.items())
            ),
            "research_hypotheses": eligible,
            "directional_first_fvg_hypotheses": directional,
            "directional_hypothesis_count_not_trades": len(directional),
            "directional_hypothesis_count_by_side": dict(Counter(
                str(x["side"]) for x in directional
            )),
            "directional_count_can_be_up_to_two_per_session_day": True,
            "candidate_count_is_not_executed_trade_count": True,
            "trade_count": "NOT_PROVEN",
            "profit_factor": "NOT_COMPUTABLE_WITHOUT_EXECUTION",
            "drawdown_r": "NOT_COMPUTABLE_WITHOUT_EXECUTION",
            "certified": False,
        }
    return {
        "schema": SCHEMA,
        "base_id": BASE_ID,
        "market": "NAS100",
        "m1_bars": total_m1,
        "frozen_start_at": START.isoformat(),
        "frozen_end_exclusive": END.isoformat(),
        "previous_day_min_m1": MIN_PRIOR_DAY_M1,
        "max_prior_day_calendar_age": MAX_PRIOR_DAY_AGE_DAYS,
        "minimum_projected_index_points": _s(MIN_PROJECTED_POINTS),
        "models": payload,
        "governance": {
            "read_only_ict_hour_pdh_pdl_hypothesis": True,
            "pdh_pdl_only_one_dol_family_not_universal_ict_requirement": True,
            "prior_day_only_after_ny_midnight_close": True,
            "first_selected_candidate_from_asof_only": True,
            "first_qualified_fvg_separated_by_direction": True,
            "no_ex_post_direction_selection_as_trading_authority": True,
            "same_bar_entry_or_fill_claimed": False,
            "m1_intrabar_touch_not_a_verified_fill": True,
            "no_mss_or_cognitive_authority_claimed": True,
            "full_structural_stop_not_established": True,
            "outcomes_used_for_selection": False,
            "fresh_holdout_opened": False,
            "live_authorized": False,
            "candidate_certified": False,
        },
    }


def _stream_m1(path: Path) -> Iterable[dict[str, Any]]:
    import ijson
    expected = {
        "base_id": BASE_ID,
        "market": "NAS100",
        "base_start_at": START.isoformat(),
        "base_end_exclusive": END.isoformat(),
    }
    for field_name, value in expected.items():
        with path.open("rb") as file:
            actual = next(ijson.items(file, field_name), None)
        if actual != value:
            raise ValueError(f"immutable M1 {field_name} mismatch: {actual!r}")
    with path.open("rb") as file:
        for raw in ijson.items(file, "periods.M1.item"):
            if not isinstance(raw, dict):
                raise ValueError("invalid M1 candle")
            yield raw


def self_test() -> None:
    # Complete prior NY trading day, then 10:02 FVG and subsequent touch.
    date_a = datetime(2025, 5, 5, 4, tzinfo=UTC)  # Mon 00:00 NY
    def make(at: datetime, hi: int, lo: int, close: int) -> dict[str, object]:
        return {
            "opened_at": at.isoformat(),
            "closed_at": (at + timedelta(minutes=1)).isoformat(),
            "high": str(hi), "low": str(lo), "close": str(close),
        }
    day_before = [
        make(date_a + timedelta(minutes=i), 140, 70, 100)
        for i in range(720)
    ]
    t = datetime(2025, 5, 6, 14, tzinfo=UTC)  # Tue 10:00 NY.
    test = day_before + [
        make(t, 112, 103, 106),
        make(t + timedelta(minutes=1), 110, 99, 104),
        make(t + timedelta(minutes=2), 100, 95, 97),
        make(t + timedelta(minutes=3), 103, 99, 100),
    ]
    # Fill the complete source window after touch with harmless no-FVG bars.
    test += [
        make(t + timedelta(minutes=i), 103, 99, 100)
        for i in range(4, 60)
    ]
    result = analyze(test)
    am = result["models"]["VT31_NY_AM"]
    # The synthetic previous day spans 00:00-12:00 NY, so it also contains
    # a complete 10-11 hour; only the following day has a real FVG.
    assert am["complete_source_hour_days"] == 2
    assert am["complete_days_with_raw_fvg"] == 1
    assert am["days_with_first_pdh_pdl_10point_fvg_hypothesis"] == 1
    assert am["days_with_subsequent_intrawindow_midpoint_touch"] == 1
    assert am["directional_hypothesis_count_not_trades"] == 1
    assert am["directional_first_fvg_hypotheses"][0]["side"] == "SHORT"
    cand = am["research_hypotheses"][0]
    assert cand["causal_draw_family"] == "PREVIOUS_DAY_LOW"
    assert cand["projected_index_points_to_pdh_pdl"] == "27"
    assert cand["gap_midpoint"] == "101.5"
    assert cand["source_fvg_closed_at_utc"] == (
        t + timedelta(minutes=3)
    ).isoformat()
    assert cand["research_only_touch_observed_at_utc"] == (
        t + timedelta(minutes=4)
    ).isoformat()
    assert cand["mt5_or_bid_ask_fill_proven"] is False
    assert result["governance"]["outcomes_used_for_selection"] is False
    # Reject late or concurrent M1 ambiguities.
    try:
        analyze(test[:1] + test[:1])
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate M1 passed")
    # A complete daily high from the CURRENT day is never eligible to
    # act as the prior-day draw before the NY-local day rollover.
    same_day = analyze(test[720:])
    assert same_day["models"]["VT31_NY_AM"][
        "days_with_first_pdh_pdl_10point_fvg_hypothesis"
    ] == 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print(json.dumps({"self_test": "PASS", "schema": SCHEMA}))
        return
    if not args.evidence or not args.output:
        parser.error("--evidence and --output required")
    report = analyze(_stream_m1(args.evidence))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "schema": SCHEMA,
        "base_id": BASE_ID,
        "m1": report["m1_bars"],
        "source_hypothesis_density_not_trades": {
            model: {
                "complete_days": item["complete_source_hour_days"],
                "raw_fvg_days": item["complete_days_with_raw_fvg"],
                "first_pdh_pdl_10point_fvg_days": item[
                    "days_with_first_pdh_pdl_10point_fvg_hypothesis"
                ],
                "later_intrawindow_midpoint_touches_not_fills": item[
                    "days_with_subsequent_intrawindow_midpoint_touch"
                ],
                "rejections": item["rejection_reason_occurrences_before_first_candidate"],
            }
            for model, item in report["models"].items()
        },
        "certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
