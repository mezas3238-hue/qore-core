#!/usr/bin/env python3
"""Research-only TTrades protected-swing M1 witness, not a broker stop.

Source 2025-08-06 and 2025-08-07: sweep important low/high, then candle
CLOSE beyond opposing candle series. AM June 2025 still separately requires
the swing that caused displacement; this source witness does NOT certify it.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    NEW_YORK,
)

PREREG = "de181b82f5e72ddb824798d642eec8fa94d9ca06"
SOURCE = "TTRADES_PROTECTED_SWING_CAUSAL_CONTEXT_NOT_EXECUTABLE_STOP"


@dataclass(frozen=True, slots=True)
class ProtectedSourceVerdict:
    status: str
    reasons: tuple[str, ...]
    side: str
    as_of: datetime
    first_raid_at: datetime | None = None
    protected_source_extreme: Decimal | None = None
    confirmed_at: datetime | None = None
    opposing_body_boundary: Decimal | None = None
    second_return_m1_wick_proxy: Decimal | None = None
    framework_g3_c2_is_not_proven_same_swing: bool = True
    displacement_causing_swing_author_final_identified: bool = False
    broker_stop_tick_price_certified: bool = False
    method_certified: bool = False
    cognition_certified: bool = False
    human_source_review_completed: bool = False
    orders: int = 0
    sizing: int = 0

    def record(self) -> dict[str, Any]:
        return {
            "status": self.status, "reasons": list(self.reasons),
            "side": self.side, "as_of": self.as_of.isoformat(),
            "as_of_ny": self.as_of.astimezone(NEW_YORK).isoformat(),
            "first_raid_at": self.first_raid_at.isoformat()
                if self.first_raid_at is not None else None,
            "protected_source_extreme": str(self.protected_source_extreme)
                if self.protected_source_extreme is not None else None,
            "confirmed_at": self.confirmed_at.isoformat()
                if self.confirmed_at is not None else None,
            "opposing_body_boundary": str(self.opposing_body_boundary)
                if self.opposing_body_boundary is not None else None,
            "second_return_m1_wick_proxy": str(self.second_return_m1_wick_proxy)
                if self.second_return_m1_wick_proxy is not None else None,
            "framework_g3_c2_is_not_proven_same_swing":
                self.framework_g3_c2_is_not_proven_same_swing,
            "displacement_causing_swing_author_final_identified":
                self.displacement_causing_swing_author_final_identified,
            "broker_stop_tick_price_certified":
                self.broker_stop_tick_price_certified,
            "method_certified": self.method_certified,
            "cognition_certified": self.cognition_certified,
            "human_source_review_completed": self.human_source_review_completed,
            "orders": self.orders, "sizing": self.sizing,
        }


def source_protected_swing(
    *, side: str, nine: tuple[M1Bar, ...], ten: tuple[M1Bar, ...],
    opposing_series: tuple[M1Bar, ...], as_of: datetime,
) -> ProtectedSourceVerdict:
    at = as_of.astimezone(UTC)

    def emit(
        status: str, *reasons: str,
        raid: datetime | None = None,
        level: Decimal | None = None,
        boundary: Decimal | None = None,
        proxy: Decimal | None = None,
        confirmed: datetime | None = None,
    ) -> ProtectedSourceVerdict:
        return ProtectedSourceVerdict(
            status, tuple(reasons), side, at, raid,
            level, confirmed, boundary, proxy,
        )

    if side not in ("LONG", "SHORT"):
        return emit("SOURCE_INPUT_REJECTED", "SIDE_NOT_LONG_OR_SHORT")
    if (
        not nine or not ten
        or ten[-1].closed_at.astimezone(UTC) != at
        or at.astimezone(NEW_YORK).hour != 10
        or any(bar.closed_at > at for bar in ten)
    ):
        return emit("SOURCE_INPUT_REJECTED", "ASOF_HOUR_OR_FUTURE_CLOSED_M1")
    if (
        len(nine) != 60 or nine[0].opened_at.astimezone(NEW_YORK).hour != 9
        or nine[0].opened_at.astimezone(NEW_YORK).minute != 0
        or nine[-1].closed_at != ten[0].opened_at
        or any(left.closed_at != right.opened_at
               for left, right in zip(nine, nine[1:], strict=False))
        or any(left.closed_at != right.opened_at
               for left, right in zip(ten, ten[1:], strict=False))
    ):
        return emit("SOURCE_CONTEXT_UNKNOWN", "H1_09_OR_10_PREFIX_INCOMPLETE")
    h1_hi = max(x.high for x in nine)
    h1_lo = min(x.low for x in nine)
    first = None
    first_bar = None
    for candle in ten:
        hits_hi, hits_lo = candle.high > h1_hi, candle.low < h1_lo
        if hits_hi and hits_lo:
            return emit(
                "SOURCE_CONTEXT_UNKNOWN", "BOTH_H1_SIDES_SAME_M1_UNKNOWN_INTRABAR",
            )
        if first is None and (hits_hi or hits_lo):
            first = "SHORT" if hits_hi else "LONG"
            first_bar = candle
            break
    if first is None:
        return emit("SOURCE_CONTEXT_UNKNOWN", "NO_FIRST_NYAM_H1_RAID")
    assert first_bar is not None
    raid_at = first_bar.closed_at
    if first != side:
        return emit(
            "SOURCE_CONTEXT_REJECTED", "FIRST_RAID_SIDE_CONTRADICTS_PROFILE",
            raid=raid_at,
        )
    if len(ten) < 3 or ten[-1].closed_at <= raid_at:
        return emit(
            "PROTECTED_SWING_NOT_CONFIRMED_WAIT", "NO_LATER_DISPLACEMENT_CLOSE",
            raid=raid_at,
        )
    if any(
        (x.high > h1_hi if side == "LONG" else x.low < h1_lo)
        for x in ten if x.opened_at >= first_bar.closed_at
    ):
        return emit(
            "SOURCE_CONTEXT_UNKNOWN", "OPPOSITE_H1_RAID_BEFORE_CONFIRMATION",
            raid=raid_at,
        )
    if not opposing_series:
        return emit(
            "PROTECTED_SWING_NOT_CONFIRMED_WAIT",
            "OPPOSING_CANDLE_SERIES_MISSING", raid=raid_at,
        )
    if opposing_series[-1].closed_at == ten[-1].closed_at:
        return emit(
            "PROTECTED_SWING_NOT_CONFIRMED_WAIT",
            "NO_CLOSED_CONFIRMATION_AFTER_OPPOSING_CANDLE_SERIES",
            raid=raid_at,
        )
    actual = {b.closed_at: b for b in ten}
    if (
        any(b.closed_at not in actual or actual[b.closed_at] != b
            for b in opposing_series)
        or opposing_series[0].closed_at < raid_at
        or opposing_series[-1].closed_at >= ten[-1].closed_at
        or any(a.closed_at != z.opened_at
               for a, z in zip(opposing_series, opposing_series[1:], strict=False))
    ):
        return emit(
            "SOURCE_INPUT_REJECTED", "OPPOSING_SERIES_NOT_CAUSAL_CLOSED_M1",
            raid=raid_at,
        )
    if any(
        b.close >= b.open if side == "LONG" else b.close <= b.open
        for b in opposing_series
    ):
        return emit(
            "PROTECTED_SWING_NOT_CONFIRMED_WAIT",
            "OPPOSING_SERIES_CANDLE_COLOR_INVALID", raid=raid_at,
        )
    boundary = (
        max(max(b.open, b.close) for b in opposing_series)
        if side == "LONG" else
        min(min(b.open, b.close) for b in opposing_series)
    )
    confirmation = ten[-1]
    crossed = (
        confirmation.close > boundary and confirmation.close > confirmation.open
        if side == "LONG" else
        confirmation.close < boundary and confirmation.close < confirmation.open
    )
    if not crossed:
        return emit(
            "PROTECTED_SWING_NOT_CONFIRMED_WAIT",
            "CONFIRMATION_CANDLE_CLOSE_NOT_BEYOND_OPPOSING_SERIES",
            raid=raid_at, boundary=boundary,
        )
    first_i = next(i for i, b in enumerate(ten) if b.closed_at == raid_at)
    source_run = ten[first_i:]
    extreme = (
        min(x.low for x in source_run)
        if side == "LONG" else max(x.high for x in source_run)
    )
    # A second-return wick is an independent geometric REFERENCE only;
    # the G3 actual C2 classification requires separate FVG/ops evidence.
    proxy = (
        ten[-2].low if side == "LONG" else ten[-2].high
    )
    return emit(
        "RESEARCH_PROTECTED_SWING_SOURCE_CONTEXT_WITNESSED",
        "PROTECTED_SWING_SERIES_CLOSED_BEYOND_CONTEXT_M1_ONLY",
        raid=raid_at, level=extreme, boundary=boundary,
        proxy=proxy, confirmed=confirmation.closed_at,
    )


def make_fixture(
    *, side: str, month: int,
) -> tuple[tuple[M1Bar, ...], tuple[M1Bar, ...], tuple[M1Bar, ...]]:
    if month not in (1, 7):
        raise ValueError("ONLY_PRESPECIFIED_DST_FIXTURES")
    first_date = datetime(2026, month, 5 if month == 1 else 13, 9,
                          tzinfo=NEW_YORK).astimezone(UTC)
    def bar(i: int, o="100", hi="102", lo="98", cl="100.5") -> M1Bar:
        open_time = first_date + timedelta(minutes=i)
        return M1Bar(
            open_time, open_time + timedelta(minutes=1),
            Decimal(o), Decimal(hi), Decimal(lo), Decimal(cl),
        )
    nine = [bar(i) for i in range(60)]
    nine[10] = bar(10, hi="110")
    nine[20] = bar(20, lo="90")
    if side == "LONG":
        ten = (
            bar(60),
            bar(61, "96", "99", "89", "95"),
            bar(62, "95", "97", "93", "94"),
            bar(63, "94", "105", "93", "104"),
        )
    elif side == "SHORT":
        ten = (
            bar(60),
            bar(61, "104", "111", "102", "105"),
            bar(62, "105", "109", "103", "106"),
            bar(63, "106", "107", "94", "95"),
        )
    else:
        raise ValueError("SIDE_NOT_LONG_OR_SHORT")
    return tuple(nine), ten, ten[1:3]


def qualitative_protected_swing_court() -> dict[str, Any]:
    cases = []
    for month in (1, 7):
        for side in ("LONG", "SHORT"):
            nine, ten, series = make_fixture(side=side, month=month)
            at = ten[-1].closed_at
            valid = source_protected_swing(
                side=side, nine=nine, ten=ten, opposing_series=series, as_of=at,
            )
            if (
                valid.status != "RESEARCH_PROTECTED_SWING_SOURCE_CONTEXT_WITNESSED"
                or valid.protected_source_extreme != Decimal(
                    "89" if side == "LONG" else "111"
                )
                or valid.second_return_m1_wick_proxy != Decimal(
                    "93" if side == "LONG" else "109"
                )
            ):
                raise ValueError(f"PROTECTED_SWING_SOURCE_CONTEXT_DRIFT:{valid.record()}")
            cases.append({"case": f"{side}_{month}_SOURCE_WITNESS", **valid.record()})
            modified_final = M1Bar(
                ten[-1].opened_at, ten[-1].closed_at,
                ten[-1].open, ten[-1].high, ten[-1].low,
                Decimal("95" if side == "LONG" else "105"),
            )
            no_close = source_protected_swing(
                side=side, nine=nine, ten=ten[:-1]+(modified_final,),
                opposing_series=series, as_of=at,
            )
            if no_close.status != "PROTECTED_SWING_NOT_CONFIRMED_WAIT":
                raise ValueError(f"NO_PROTECTED_CLOSE_NOT_ABSTAINED:{no_close.record()}")
            cases.append({"case": f"{side}_{month}_NO_CONFIRMATION_WAIT",
                          **no_close.record()})
    return {
        "title": "VT31_TTRADES_PROTECTED_SWING_M5_AUTHOR_CONTEXT_NOT_BROKER_STOP",
        "prereg_commit": PREREG,
        "source_identity": SOURCE,
        "cases": cases,
        "author_full_displacement_causing_swing_identified": False,
        "g3_c2_stop_equivalence_claimed": False,
        "source_test_is_synthetic_m1": True,
        "human_method_review_completed": False,
        "methodology_certified": False,
        "cognition_certified": False,
        "pnl_or_return_evidence": None,
        "broker_orders": 0,
        "lot_sizing": 0,
        "live_authorized": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    out = p.parse_args().out
    record = qualitative_protected_swing_court()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "cases": [(c["case"], c["status"]) for c in record["cases"]],
        "methodology_certified": False, "cognition_certified": False,
    }))


if __name__ == "__main__":
    main()
