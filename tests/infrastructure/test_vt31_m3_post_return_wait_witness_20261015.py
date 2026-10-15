"""VT31 M3 cognitive WAIT diagnostic tests. Fixtures are synthetic, not trades."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar
from scripts.vt31_m3_post_return_wait_witness_20261015 import (
    examine_first_return_day,
)
from scripts.vt31_ttrades_am_native_cog_v1_20261014 import (
    propose_ttrades_am_cognition,
)

NY = ZoneInfo("America/New_York")


def m1(at, o="100", h="102", lo="98", c="101"):
    return M1Bar(
        at, at+timedelta(minutes=1),
        Decimal(o), Decimal(h), Decimal(lo), Decimal(c),
    )


def scene(month=7, direction="LONG", continuation="LATE"):
    day = 1 if month == 7 else 15
    start9 = datetime(2025, month, day, 9, tzinfo=NY).astimezone(UTC)
    start10 = datetime(2025, month, day, 10, tzinfo=NY).astimezone(UTC)
    nine = [m1(start9+timedelta(minutes=i)) for i in range(60)]
    nine[10] = m1(start9+timedelta(minutes=10), h="110")
    nine[20] = m1(start9+timedelta(minutes=20), lo="90")
    ten = [m1(start10+timedelta(minutes=i)) for i in range(60)]
    if direction == "LONG":
        nine[57] = m1(start9+timedelta(minutes=57), h="104")
        ten[0] = m1(start10, o="100", c="100")
        ten[1] = m1(start10+timedelta(minutes=1), o="96", h="99", lo="89", c="95")
        ten[2] = m1(start10+timedelta(minutes=2), o="94", h="103", lo="93", c="100")
        if continuation == "LATE":
            ten[3] = m1(start10+timedelta(minutes=3), o="100", h="106", lo="99", c="105")
        elif continuation == "OPPOSITE_SWEEP":
            ten[3] = m1(start10+timedelta(minutes=3), o="100", h="111", lo="99", c="105")
        elif continuation == "DOUBLE_SWEEP":
            ten[3] = m1(start10+timedelta(minutes=3), o="100", h="111", lo="89", c="105")
        elif continuation == "NO_LATE":
            for i in range(3, 60):
                ten[i] = m1(start10+timedelta(minutes=i), o="100", h="102", lo="98", c="100")
    else:
        nine[57] = m1(start9+timedelta(minutes=57), lo="96")
        ten[0] = m1(start10, o="100", c="100")
        ten[1] = m1(start10+timedelta(minutes=1), o="104", h="111", lo="103", c="105")
        ten[2] = m1(start10+timedelta(minutes=2), o="106", h="107", lo="97", c="100")
        if continuation == "LATE":
            ten[3] = m1(start10+timedelta(minutes=3), o="100", h="101", lo="94", c="95")
        elif continuation == "OPPOSITE_SWEEP":
            ten[3] = m1(start10+timedelta(minutes=3), o="100", h="101", lo="89", c="95")
        elif continuation == "DOUBLE_SWEEP":
            ten[3] = m1(start10+timedelta(minutes=3), o="100", h="111", lo="89", c="95")
        elif continuation == "NO_LATE":
            for i in range(3, 60):
                ten[i] = m1(start10+timedelta(minutes=i), o="100", h="102", lo="98", c="100")
    return str(start9.astimezone(NY).date()), tuple(nine), tuple(ten)


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("direction", ["LONG", "SHORT"])
def test_late_qore_confirmation_exists_but_original_cog_keeps_no_intent(month, direction):
    day, nine, ten = scene(month, direction)
    at = ten[2].closed_at
    old = propose_ttrades_am_cognition(as_of=at, history=nine+ten[:3])
    late = propose_ttrades_am_cognition(as_of=ten[3].closed_at,
                                       history=nine+ten[:4])
    assert old.state == "UNKNOWN"
    assert "QORE_MSS_PROXY_NOT_CONFIRMED_ON_FIRST_RETURN" in old.reasons
    assert old.decision is None
    assert late.state == "UNKNOWN"
    assert "RETURN_M1_NOT_FRESH_AT_ASOF" in late.reasons
    assert late.decision is None
    audit = examine_first_return_day(
        day=day, nine=nine, ten=ten, first_return_at=at,
    )
    assert audit["terminal_state"] == "LATE_QORE_PROXY_ONLY_NOT_AUTHOR_CERTIFIED"
    assert audit["candidate_side_from_first_raid"] == direction
    assert audit["last_observed_at"] == ten[3].closed_at.isoformat()
    assert audit["late_qore_pivot_confirmed_at"] is not None
    assert audit["original_cog_kept_intent_absent"] is True
    assert not audit["methodology_certified"]
    assert not audit["cognition_certified"]
    assert not audit["trade_or_order_created"]


@pytest.mark.parametrize("direction", ["LONG", "SHORT"])
def test_opposite_raid_after_return_cannot_reorient_context(direction):
    day, nine, ten = scene(direction=direction, continuation="OPPOSITE_SWEEP")
    record = examine_first_return_day(
        day=day, nine=nine, ten=ten, first_return_at=ten[2].closed_at,
    )
    assert record["terminal_state"] == "SOURCE_REJECTED"
    assert "OPPOSITE_H1_RAID_AFTER_FIRST_SWEEP" in record["terminal_reason"]
    assert record["late_qore_pivot_confirmed_at"] is None


def test_both_sides_on_one_bar_is_unknown_not_predict_high_low_order():
    day, nine, ten = scene(continuation="DOUBLE_SWEEP")
    record = examine_first_return_day(
        day=day, nine=nine, ten=ten, first_return_at=ten[2].closed_at,
    )
    assert record["terminal_state"] == "SOURCE_AMBIGUOUS"
    assert "BOTH_H1_SIDES_SWEPT_UNKNOWN_INTRABAR_ORDER" in record["terminal_reason"]


def test_without_late_proxy_and_without_opposite_raid_wait_expires():
    day, nine, ten = scene(continuation="NO_LATE")
    record = examine_first_return_day(
        day=day, nine=nine, ten=ten, first_return_at=ten[2].closed_at,
    )
    assert record["terminal_state"] == "EXPIRED_WITHOUT_LATE_PROXY"
    assert record["last_observed_at"] == ten[-1].closed_at.isoformat()
    assert record["wait_for_confirmation_m1_steps"] > 0


def test_missing_9am_reference_abstains_instead_of_inventing():
    day, nine, ten = scene()
    with pytest.raises(ValueError, match="SOURCE_HOURS_INCOMPLETE"):
        examine_first_return_day(
            day=day, nine=nine[1:], ten=ten, first_return_at=ten[2].closed_at,
        )


def test_future_variation_does_not_change_original_first_return_cognitive_state():
    _, nine, ten = scene()
    at = ten[2].closed_at
    baseline = propose_ttrades_am_cognition(as_of=at, history=nine+ten[:3])
    flipped = ten[:3] + tuple(m1(b.opened_at, h="500", lo="1")
                             for b in ten[3:])
    reviewed = propose_ttrades_am_cognition(as_of=at, history=nine+flipped[:3])
    assert baseline == reviewed
    assert baseline.decision is None
