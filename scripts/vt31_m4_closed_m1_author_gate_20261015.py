#!/usr/bin/env python3
"""VT31 M4 V2: reject unfinished M1 retests before existing OB/Breaker gate.

Research only. Original M4 source gate and protected G3 COG/OPS stay unchanged.
Author completeness, displacement-causing swing and stop are NOT certified.
Prereg: ce4047201ec27ac4a3e98d854c07606e6e2f30d2.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    NEW_YORK,
    utc,
)
from scripts.vt31_m4_ob_breaker_author_evidence_gate_20261015 import (
    PROFILE,
    Candle,
    Swing,
    adjudicate_breaker,
    adjudicate_ob,
)

PREREG = "ce4047201ec27ac4a3e98d854c07606e6e2f30d2"
VERSION = "VT31_M4_V2_CLOSED_M1_CAUSAL_SOURCE_ADMISSION_RESEARCH"
REJECTED = "M4_CAUSAL_PRE_ADMISSION_REJECTED"
OBSERVED = "M4_CLOSED_M1_SOURCE_STRUCTURE_RESEARCH_ONLY"
INSUFFICIENT = "M4_SOURCE_STRUCTURE_UNDECIDABLE_WAIT"


@dataclass(frozen=True, slots=True)
class M4ClosedM1Verdict:
    family: str
    state: str
    reason: str
    source_v1_status: str | None = None
    legacy_source_gate_invoked: bool = False
    cognitive_action: str = "WAIT"
    author_method_certified: bool = False
    cognition_certified: bool = False
    displacement_causing_stop_certified: bool = False
    broker_order_authorized: bool = False
    lot_sizing_performed: bool = False

    def record(self) -> dict[str, Any]:
        return {
            "version": VERSION,
            "family": self.family,
            "state": self.state,
            "reason": self.reason,
            "source_v1_status": self.source_v1_status,
            "legacy_source_gate_invoked": self.legacy_source_gate_invoked,
            "cognitive_action": self.cognitive_action,
            "author_method_certified": self.author_method_certified,
            "cognition_certified": self.cognition_certified,
            "displacement_causing_stop_certified": self.displacement_causing_stop_certified,
            "broker_order_authorized": self.broker_order_authorized,
            "lot_sizing_performed": self.lot_sizing_performed,
        }


def adjudicate_closed_m1_retest(
    *,
    family: str,
    profile: str,
    side: str,
    as_of: datetime,
    first_raid_at: datetime,
    displacement_at: datetime,
    retest: Candle | None,
    opposing_candles: tuple[Candle, ...] = (),
    confluence_level: str | None = None,
    confluence_confirmed_at: datetime | None = None,
    swing_legs: tuple[Swing, ...] = (),
    zone_candles: tuple[Candle, ...] = (),
    intrabar_stop_target_ambiguous: bool = False,
) -> M4ClosedM1Verdict:
    """Causal boundary first, original source-only judge second, never an order."""

    def rejected(reason: str) -> M4ClosedM1Verdict:
        return M4ClosedM1Verdict(family, REJECTED, reason)

    if family not in ("ORDER_BLOCK_RETEST", "BREAKER_RETEST"):
        return rejected("M4_FAMILY_NOT_DEFINED")
    if profile != PROFILE or side not in ("LONG", "SHORT"):
        return rejected("M4_PROFILE_OR_SIDE_NOT_TTRADES_NYAM")
    if retest is None or not isinstance(retest, Candle):
        return rejected("CLOSED_M1_RETEST_REQUIRED")
    if not isinstance(opposing_candles, tuple) or not isinstance(zone_candles, tuple):
        return rejected("IMMUTABLE_SOURCE_CANDLE_SERIES_REQUIRED")
    if not isinstance(swing_legs, tuple):
        return rejected("IMMUTABLE_FOUR_SWINGS_REQUIRED")

    stamps = [as_of, first_raid_at, displacement_at, retest.at]
    if confluence_confirmed_at is not None:
        stamps.append(confluence_confirmed_at)
    for candle in (*opposing_candles, *zone_candles):
        if not isinstance(candle, Candle):
            return rejected("SOURCE_CANDLE_NOT_TYPED")
        stamps.append(candle.at)
    for swing in swing_legs:
        if not isinstance(swing, Swing):
            return rejected("SOURCE_SWING_NOT_TYPED")
        stamps.extend((swing.extreme_at, swing.confirmed_at))
    try:
        clock = [utc(stamp) for stamp in stamps]
    except (ValueError, TypeError):
        return rejected("NAIVE_OR_INVALID_SOURCE_TIMESTAMP")
    if any(stamp.second or stamp.microsecond for stamp in clock):
        return rejected("NON_MINUTE_ALIGNED_SOURCE_TIMESTAMP")
    at, raid, displacement, retest_open = clock[:4]
    retest_closed = retest_open + timedelta(minutes=1)

    if at != retest_closed:
        return rejected("RETEST_M1_NOT_EXACTLY_CLOSED_AT_ASOF")
    local_open = retest_open.astimezone(NEW_YORK)
    local_close = at.astimezone(NEW_YORK)
    if (
        local_open.date() != local_close.date()
        or local_open.hour != 10
        or not (10 <= local_close.hour <= 11)
        or (local_close.hour == 11 and local_close.minute != 0)
    ):
        return rejected("RETEST_OUTSIDE_TTRADES_NYAM_WINDOW")
    if not (raid < displacement <= retest_open):
        return rejected("RAID_DISPLACEMENT_RETEST_CAUSAL_ORDER_INVALID")
    if (
        raid.astimezone(NEW_YORK).date() != local_open.date()
        or displacement.astimezone(NEW_YORK).date() != local_open.date()
        or raid.astimezone(NEW_YORK).hour != 10
        or displacement.astimezone(NEW_YORK).hour != 10
    ):
        return rejected("RAID_OR_DISPLACEMENT_OUTSIDE_SAME_NYAM_SESSION")
    if confluence_confirmed_at is not None and utc(confluence_confirmed_at) > displacement:
        return rejected("FUTURE_HTF_OR_POI_CONFLUENCE")
    if family == "ORDER_BLOCK_RETEST":
        if swing_legs or zone_candles:
            return rejected("UNDECLARED_MIXED_FAMILY_INPUT")
        if any(utc(c.at) + timedelta(minutes=1) > displacement for c in opposing_candles):
            return rejected("OB_SOURCE_CANDLE_NOT_CLOSED_AT_DISPLACEMENT")
        judgment = adjudicate_ob(
            profile=profile, side=side, as_of=at,
            first_raid_at=raid, displacement_at=displacement,
            opposing_candles=opposing_candles,
            confluence_level=confluence_level,
            confluence_confirmed_at=confluence_confirmed_at,
            retest=retest,
            intrabar_stop_target_ambiguous=intrabar_stop_target_ambiguous,
        )
        positive = "RESEARCH_OB_STRUCTURE_WITNESSED_AUTHOR_FINAL_PENDING"
    else:
        if opposing_candles or confluence_level or confluence_confirmed_at is not None:
            return rejected("UNDECLARED_MIXED_FAMILY_INPUT")
        if any(utc(c.at) + timedelta(minutes=1) > retest_open for c in zone_candles):
            return rejected("BREAKER_ZONE_CANDLE_FUTURE_OR_NOT_CLOSED")
        if any(utc(s.confirmed_at) > retest_open for s in swing_legs):
            return rejected("SWING_NOT_CONFIRMED_BEFORE_RETEST")
        judgment = adjudicate_breaker(
            profile=profile, side=side, as_of=at,
            first_raid_at=raid, displacement_at=displacement,
            swing_legs=swing_legs, zone_candles=zone_candles,
            retest=retest,
            intrabar_stop_target_ambiguous=intrabar_stop_target_ambiguous,
        )
        positive = "RESEARCH_BREAKER_STRUCTURE_WITNESSED_AUTHOR_FINAL_PENDING"
    return M4ClosedM1Verdict(
        family=family,
        state=OBSERVED if judgment.status == positive else INSUFFICIENT,
        reason=(
            "CAUSAL_M1_CLOSED_BUT_M3_M4_M5_AUTHOR_METHOD_STILL_UNCERTIFIED"
            if judgment.status == positive else "SOURCE_V1_WITNESS_NONCONFORMANT_OR_UNKNOWN"
        ),
        source_v1_status=judgment.status,
        legacy_source_gate_invoked=True,
    )


def fixture_case(
    *, family: str, side: str, month: int,
) -> dict[str, Any]:
    """Fixed geometric research fixtures; neither author screenshots nor market data."""
    if month not in (1, 7) or side not in ("LONG", "SHORT"):
        raise ValueError("FIXTURE_EST_EDT_AND_LONG_SHORT_ONLY")
    at = datetime(2026, month, 15, 10, 16, tzinfo=NEW_YORK)
    raid = at - timedelta(minutes=15)
    displacement = at - timedelta(minutes=11)
    rest = Candle(
        at - timedelta(minutes=1),
        Decimal("105"), Decimal("107"), Decimal("100"), Decimal("105"),
    )
    base: dict[str, Any] = {
        "family": family, "profile": PROFILE, "side": side,
        "as_of": at, "first_raid_at": raid,
        "displacement_at": displacement, "retest": rest,
    }
    if family == "ORDER_BLOCK_RETEST":
        candle = Candle(
            at - timedelta(minutes=13),
            Decimal("103") if side == "LONG" else Decimal("101"),
            Decimal("104"), Decimal("100"),
            Decimal("101") if side == "LONG" else Decimal("103"),
        )
        return base | {
            "opposing_candles": (candle,),
            "confluence_level": "H1_09_SOURCE_LIQUIDITY_CONTEXT_NOT_AUTHOR_CERT",
            "confluence_confirmed_at": raid,
        }
    if family == "BREAKER_RETEST":
        kinds = ("LOW", "HIGH", "LOW", "HIGH") if side == "LONG" else (
            "HIGH", "LOW", "HIGH", "LOW"
        )
        levels = ("100", "110", "95", "115") if side == "LONG" else (
            "110", "100", "115", "95"
        )
        offsets = (27, 23, 16, 10)
        legs = tuple(
            Swing(kind, Decimal(value), at - timedelta(minutes=offset),
                  at - timedelta(minutes=offset - 1))
            for kind, value, offset in zip(kinds, levels, offsets, strict=True)
        )
        zone = Candle(
            at - timedelta(minutes=25),
            Decimal("103") if side == "LONG" else Decimal("106"),
            Decimal("107"), Decimal("102"),
            Decimal("106") if side == "LONG" else Decimal("103"),
        )
        return base | {"swing_legs": legs, "zone_candles": (zone,)}
    raise ValueError("UNKNOWN_M4_FIXTURE_FAMILY")


def m4_closed_m1_court() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for family in ("ORDER_BLOCK_RETEST", "BREAKER_RETEST"):
        for side in ("LONG", "SHORT"):
            for month in (1, 7):
                args = fixture_case(family=family, side=side, month=month)
                good = adjudicate_closed_m1_retest(**args)
                if good.state != OBSERVED or not good.legacy_source_gate_invoked:
                    raise ValueError(f"M4_CLOSED_M1_SOURCE_GATE_DRIFT:{args}:{good}")
                cases.append({
                    "case": f"{family}_{side}_{month}_CLOSED_SOURCE",
                    **good.record(),
                })
                unclosed = adjudicate_closed_m1_retest(
                    **(args | {"as_of": args["retest"].at})
                )
                if unclosed.state != REJECTED or unclosed.legacy_source_gate_invoked:
                    raise ValueError(f"UNCLOSED_SOURCE_WAS_USED:{unclosed}")
                cases.append({
                    "case": f"{family}_{side}_{month}_UNCLOSED_REJECT",
                    **unclosed.record(),
                })
    return {
        "title": VERSION,
        "prereg_commit": PREREG,
        "source_primary": [
            "https://ttrades.com/the-am-silver-bullet-strategy-on-nq/",
            "https://ttrades.com/order-blocks-simplified/",
            "https://ttrades.com/breaker-blocks-simplified/",
        ],
        "synthetic_m1_geometry_only": True,
        "cases": cases,
        "methodology_certified": False,
        "cognition_certified": False,
        "owner_signed_m0": False,
        "dual_cog_ops_signatures": False,
        "stop_causing_displacement_identified": False,
        "broker_orders": 0,
        "sizing": 0,
        "live": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True, type=Path)
    dest = p.parse_args().out
    record = m4_closed_m1_court()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "cases": len(record["cases"]),
        "closed_structure_research": sum(
            x["state"] == OBSERVED for x in record["cases"]
        ),
        "uncausal_rejected": sum(
            x["state"] == REJECTED for x in record["cases"]
        ),
        "methodology_certified": False,
        "cognition_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
