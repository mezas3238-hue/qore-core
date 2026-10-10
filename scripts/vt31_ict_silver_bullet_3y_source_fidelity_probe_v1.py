#!/usr/bin/env python3
"""Read-only ICT 2023 Silver Bullet FVG census on the frozen 3Y NAS100 M1.

Primary lesson: https://www.youtube.com/watch?v=tRq1hyGGtl4
London = 03-04, NY AM = 10-11, NY PM = 14-15, ALL New York local time.
Detects raw closed-candle 3-bar FVGs; never claims a valid trade before
causal draw-on-liquidity, direction, price-delivery, setup and execution.
No historical outcomes, trading policy, sizing, holdout or live authority.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

BASE_ID = "VT31_NAS100_OWNER_3Y_BASE_001"
SCHEMA = "qore.vt31.ict_silver_bullet_3y_source_fidelity_probe.v1"
START = datetime(2023, 10, 1, tzinfo=UTC)
END = datetime(2026, 10, 1, tzinfo=UTC)
NY = ZoneInfo("America/New_York")
LONDON = ZoneInfo("Europe/London")
SLOTS = {"VT31_LONDON": 3, "VT31_NY_AM": 10, "VT31_NY_PM": 14}
MASK = (1 << 60) - 1


def _dt(raw: object) -> datetime:
    value = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("M1 timestamp must include UTC offset")
    return value.astimezone(UTC)


def _decimal(raw: object) -> Decimal:
    value = Decimal(str(raw))
    if not value.is_finite() or value <= 0:
        raise ValueError("invalid finite positive OHLC")
    return value


def _candle(row: dict[str, Any]) -> dict[str, Any]:
    start = _dt(row["opened_at"])
    end = _dt(row["closed_at"])
    if end - start != timedelta(minutes=1):
        raise ValueError("non-exact M1 data")
    o, h, low, close = (
        _decimal(row[x]) for x in ("open", "high", "low", "close")
    )
    if low > min(o, close) or h < max(o, close):
        raise ValueError("OHLC invalid range")
    return {
        "opened_at": start, "closed_at": end,
        "open": o, "high": h, "low": low, "close": close
    }


def count_source_events(rows: Iterable[dict[str, Any]]) -> dict[str, object]:
    previous: list[dict[str, Any]] = []
    masks: dict[str, Counter[str]] = {model: Counter() for model in SLOTS}
    # int bitmask for exact M1 completeness on each frozen NY-local day.
    bitmasks: dict[str, dict[str, int]] = {model: {} for model in SLOTS}
    totals = Counter()
    per_model_events: dict[str, Counter[str]] = {
        model: Counter() for model in SLOTS
    }
    first_fvg: dict[str, dict[str, dict[str, str]]] = {
        model: {} for model in SLOTS
    }
    strict_full_three_days: dict[str, set[str]] = {
        model: set() for model in SLOTS
    }
    samples: dict[str, list[dict[str, str]]] = {model: [] for model in SLOTS}
    previous_open: datetime | None = None
    prev_two_contiguous = 0
    for raw in rows:
        bar = _candle(raw)
        opened, closed = bar["opened_at"], bar["closed_at"]
        if not START <= opened < END or closed > END:
            raise ValueError("M1 bar is outside frozen 3Y boundary")
        if opened.second or opened.microsecond:
            raise ValueError("M1 opened_at is not minute aligned")
        if previous_open is not None and opened <= previous_open:
            raise ValueError("duplicate or out-of-order M1")
        if previous_open is None or opened - previous_open != timedelta(minutes=1):
            prev_two_contiguous = 0
            previous = []
        previous_open = opened
        totals["all_m1"] += 1

        # A FVG is CANDIDATE evidence only if third candle fully closes
        # during the exact source window, not merely opens in that hour.
        ny_open = opened.astimezone(NY)
        ny_close = closed.astimezone(NY)
        for model, hour in SLOTS.items():
            if ny_open.hour != hour or ny_open.date() != ny_close.date():
                continue
            day = ny_open.date().isoformat()
            masks[model][day] += 1
            bitmasks[model][day] = (
                bitmasks[model].get(day, 0) | 1 << ny_open.minute
            )
        if len(previous) == 2:
            first = previous[0]
            # Require all three candles to be contiguous and fully causal.
            if (first["closed_at"] == previous[1]["opened_at"]
                    and previous[1]["closed_at"] == opened):
                bearish = first["low"] - bar["high"]
                bullish = bar["low"] - first["high"]
                side = ("SHORT" if bearish > 0 else
                        "LONG" if bullish > 0 else None)
                gap = bearish if bearish > 0 else bullish
                if side is not None:
                    for model, hour in SLOTS.items():
                        # 4:00 close belongs to the last 3:59 source candle.
                        if ny_open.hour != hour or ny_close.hour not in (
                            hour, hour + 1
                        ):
                            continue
                        day = ny_open.date().isoformat()
                        per_model_events[model]["raw_three_bar_fvg_count"] += 1
                        per_model_events[model][f"{side.lower()}_fvg_count"] += 1
                        first_ny = first["opened_at"].astimezone(NY)
                        all_three_inside = (
                            first_ny.date() == ny_open.date()
                            and first_ny.hour == hour
                        )
                        if all_three_inside:
                            per_model_events[model]["three_full_m1_inside_hour"] += 1
                            strict_full_three_days[model].add(day)
                        else:
                            per_model_events[model]["fvg_straddles_window_start"] += 1
                        event = {
                            "closed_at_utc": closed.isoformat(),
                            "formed_at_ny": ny_close.isoformat(),
                            "side": side,
                            "gap_points": format(gap, "f"),
                            "all_three_m1_inside_hour_research_policy": all_three_inside,
                            "prior_candles_may_precede_window": str(
                                first["opened_at"].astimezone(NY).hour != hour
                            ).lower(),
                            "draw_on_liquidity": "NOT_EVALUATED",
                            "prospective_10_index_point_framework": "NOT_EVALUATED",
                            "mss_or_displacement_quality": "NOT_EVALUATED",
                        }
                        first_fvg[model].setdefault(day, event)
                        if len(samples[model]) < 8:
                            samples[model].append(event)
        previous.append(bar)
        previous = previous[-2:]

    if totals["all_m1"] == 0:
        raise ValueError("empty 3Y M1 evidence")
    reports: dict[str, dict[str, object]] = {}
    for model in SLOTS:
        eligible_days = sorted(
            day for day, mask in bitmasks[model].items()
            if mask == MASK
        )
        partial_days = sorted(
            day for day, mask in bitmasks[model].items()
            if mask != MASK
        )
        first = first_fvg[model]
        completed_fvg_days = sorted(set(eligible_days) & set(first))
        first_side = Counter(first[day]["side"] for day in completed_fvg_days)
        london_hours = Counter(
            str(datetime.fromisoformat(first[day]["formed_at_ny"])
                .astimezone(LONDON).hour)
            for day in completed_fvg_days
        )
        reports[model] = {
            "ny_source_window": f"{SLOTS[model]:02d}:00-{SLOTS[model]+1:02d}:00",
            "ny_source_timezone": "America/New_York",
            "m1_days_with_any_window_bar": len(bitmasks[model]),
            "m1_days_with_complete_60_minute_source_window": len(eligible_days),
            "m1_days_with_incomplete_source_window": len(partial_days),
            "days_with_raw_fvg_in_complete_source_window": len(completed_fvg_days),
            "days_with_complete_window_no_raw_fvg": (
                len(eligible_days) - len(completed_fvg_days)
            ),
            "complete_days_with_full_three_inside_raw_fvg": len(
                set(eligible_days) & strict_full_three_days[model]
            ),
            "full_three_inside_window_is_qore_conservative_research_policy": True,
            "full_three_requirement_not_verified_as_universal_2023_ict": True,
            "raw_fvg_event_counts": dict(per_model_events[model]),
            "first_raw_fvg_side_by_day": dict(first_side),
            "london_wall_clock_first_fvg_hour": dict(sorted(london_hours.items())),
            "first_8_events_observation_only": samples[model],
            "no_valid_trades_inferred": True,
            "max_10_point_delivery_framework_proven": False,
            "next_causal_draw_on_liquidity_proven": False,
            "maximum_cognition_connected": False,
            "session_certified": False,
        }
    return {
        "schema": SCHEMA,
        "base_id": BASE_ID,
        "frozen_start_at": START.isoformat(),
        "frozen_end_exclusive": END.isoformat(),
        "market": "NAS100",
        "source": "ICT_2023_PRIMARY_SILVER_BULLET",
        "source_video": "https://www.youtube.com/watch?v=tRq1hyGGtl4",
        "all_m1_count": totals["all_m1"],
        "models": reports,
        "source_2023_minimum_projected_framework_index_points": "10",
        "source_setup_count": "NOT_ESTABLISHED_BY_RAW_FVG",
        "executed_trade_count": "NOT_ESTABLISHED_BY_RAW_FVG",
        "governance": {
            "read_only_source_candidate_census": True,
            "raw_fvg_does_not_authorize_trade": True,
            "target_ranking_from_outcomes": False,
            "future_bar_authority": False,
            "forced_9_10_ny_range_as_ict_necessity": False,
            "no_sizing_leverage_or_compounding": True,
            "fresh_holdout_opened": False,
            "candidate_certified": False,
            "live_authorized": False,
        },
    }


def _stream_evidence(path: Path) -> Iterable[dict[str, Any]]:
    import ijson

    # Single streaming pass: no huge three-year M1 load into memory.
    with path.open("rb") as handle:
        for row in ijson.items(handle, "periods.M1.item"):
            if not isinstance(row, dict):
                raise ValueError("invalid candle")
            yield row


def _identity(path: Path) -> None:
    import ijson

    expected = {
        "base_id": BASE_ID,
        "base_start_at": START.isoformat(),
        "base_end_exclusive": END.isoformat(),
        "market": "NAS100",
    }
    for key, value in expected.items():
        with path.open("rb") as handle:
            observed = next(ijson.items(handle, key), None)
        if observed != value:
            raise ValueError(f"wrong immutable evidence {key}: {observed!r}")


def _mkbar(start: datetime, *, high: str, low: str,
           opened: str, closed: str) -> dict[str, str]:
    return {
        "opened_at": start.isoformat(),
        "closed_at": (start + timedelta(minutes=1)).isoformat(),
        "open": opened, "high": high, "low": low, "close": closed,
    }


def self_test() -> None:
    # US/UK DST mismatch: London source must still be 03-04 NY year-round.
    for date_text, utc_hour, london_hour in (
        ("2026-03-02", 8, 8),
        ("2026-03-10", 7, 7),
        ("2026-03-30", 7, 8),
        ("2026-10-26", 7, 7),
        ("2026-11-02", 8, 8),
    ):
        utc = datetime.fromisoformat(date_text + "T" + str(utc_hour).zfill(2)
                                   + ":00:00+00:00")
        assert utc.astimezone(NY).hour == 3
        assert utc.astimezone(LONDON).hour == london_hour
    base = datetime(2025, 5, 6, 14, 0, tzinfo=UTC)  # 10:00 NY
    rows = (
        _mkbar(base, high="110", low="100", opened="105", closed="106"),
        _mkbar(base + timedelta(minutes=1),
               high="108", low="99", opened="106", closed="100"),
        _mkbar(base + timedelta(minutes=2),
               high="97", low="94", opened="96", closed="95"),
    )
    report = count_source_events(rows)
    m = report["models"]["VT31_NY_AM"]
    assert m["raw_fvg_event_counts"]["short_fvg_count"] == 1
    assert m["raw_fvg_event_counts"]["three_full_m1_inside_hour"] == 1
    assert m["m1_days_with_complete_60_minute_source_window"] == 0
    # Gap formed at 10:01 from candle 09:59 -> 10:01: source hour
    # raw FVG observation, but cross-hour strict research policy rejects.
    early = base - timedelta(minutes=1)
    cross = (
        _mkbar(early, high="110", low="100", opened="105", closed="106"),
        _mkbar(base, high="108", low="99", opened="106", closed="100"),
        _mkbar(base + timedelta(minutes=1), high="97", low="94", opened="96", closed="95"),
    )
    cross_report = count_source_events(cross)["models"]["VT31_NY_AM"]
    assert cross_report["raw_fvg_event_counts"]["raw_three_bar_fvg_count"] == 1
    assert cross_report["raw_fvg_event_counts"]["fvg_straddles_window_start"] == 1
    assert cross_report["raw_fvg_event_counts"].get("three_full_m1_inside_hour", 0) == 0
    assert m["days_with_raw_fvg_in_complete_source_window"] == 0
    assert report["governance"]["raw_fvg_does_not_authorize_trade"] is True
    # FVG from first 2 bars & future third inside window must not use future.
    try:
        count_source_events((rows[0], rows[0]))
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate M1 accepted")
    invalid = dict(rows[2])
    invalid["high"] = "90"
    try:
        count_source_events((rows[0], rows[1], invalid))
    except ValueError:
        pass
    else:
        raise AssertionError("invalid OHLC accepted")


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
    if args.evidence is None or args.output is None:
        parser.error("--evidence and --output required")
    _identity(args.evidence)
    payload = count_source_events(_stream_evidence(args.evidence))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "schema": SCHEMA,
        "base_id": BASE_ID,
        "all_m1": payload["all_m1_count"],
        "source_fvg_census_no_trade_count": {
            model: {
                "complete_days": data["m1_days_with_complete_60_minute_source_window"],
                "days_with_fvg": data["days_with_raw_fvg_in_complete_source_window"],
                "raw_fvg_events": data["raw_fvg_event_counts"],
                "complete_days_with_full_three_inside_fvg": data[
                    "complete_days_with_full_three_inside_raw_fvg"
                ],
            }
            for model, data in payload["models"].items()
        },
        "candidate_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
