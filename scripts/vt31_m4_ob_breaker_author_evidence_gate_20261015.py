#!/usr/bin/env python3
"""Author-source OB/Breaker admissibility: one VT31, NO new trading strategy.

TTrades source constraints are used to REJECT insufficient evidence. A passing
synthetic structure cannot certify author doctrine or the actual VT31 COG.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
PREREG = "0fd053f894428a3810d71ef079847fa6b73d4002"
OLD_OB_BREAKER_PROXY_BLOB = "c8b96c26fc60ae86c1fcccb0877354093b3782bb"
PROFILE = "TTRADES_NY_AM_2025"


@dataclass(frozen=True)
class Candle:
    at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def __post_init__(self) -> None:
        if not (self.low <= self.open <= self.high and
                self.low <= self.close <= self.high):
            raise ValueError("INVALID_M1_OHLC")


@dataclass(frozen=True)
class Swing:
    kind: str
    level: Decimal
    extreme_at: datetime
    confirmed_at: datetime


@dataclass(frozen=True)
class StructureJudgment:
    family: str
    status: str
    causes: tuple[str, ...]
    witness_known_before_retest: bool
    stop_source_status: str = "M5_DISPLACEMENT_CAUSAL_SWING_AUTHOR_UNVERIFIED"
    author_full_method_certified: bool = False
    cognition_certified: bool = False
    human_author_example_approved: bool = False
    operations_authorized: bool = False
    orders_placed: int = 0
    lot_sizing_actions: int = 0

    def record(self) -> dict[str, Any]:
        return {
            "family": self.family, "status": self.status,
            "causes": list(self.causes),
            "witness_known_before_retest": self.witness_known_before_retest,
            "stop_source_status": self.stop_source_status,
            "author_full_method_certified": self.author_full_method_certified,
            "cognition_certified": self.cognition_certified,
            "human_author_example_approved": self.human_author_example_approved,
            "operations_authorized": self.operations_authorized,
            "orders_placed": self.orders_placed,
            "lot_sizing_actions": self.lot_sizing_actions,
        }


def _clock(
    *, profile: str, at: datetime, first_raid_at: datetime,
    displacement_at: datetime, retest: Candle | None,
) -> tuple[str, ...]:
    errors = []
    if profile != PROFILE:
        errors.append("METHOD_PROFILE_MISMATCH")
    local = at.astimezone(NY)
    if local.hour != 10:
        errors.append("OUTSIDE_TTRADES_NYAM_WINDOW")
    if not (first_raid_at < displacement_at <= at):
        errors.append("RAID_MUST_PRECEDE_CONFIRMED_DISPLACEMENT")
    if (
        retest is None or retest.at > at
        or retest.at <= displacement_at
    ):
        errors.append("RETEST_MISSING_PREMATURE_OR_AFTER_ASOF")
    return tuple(errors)


def adjudicate_ob(
    *, profile: str, side: str, as_of: datetime,
    first_raid_at: datetime, displacement_at: datetime,
    opposing_candles: tuple[Candle, ...],
    confluence_level: str | None,
    confluence_confirmed_at: datetime | None,
    retest: Candle | None,
    intrabar_stop_target_ambiguous: bool = False,
) -> StructureJudgment:
    family = "ORDER_BLOCK_RETEST"
    clock = _clock(
        profile=profile, at=as_of, first_raid_at=first_raid_at,
        displacement_at=displacement_at, retest=retest,
    )
    if clock:
        return StructureJudgment(family, "CAUSAL_OR_PROFILE_REJECTED", clock, False)
    assert retest is not None
    if side not in {"LONG", "SHORT"}:
        return StructureJudgment(family, "INSUFFICIENT_SOURCE_WITNESS", ("SIDE_UNKNOWN",), False)
    if not opposing_candles:
        return StructureJudgment(
            family, "INSUFFICIENT_SOURCE_WITNESS", ("NO_OPPOSING_CANDLE_SERIES",), False,
        )
    if any(c.at >= displacement_at or c.at < first_raid_at for c in opposing_candles):
        return StructureJudgment(
            family, "CAUSAL_OR_PROFILE_REJECTED",
            ("OB_CANDLE_NOT_POST_RAID_PRE_DISPLACEMENT",), False,
        )
    if any(
        (c.close >= c.open if side == "LONG" else c.close <= c.open)
        for c in opposing_candles
    ):
        return StructureJudgment(
            family, "INSUFFICIENT_SOURCE_WITNESS",
            ("OPPOSING_CANDLE_COLOR_NOT_CONFIRMED",), False,
        )
    if any(
        a.at + timedelta(minutes=1) != z.at
        for a, z in zip(opposing_candles, opposing_candles[1:], strict=False)
    ):
        return StructureJudgment(
            family, "INSUFFICIENT_SOURCE_WITNESS",
            ("OPPOSING_CANDLE_SERIES_NOT_CONTIGUOUS",), False,
        )
    if (
        not confluence_level or confluence_confirmed_at is None
        or confluence_confirmed_at > displacement_at
    ):
        return StructureJudgment(
            family, "INSUFFICIENT_SOURCE_WITNESS",
            ("HTF_OR_LIQUIDITY_POINT_OF_INTEREST_NOT_ATTESTED",), False,
        )
    if intrabar_stop_target_ambiguous:
        return StructureJudgment(
            family, "SOURCE_STRUCTURE_UNDECIDABLE_INTRABAR",
            ("STOP_TARGET_INTRABAR_UNKNOWN",), False,
        )
    if len(opposing_candles) != 1:
        return StructureJudgment(
            family, "AUTHOR_ZONE_SELECTION_UNDERDETERMINED",
            ("MULTICANDLE_OB_BODY_MEAN_SELECTION_NOT_AUTHOR_FIXED",), True,
        )
    ob = opposing_candles[0]
    midpoint = (ob.open + ob.close) / 2
    if not ob.low <= retest.high or not retest.low <= ob.high:
        return StructureJudgment(
            family, "INSUFFICIENT_SOURCE_WITNESS", ("NO_OB_REGION_RETEST",), False,
        )
    # Check candle CLOSE, never label a wick-through as invalidation.
    invalidated = retest.close < midpoint if side == "LONG" else retest.close > midpoint
    if invalidated:
        return StructureJudgment(
            family, "SOURCE_OB_INVALIDATED",
            ("RETEST_CLOSE_BEYOND_BODY_MEAN_50_PERCENT",), True,
        )
    return StructureJudgment(
        family, "RESEARCH_OB_STRUCTURE_WITNESSED_AUTHOR_FINAL_PENDING",
        ("SINGLE_OB_CANDLE_HTF_CONFLUENCE_MEAN_RETEST_CLOSED_M1",), True,
    )


def adjudicate_breaker(
    *, profile: str, side: str, as_of: datetime,
    first_raid_at: datetime, displacement_at: datetime,
    swing_legs: tuple[Swing, ...], zone_candles: tuple[Candle, ...],
    retest: Candle | None, intrabar_stop_target_ambiguous: bool = False,
) -> StructureJudgment:
    family = "BREAKER_RETEST"
    clock = _clock(
        profile=profile, at=as_of, first_raid_at=first_raid_at,
        displacement_at=displacement_at, retest=retest,
    )
    if clock:
        return StructureJudgment(family, "CAUSAL_OR_PROFILE_REJECTED", clock, False)
    assert retest is not None
    if len(swing_legs) != 4:
        return StructureJudgment(
            family, "INSUFFICIENT_SOURCE_WITNESS",
            ("FOUR_SEPARATE_SWING_LEGS_NOT_PROVEN",), False,
        )
    if side not in ("LONG", "SHORT"):
        return StructureJudgment(family, "INSUFFICIENT_SOURCE_WITNESS", ("SIDE_UNKNOWN",), False)
    kind_expect = ("LOW", "HIGH", "LOW", "HIGH") if side == "LONG" else (
        "HIGH", "LOW", "HIGH", "LOW"
    )
    levels = [s.level for s in swing_legs]
    valid_levels = (
        levels[2] < levels[0] and levels[3] > levels[1]
        if side == "LONG" else levels[2] > levels[0] and levels[3] < levels[1]
    )
    if tuple(x.kind for x in swing_legs) != kind_expect or not valid_levels:
        return StructureJudgment(
            family, "INSUFFICIENT_SOURCE_WITNESS",
            ("LOW_HIGH_LOWER_LOW_HIGHER_HIGH_SEQUENCE_INVALID",), False,
        )
    if (
        any(x.confirmed_at > as_of or x.confirmed_at <= x.extreme_at for x in swing_legs)
        or any(
            a.extreme_at >= z.extreme_at or a.confirmed_at >= z.confirmed_at
            for a, z in zip(swing_legs, swing_legs[1:], strict=False)
        )
        or swing_legs[-1].confirmed_at >= retest.at
    ):
        return StructureJudgment(
            family, "CAUSAL_OR_PROFILE_REJECTED",
            ("FOUR_SWINGS_FUTURE_OR_RETEST_BEFORE_CONFIRMED_FOURTH",), False,
        )
    if not zone_candles:
        return StructureJudgment(
            family, "INSUFFICIENT_SOURCE_WITNESS",
            ("BLOCK_DIRECTIONAL_CANDLE_ZONE_MISSING",), False,
        )
    if any(
        c.at > as_of or not (swing_legs[0].extreme_at <= c.at <= swing_legs[1].extreme_at)
        or (c.close <= c.open if side == "LONG" else c.close >= c.open)
        for c in zone_candles
    ):
        return StructureJudgment(
            family, "INSUFFICIENT_SOURCE_WITNESS",
            ("BLOCK_SERIES_DIRECTION_OR_SOURCE_TIME_INVALID",), False,
        )
    zone_low = min(c.low for c in zone_candles)
    zone_high = max(c.high for c in zone_candles)
    if retest.low > zone_high or retest.high < zone_low:
        return StructureJudgment(
            family, "INSUFFICIENT_SOURCE_WITNESS",
            ("NO_CLOSED_M1_RETEST_OF_BREAKER_ZONE",), False,
        )
    if intrabar_stop_target_ambiguous:
        return StructureJudgment(
            family, "SOURCE_STRUCTURE_UNDECIDABLE_INTRABAR",
            ("STOP_TARGET_INTRABAR_UNKNOWN",), False,
        )
    if len(zone_candles) > 1:
        return StructureJudgment(
            family, "AUTHOR_ZONE_SELECTION_UNDERDETERMINED",
            ("MULTICANDLE_BREAKER_ZONE_BOUNDS_NEED_INDEPENDENT_AUTHOR_CASE",), True,
        )
    return StructureJudgment(
        family, "RESEARCH_BREAKER_STRUCTURE_WITNESSED_AUTHOR_FINAL_PENDING",
        ("FOUR_CAUSAL_SWINGS_DIRECTIONAL_ZONE_LATER_RETEST_WITNESSED",), True,
    )


def synthetic_m4_source_dossier() -> dict[str, Any]:
    anchor = datetime(2025, 7, 15, 10, 15, tzinfo=NY)
    raid = anchor - timedelta(minutes=14)
    disp = anchor - timedelta(minutes=10)
    ob = Candle(
        anchor - timedelta(minutes=12),
        Decimal("103"), Decimal("104"), Decimal("100"), Decimal("101"),
    )
    ob_retest = Candle(
        anchor, Decimal("102"), Decimal("103"), Decimal("100"), Decimal("102"),
    )
    cases = []
    def append(name: str, judgment: StructureJudgment) -> None:
        cases.append({"case": name, **judgment.record()})
    good_ob = dict(
        profile=PROFILE, side="LONG", as_of=anchor,
        first_raid_at=raid, displacement_at=disp,
        opposing_candles=(ob,), confluence_level="FIRST_09H_H1_LOW_RAID",
        confluence_confirmed_at=raid,
        retest=ob_retest,
    )
    append("OB_ONE_CANDLE_CONTEXTUAL_NO_MEAN_CLOSE_BREAK",
           adjudicate_ob(**good_ob))
    append("OB_MISSING_HTF_CONFLUENCE",
           adjudicate_ob(**(good_ob | {"confluence_level": None})))
    append("OB_MEAN_INVALIDATED_BY_CLOSE",
           adjudicate_ob(**(good_ob | {"retest": Candle(
               anchor, Decimal("102"), Decimal("103"), Decimal("99"), Decimal("100")
           )})))
    append("OB_MULTICANDLE_UNRESOLVED_ZONE",
           adjudicate_ob(**(good_ob | {
               "opposing_candles": (
                   Candle(anchor-timedelta(minutes=13), Decimal("105"),
                          Decimal("106"), Decimal("102"), Decimal("103")),
                   ob,
               )})))
    legs = (
        Swing("LOW", Decimal("100"), anchor-timedelta(minutes=26),
              anchor-timedelta(minutes=25)),
        Swing("HIGH", Decimal("110"), anchor-timedelta(minutes=22),
              anchor-timedelta(minutes=21)),
        Swing("LOW", Decimal("95"), anchor-timedelta(minutes=15),
              anchor-timedelta(minutes=14)),
        Swing("HIGH", Decimal("115"), anchor-timedelta(minutes=9),
              anchor-timedelta(minutes=8)),
    )
    breaker_zone = Candle(
        anchor-timedelta(minutes=24), Decimal("103"),
        Decimal("107"), Decimal("102"), Decimal("106"),
    )
    breaker_retest = Candle(
        anchor, Decimal("106"), Decimal("107"), Decimal("103"), Decimal("105"),
    )
    good_breaker = dict(
        profile=PROFILE, side="LONG", as_of=anchor,
        first_raid_at=raid, displacement_at=disp,
        swing_legs=legs, zone_candles=(breaker_zone,),
        retest=breaker_retest,
    )
    append("BREAKER_FOUR_LEGS_ZONE_AFTER_RETEST",
           adjudicate_breaker(**good_breaker))
    append("BREAKER_ONLY_ONE_PIVOT_IS_NOT_A_METHOD",
           adjudicate_breaker(**(good_breaker | {"swing_legs": legs[:1]})))
    append("BREAKER_NO_FOURTH_HIGH",
           adjudicate_breaker(**(good_breaker | {
               "swing_legs": legs[:3] + (Swing(
                   "HIGH", Decimal("109"),
                   legs[-1].extreme_at, legs[-1].confirmed_at,
               ),)})))
    append("BREAKER_NO_ZONE",
           adjudicate_breaker(**(good_breaker | {"zone_candles": ()})))
    append("BREAKER_ZONE_RETEST_PREMATURE",
           adjudicate_breaker(**(good_breaker | {
               "retest": Candle(
                   anchor-timedelta(minutes=9), Decimal("106"),
                   Decimal("107"), Decimal("103"), Decimal("105"),
               )})))
    results = [x["status"] for x in cases]
    expected = [
        "RESEARCH_OB_STRUCTURE_WITNESSED_AUTHOR_FINAL_PENDING",
        "INSUFFICIENT_SOURCE_WITNESS",
        "SOURCE_OB_INVALIDATED",
        "AUTHOR_ZONE_SELECTION_UNDERDETERMINED",
        "RESEARCH_BREAKER_STRUCTURE_WITNESSED_AUTHOR_FINAL_PENDING",
        "INSUFFICIENT_SOURCE_WITNESS",
        "INSUFFICIENT_SOURCE_WITNESS",
        "INSUFFICIENT_SOURCE_WITNESS",
        "CAUSAL_OR_PROFILE_REJECTED",
    ]
    if results != expected:
        raise ValueError(f"QUALITATIVE_SOURCE_GATE_EXPECTATION_DRIFT:{results}")
    return {
        "prereg_commit": PREREG,
        "old_qore_proxy_file_git_blob": OLD_OB_BREAKER_PROXY_BLOB,
        "primary_sources": (
            "https://ttrades.com/order-blocks-simplified/",
            "https://ttrades.com/breaker-blocks-simplified/",
            "https://ttrades.com/the-am-silver-bullet-strategy-on-nq/",
        ),
        "cases": cases,
        "method_certified": False,
        "cognition_certified": False,
        "human_author_examples_independently_approved": False,
        "swing_stop_author_caused_leg_certified": False,
        "source_data_type": "SYNTHETIC_M1_ANNOTATED_NOT_AUTHOR_CHART",
        "economic_data_or_pnl": None,
        "orders": 0,
        "sizing": 0,
        "live_authorized": False,
    }


def main() -> None:
    arg = argparse.ArgumentParser()
    arg.add_argument("--out", type=Path, required=True)
    out = arg.parse_args().out
    data = synthetic_m4_source_dossier()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n")
    print(json.dumps(
        {"verdicts": [(x["case"], x["status"]) for x in data["cases"]],
         "method_certified": data["method_certified"]}, sort_keys=True,
    ))


if __name__ == "__main__":
    main()
