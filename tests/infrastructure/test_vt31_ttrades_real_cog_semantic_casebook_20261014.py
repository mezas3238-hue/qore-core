"""Adversarial original native TTrades M1 COG method/cognition dossier."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar
from scripts.vt31_ttrades_am_method_m1_census_20261014 import adjudicate_day
from scripts.vt31_ttrades_real_cog_semantic_casebook_20261014 import (
    CANONICAL_CLASSES,
    inspect_real_day,
)

NY = ZoneInfo("America/New_York")


def bar(at, o="100", h="102", lo="98", c="101"):
    return M1Bar(
        at, at+timedelta(minutes=1),
        Decimal(o), Decimal(h), Decimal(lo), Decimal(c),
    )


def sample(month=7, direction="LONG"):
    d = 1 if month == 7 else 15
    start9 = datetime(2025, month, d, 9, tzinfo=NY).astimezone(UTC)
    start10 = datetime(2025, month, d, 10, tzinfo=NY).astimezone(UTC)
    nine = [bar(start9+timedelta(minutes=i)) for i in range(60)]
    nine[10] = bar(start9+timedelta(minutes=10), h="110")
    nine[20] = bar(start9+timedelta(minutes=20), lo="90")
    ten = [bar(start10+timedelta(minutes=i)) for i in range(60)]
    if direction == "LONG":
        nine[57] = bar(start9+timedelta(minutes=57), h="104")
        ten[0] = bar(start10, o="100", c="100")
        ten[1] = bar(start10+timedelta(minutes=1), o="96", h="99", lo="89", c="95")
        ten[2] = bar(start10+timedelta(minutes=2), o="94", h="106", lo="93", c="105")
    else:
        nine[57] = bar(start9+timedelta(minutes=57), lo="96")
        ten[0] = bar(start10, o="100", c="100")
        ten[1] = bar(start10+timedelta(minutes=1), o="104", h="111", lo="103", c="105")
        ten[2] = bar(start10+timedelta(minutes=2), o="106", h="107", lo="94", c="95")
    return str(start9.astimezone(NY).date()), tuple(nine), tuple(ten)


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", ["LONG", "SHORT"])
def test_real_native_emitter_m2_opposite_h1_source_not_fill(month, side):
    day, nine, ten = sample(month, side)
    census = adjudicate_day(nine, ten)
    assert census["classification"] == "MSS_ATTESTED_CONTEXT_ONLY"
    r = inspect_real_day(day=day, nine=nine, ten=ten, census=census)
    assert r["native_cog_emitted_proposal"] is True
    assert r["expected_direction_from_raid"] == side
    assert r["semantic_m2_raid_and_dol"] == (
        "AUTHORIAL_H1_RAID_TARGET_CONTEXT_CONFORMANT"
    ), r
    assert r["independent_926"] == "CONTEXT_CONFORMANT_ONLY"
    assert r["independent_v2"] == "CONFIRMED"
    assert r["semantic_m3_mss_displacement"] == "QORE_PROXY_NOT_AUTHOR_CERTIFIED"
    assert not r["methodology_certified"]
    assert not r["cognition_certified"]
    assert not r["trader_order_or_fill"]


def test_no_raid_means_no_intent_even_without_explicit_top_level_wait():
    day, nine, ten = sample()
    start = ten[0].opened_at
    no_sweep = tuple(bar(start+timedelta(minutes=i)) for i in range(60))
    census = adjudicate_day(nine, no_sweep)
    assert census["classification"] == "NO_SWEEP"
    r = inspect_real_day(day=day, nine=nine, ten=no_sweep, census=census)
    assert not r["native_cog_emitted_proposal"]
    assert r["top_level_cog_state"] == "UNKNOWN"
    assert r["native_source_state"] == "AWAIT_SWEEP"
    assert r["cog_native_source_wait"] is True
    assert r["cog_top_level_explicit_wait"] is False
    assert r["semantic_abstention"] == "SOURCE_CONDITION_UNFULFILLED_NO_INTENT"


def test_no_confirmed_qore_mss_is_no_intent_not_method_failure():
    day, nine, ten = sample()
    third = ten[2]
    ten = ten[:2] + (
        bar(third.opened_at, o="94", h="103", lo="93", c="100"),
    ) + ten[3:]
    census = adjudicate_day(nine, ten)
    assert census["classification"] == "FIRST_RETURN_NO_QORE_MSS"
    r = inspect_real_day(day=day, nine=nine, ten=ten, census=census)
    assert not r["native_cog_emitted_proposal"]
    assert "QORE_MSS_PROXY_NOT_CONFIRMED_ON_FIRST_RETURN" in r["cog_reasons"]
    assert r["semantic_m3_mss_displacement"] == "QORE_PROXY_NOT_AUTHOR_CERTIFIED"


def test_incomplete_9am_hour_is_unknown_not_synthetic_cog():
    day, nine, ten = sample()
    r = inspect_real_day(
        day=day, nine=nine[1:], ten=ten,
        census={"classification": "INCOMPLETE_M1_HOURS"},
    )
    assert r["semantic_m1_causal"] == "UNKNOWN_INCOMPLETE_SOURCE"
    assert r["semantic_m2_raid_and_dol"].startswith("NOT_EVALUABLE")
    assert r["native_cog_emitted_proposal"] is False


def test_frozen_categories_cover_no_trade_without_fabricated_results():
    assert sum(CANONICAL_CLASSES.values()) == 775
    assert "FIRST_RETURN_NO_QORE_MSS" in CANONICAL_CLASSES
    assert "INCOMPLETE_M1_HOURS" in CANONICAL_CLASSES


def test_adversarial_post_asof_future_m1_cannot_rewrite_exemplar():
    day, nine, ten = sample()
    original = adjudicate_day(nine, ten)
    result = inspect_real_day(day=day, nine=nine, ten=ten, census=original)
    extra = ten[:3] + tuple(
        bar(x.opened_at, o="100", h="1000", lo="1", c="100")
        for x in ten[3:]
    )
    # Original event is in first 3 closed M1; later bars are excluded.
    altered = inspect_real_day(day=day, nine=nine, ten=extra, census=original)
    assert result == altered
