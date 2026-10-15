"""Qualitative TTrades method admissibility: falsify QORE OB / breaker proxies."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from scripts.vt31_m4_ob_breaker_author_evidence_gate_20261015 import (
    Candle,
    Swing,
    adjudicate_breaker,
    adjudicate_ob,
    synthetic_m4_source_dossier,
)

NY = ZoneInfo("America/New_YORK".replace("YORK", "York"))


def source_times():
    now = datetime(2025, 7, 15, 10, 15, tzinfo=NY)
    return now, now - timedelta(minutes=14), now - timedelta(minutes=10)


def _ob_args(side="LONG"):
    now, raid, shift = source_times()
    opposing = (
        Candle(
            now - timedelta(minutes=12),
            Decimal("103"), Decimal("104"), Decimal("100"), Decimal("101"),
        ) if side == "LONG" else
        Candle(
            now - timedelta(minutes=12),
            Decimal("101"), Decimal("104"), Decimal("100"), Decimal("103"),
        )
    )
    return {
        "profile": "TTRADES_NY_AM_2025",
        "side": side, "as_of": now,
        "first_raid_at": raid, "displacement_at": shift,
        "opposing_candles": (opposing,),
        "confluence_level": "H1_09_SOURCE_LIQUIDITY_SWEEP",
        "confluence_confirmed_at": raid,
        "retest": Candle(
            now, Decimal("102"), Decimal("103"), Decimal("100"), Decimal("102"),
        ),
    }


def _breaker_args(side="LONG"):
    now, raid, shift = source_times()
    kinds = ("LOW", "HIGH", "LOW", "HIGH") if side == "LONG" else (
        "HIGH", "LOW", "HIGH", "LOW",
    )
    nums = (100, 110, 95, 115) if side == "LONG" else (
        110, 100, 115, 95,
    )
    extrema = (26, 22, 15, 9)
    legs = tuple(
        Swing(
            kind, Decimal(str(value)),
            now - timedelta(minutes=delta),
            now - timedelta(minutes=delta-1),
        )
        for kind, value, delta in zip(kinds, nums, extrema, strict=True)
    )
    zone = (
        Candle(
            now - timedelta(minutes=24),
            Decimal("103"), Decimal("107"), Decimal("102"), Decimal("106"),
        ) if side == "LONG" else
        Candle(
            now - timedelta(minutes=24),
            Decimal("106"), Decimal("107"), Decimal("102"), Decimal("103"),
        )
    )
    return {
        "profile": "TTRADES_NY_AM_2025", "side": side,
        "as_of": now, "first_raid_at": raid, "displacement_at": shift,
        "swing_legs": legs, "zone_candles": (zone,),
        "retest": Candle(
            now, Decimal("105"), Decimal("107"), Decimal("103"), Decimal("105"),
        ),
    }


@pytest.mark.parametrize("side", ["LONG", "SHORT"])
def test_ob_requires_opposing_candle_sweep_confluence_and_body_close(side):
    args = _ob_args(side)
    good = adjudicate_ob(**args)
    assert good.status == "RESEARCH_OB_STRUCTURE_WITNESSED_AUTHOR_FINAL_PENDING"
    assert good.stop_source_status.startswith("M5_")
    assert good.author_full_method_certified is False
    assert good.cognition_certified is False
    missing_poi = adjudicate_ob(**(args | {"confluence_level": None}))
    assert missing_poi.status == "INSUFFICIENT_SOURCE_WITNESS"
    wrong_color = replace(
        args["opposing_candles"][0],
        open=Decimal("103") if side == "SHORT" else Decimal("101"),
        close=Decimal("101") if side == "SHORT" else Decimal("103"),
    )
    bad = adjudicate_ob(**(args | {"opposing_candles": (wrong_color,)}))
    assert bad.status == "INSUFFICIENT_SOURCE_WITNESS"


@pytest.mark.parametrize("side", ["LONG", "SHORT"])
def test_ob_retest_close_invalidates_but_wick_through_alone_not_enough(side):
    args = _ob_args(side)
    pierced = replace(
        args["retest"], low=Decimal("99"), high=Decimal("105"),
        close=Decimal("102"),
    )
    assert adjudicate_ob(**(args | {"retest": pierced})).status.startswith(
        "RESEARCH_OB_STRUCTURE_WITNESSED"
    )
    invalid = replace(
        args["retest"], low=Decimal("99"), high=Decimal("105"),
        close=Decimal("100") if side == "LONG" else Decimal("104"),
    )
    assert adjudicate_ob(**(args | {"retest": invalid})).status == (
        "SOURCE_OB_INVALIDATED"
    )


@pytest.mark.parametrize("side", ["LONG", "SHORT"])
def test_breaker_four_legs_and_directional_candle_zone_retest_required(side):
    args = _breaker_args(side)
    p = adjudicate_breaker(**args)
    assert p.status == "RESEARCH_BREAKER_STRUCTURE_WITNESSED_AUTHOR_FINAL_PENDING"
    assert p.operations_authorized is False
    lone = adjudicate_breaker(**(args | {"swing_legs": args["swing_legs"][:1]}))
    assert lone.status == "INSUFFICIENT_SOURCE_WITNESS"
    no_zone = adjudicate_breaker(**(args | {"zone_candles": ()}))
    assert no_zone.status == "INSUFFICIENT_SOURCE_WITNESS"


@pytest.mark.parametrize("side", ["LONG", "SHORT"])
def test_breaker_equal_level_does_not_count_as_strict_4th_leg(side):
    args = _breaker_args(side)
    leg2 = args["swing_legs"][1]
    bad = replace(args["swing_legs"][3], level=leg2.level)
    out = adjudicate_breaker(**(args | {
        "swing_legs": args["swing_legs"][:3] + (bad,),
    }))
    assert out.status == "INSUFFICIENT_SOURCE_WITNESS"


def test_future_swing_and_future_retest_cannot_be_used_as_source():
    args = _breaker_args()
    after = replace(
        args["swing_legs"][3],
        confirmed_at=args["as_of"] + timedelta(minutes=1),
    )
    future_leg = adjudicate_breaker(**(args | {
        "swing_legs": args["swing_legs"][:3] + (after,),
    }))
    assert future_leg.status == "CAUSAL_OR_PROFILE_REJECTED"
    premature = adjudicate_breaker(**(args | {
        "retest": replace(args["retest"], at=args["as_of"]-timedelta(minutes=9)),
    }))
    assert premature.status == "CAUSAL_OR_PROFILE_REJECTED"


def test_source_cannot_be_relabelled_as_ttrades_outside_nyam():
    args = _ob_args()
    invalid = adjudicate_ob(**(args | {
        "profile": "ICT_GENERAL_2023",
    }))
    assert invalid.status == "CAUSAL_OR_PROFILE_REJECTED"
    out = adjudicate_breaker(**(_breaker_args() | {
        "as_of": args["as_of"] + timedelta(hours=4),
        "retest": replace(args["retest"], at=args["as_of"]+timedelta(hours=4)),
    }))
    assert out.status == "CAUSAL_OR_PROFILE_REJECTED"


def test_intrabar_ambiguous_stop_target_never_counts_as_adequate_evidence():
    ob = adjudicate_ob(**(_ob_args() | {
        "intrabar_stop_target_ambiguous": True,
    }))
    breaker = adjudicate_breaker(**(_breaker_args() | {
        "intrabar_stop_target_ambiguous": True,
    }))
    assert ob.status == breaker.status == "SOURCE_STRUCTURE_UNDECIDABLE_INTRABAR"


def test_synthetic_examples_do_not_approve_method_or_cognition():
    result = synthetic_m4_source_dossier()
    assert result["old_qore_proxy_file_git_blob"] == (
        "c8b96c26fc60ae86c1fcccb0877354093b3782bb"
    )
    assert len(result["cases"]) == 9
    assert result["method_certified"] is False
    assert result["cognition_certified"] is False
    assert result["human_author_examples_independently_approved"] is False
    assert result["swing_stop_author_caused_leg_certified"] is False
    assert result["economic_data_or_pnl"] is None
    assert result["orders"] == result["sizing"] == 0
    assert result["live_authorized"] is False
    assert all(not x["author_full_method_certified"] and
               not x["cognition_certified"] and
               not x["human_author_example_approved"] and
               not x["operations_authorized"] and
               x["orders_placed"] == x["lot_sizing_actions"] == 0
               for x in result["cases"])
