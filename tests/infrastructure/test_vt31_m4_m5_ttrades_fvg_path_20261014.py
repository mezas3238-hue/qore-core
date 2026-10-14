"""M4/M5 no-order FVG source witness + first choice / full wick adversaries."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    Side,
)
from scripts.vt31_m4_m5_ttrades_fvg_path_20261014 import (
    first_fvg_and_source_path,
)
from scripts.vt31_ttrades_am_native_cog_v1_20261014 import (
    propose_ttrades_am_cognition,
)

NY = ZoneInfo("America/New_York")


def bar(
    at: datetime, o: str = "100", h: str = "102",
    low: str = "98", c: str = "101",
) -> M1Bar:
    return M1Bar(
        at, at + timedelta(minutes=1),
        Decimal(o), Decimal(h), Decimal(low), Decimal(c),
    )


def market(
    side: Side = Side.LONG, month: int = 7,
) -> tuple[tuple[M1Bar, ...], tuple[M1Bar, ...]]:
    start9 = datetime(2025, month, 15, 9, tzinfo=NY).astimezone(UTC)
    start10 = datetime(2025, month, 15, 10, tzinfo=NY).astimezone(UTC)
    nine = [bar(start9 + timedelta(minutes=i)) for i in range(60)]
    nine[10] = bar(
        start9 + timedelta(minutes=10),
        h="130" if side is Side.LONG else "110",
    )
    nine[20] = bar(
        start9 + timedelta(minutes=20),
        low="90" if side is Side.LONG else "70",
    )
    nine[57] = (
        bar(start9 + timedelta(minutes=57), h="104")
        if side is Side.LONG
        else bar(start9 + timedelta(minutes=57), low="96")
    )
    if side is Side.LONG:
        ten = (
            bar(start10, c="100"),
            bar(start10 + timedelta(minutes=1), "96", "99", "89", "95"),
            bar(start10 + timedelta(minutes=2), "94", "106", "93", "105"),
            bar(start10 + timedelta(minutes=3), "105", "108", "104", "107"),
            bar(start10 + timedelta(minutes=4), "108", "112", "107", "111"),
        )
    else:
        ten = (
            bar(start10, c="100"),
            bar(start10 + timedelta(minutes=1), "104", "111", "103", "105"),
            bar(start10 + timedelta(minutes=2), "106", "107", "94", "95"),
            bar(start10 + timedelta(minutes=3), "95", "96", "91", "92"),
            bar(start10 + timedelta(minutes=4), "91", "93", "88", "90"),
        )
    return tuple(nine), ten


def proposal(nine, ten):
    r = propose_ttrades_am_cognition(
        as_of=ten[2].closed_at, history=nine + ten[:3],
    )
    assert r.state == "CONTEXT_ATTESTED_NOT_CERTIFIED", r.record()
    assert r.decision is not None
    return r.decision


@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
@pytest.mark.parametrize("month", [1, 7])
def test_native_mss_to_first_fvg_form_and_full_wick(month, side):
    nine, ten = market(side, month)
    cognition = proposal(nine, ten)
    witness = first_fvg_and_source_path(
        nine=nine, ten=ten[:4], cognition=cognition,
    )
    assert witness.state == "FVG_GEOMETRY_ATTESTED_NOT_EXECUTABLE", witness
    assert witness.first_fvg_confirmed_at == ten[3].closed_at
    assert witness.side is side
    assert witness.ce_research_only == Decimal(
        "101.5" if side is Side.LONG else "99.5"
    )
    assert witness.c2_full_wick_reference == Decimal(
        "93" if side is Side.LONG else "107"
    )
    assert witness.potential_points_at_mss == Decimal(
        "25" if side is Side.LONG else "25"
    )
    assert witness.source_path_state == "BROKER_TICK_AND_QUOTE_UNATTESTED"
    assert not witness.filled and not witness.execution_authorized
    assert not witness.method_certified
    assert "stop" not in witness.record()
    assert "lot_size" not in witness.record()


def test_early_source_never_uses_future_c3():
    nine, ten = market()
    cog = proposal(nine, ten)
    assert first_fvg_and_source_path(
        nine=nine, ten=ten[:3], cognition=cog,
    ).state == "NO_ELIGIBLE_FVG"


def test_no_fvg_on_non_strict_gap():
    nine, ten = market()
    cog = proposal(nine, ten)
    changed = bar(ten[3].opened_at, "105", "108", "99", "107")
    out = first_fvg_and_source_path(
        nine=nine, ten=ten[:3] + (changed,), cognition=cog,
    )
    assert out.state == "NO_ELIGIBLE_FVG"


def test_minimum_10_points_from_mss_not_c3_close():
    nine, ten = market()
    cog = proposal(nine, ten)
    # Frozen cognition with less than ten points, never change MSS anchor.
    small = replace(cog, draw_target=Decimal("109"))
    out = first_fvg_and_source_path(
        nine=nine, ten=ten[:4], cognition=small,
    )
    assert out.state == "REJECTED"  # immutable source target mismatch


def test_any_source_target_mismatch_fails_closed():
    nine, ten = market()
    cog = proposal(nine, ten)
    out = first_fvg_and_source_path(
        nine=nine, ten=ten[:4],
        cognition=replace(cog, draw_target=Decimal("300")),
    )
    assert out.state == "REJECTED"


def test_mss_close_corrupted_without_changing_price_source_is_rejected():
    nine, ten = market()
    cog = proposal(nine, ten)
    out = first_fvg_and_source_path(
        nine=nine, ten=ten[:4],
        cognition=replace(cog, mss_anchor_close=Decimal("108")),
    )
    assert out.state == "REJECTED"
    assert "MSS_ANCHOR_INCONSISTENT_WITH_M1_DATA" in out.reasons


def test_ce_observed_after_c3_not_a_broker_fill():
    nine, ten = market()
    cog = proposal(nine, ten)
    after = bar(ten[4].opened_at, "107", "110", "101", "108")
    out = first_fvg_and_source_path(
        nine=nine, ten=ten[:4] + (after,), cognition=cog,
    )
    assert out.state == "FVG_GEOMETRY_ATTESTED_NOT_EXECUTABLE"
    assert out.source_path_state == "TOUCH_NOT_FILL"
    assert out.path_observation_at == after.closed_at
    assert not out.filled


def test_touch_and_cancel_same_closed_m1_is_ambiguous():
    nine, ten = market()
    cog = proposal(nine, ten)
    conflict = bar(ten[4].opened_at, "107", "110", "96", "97")
    out = first_fvg_and_source_path(
        nine=nine, ten=ten[:4] + (conflict,), cognition=cog,
    )
    assert out.source_path_state == "AMBIGUOUS_M1_SEQUENCE_NO_FILL"
    assert not out.filled


def test_close_beyond_fvg_but_no_ce_touch_is_postclose_cancel_only():
    nine, ten = market()
    cog = proposal(nine, ten)
    invalid = bar(ten[4].opened_at, "98", "99", "96", "97")
    out = first_fvg_and_source_path(
        nine=nine, ten=ten[:4] + (invalid,), cognition=cog,
    )
    assert out.source_path_state == "INVALIDATED_AT_M1_CLOSE_NO_ORDER"
    assert out.path_observation_at == invalid.closed_at


def test_first_eligible_fvg_persists_even_if_second_available():
    nine, ten = market()
    cog = proposal(nine, ten)
    out = first_fvg_and_source_path(
        nine=nine, ten=ten, cognition=cog,
    )
    assert out.first_fvg_confirmed_at == ten[3].closed_at
    assert out.c2_full_wick_reference == ten[2].low


def test_closed_m1_gaps_no_fvg_or_exec():
    nine, ten = market()
    cog = proposal(nine, ten)
    out = first_fvg_and_source_path(
        nine=nine, ten=ten[:3] + ten[4:], cognition=cog,
    )
    assert out.state == "UNKNOWN"
    assert "CLOSED_M1_GAP_OR_DUPLICATE" in out.reasons


def test_first_return_but_bad_profile_cannot_pass_m4():
    nine, ten = market()
    cog = proposal(nine, ten)
    # No order object is ever produced or broker fills claimed.
    result = first_fvg_and_source_path(
        nine=nine, ten=ten[:4], cognition=cog,
    ).record()
    assert result["execution_authorized"] is False
    assert result["filled"] is False
    assert result["method_certified"] is False
    assert result["ce_research_only"] == "101.5"


@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_real_first_return_with_nine_points_cannot_pass_framework(side):
    nine, ten = market(side=side)
    nine = list(nine)
    if side is Side.LONG:
        nine[10] = bar(nine[10].opened_at, h="114")
    else:
        nine[20] = bar(nine[20].opened_at, low="86")
    nine = tuple(nine)
    cog = proposal(nine, ten)
    out = first_fvg_and_source_path(
        nine=nine, ten=ten[:4], cognition=cog,
    )
    assert out.state == "NO_FRAMEWORK"
    assert out.potential_points_at_mss == Decimal("9")
    assert out.first_fvg_confirmed_at is None


@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_ten_points_from_actual_mss_close_at_exact_boundary(side):
    nine, ten = market(side=side)
    nine = list(nine)
    if side is Side.LONG:
        nine[10] = bar(nine[10].opened_at, h="115")
    else:
        nine[20] = bar(nine[20].opened_at, low="85")
    nine = tuple(nine)
    cog = proposal(nine, ten)
    out = first_fvg_and_source_path(
        nine=nine, ten=ten[:4], cognition=cog,
    )
    assert out.state == "FVG_GEOMETRY_ATTESTED_NOT_EXECUTABLE"
    assert out.potential_points_at_mss == Decimal("10")
    assert not out.execution_authorized


def test_first_fvg_exactly_at_11am_is_not_an_order():
    nine, ten = market()
    cog = proposal(nine, ten)
    early = (
        bar(ten[3].opened_at, "105", "105", "93", "100"),
    )
    middle = tuple(
        bar(ten[0].opened_at + timedelta(minutes=i))
        for i in range(4, 59)
    )
    last = bar(
        ten[0].opened_at + timedelta(minutes=59),
        "105", "107", "104", "106",
    )
    whole = ten[:3] + early + middle + (last,)
    assert len(whole) == 60
    out = first_fvg_and_source_path(
        nine=nine, ten=whole, cognition=cog,
    )
    assert out.state == "WINDOW_CLOSED_FOR_NEW_LIMIT"
    assert out.first_fvg_confirmed_at is None
    assert out.execution_authorized is False
