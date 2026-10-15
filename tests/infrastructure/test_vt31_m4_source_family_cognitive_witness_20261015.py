"""M4 four-source families with causal QORE geometry and NO false author certification."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    SessionId,
    Side,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.m1_execution import (
    confirmed_m1_fvg,
)
from scripts.vt31_m4_source_family_cognitive_witness_20261015 import (
    M4_NOT_CERTIFIED,
    M5_NOT_CERTIFIED,
    audit_family_one_day,
)

NY = ZoneInfo("America/New_York")


def bar(at, o="100", h="102", lo="98", c="101"):
    return M1Bar(
        at, at+timedelta(minutes=1),
        Decimal(o), Decimal(h), Decimal(lo), Decimal(c),
    )


def source_day(month=7, direction="LONG", fvg=True):
    d = 1 if month == 7 else 15
    at9 = datetime(2025, month, d, 9, tzinfo=NY).astimezone(UTC)
    at10 = datetime(2025, month, d, 10, tzinfo=NY).astimezone(UTC)
    nine = [bar(at9+timedelta(minutes=i)) for i in range(60)]
    nine[10] = bar(at9+timedelta(minutes=10), h="110")
    nine[20] = bar(at9+timedelta(minutes=20), lo="90")
    ten = [bar(at10+timedelta(minutes=i)) for i in range(60)]
    if direction == "LONG":
        nine[57] = bar(at9+timedelta(minutes=57), h="104")
        ten[0] = bar(at10, o="100", c="100")
        ten[1] = bar(at10+timedelta(minutes=1), o="96", h="99", lo="89", c="95")
        ten[2] = bar(at10+timedelta(minutes=2), o="94", h="103", lo="93", c="100")
        if fvg:
            ten[3] = bar(at10+timedelta(minutes=3), o="100", h="106", lo="99", c="105")
            ten[4] = bar(at10+timedelta(minutes=4), o="105", h="108", lo="104", c="107")
    else:
        nine[57] = bar(at9+timedelta(minutes=57), lo="96")
        ten[0] = bar(at10, o="100", c="100")
        ten[1] = bar(at10+timedelta(minutes=1), o="104", h="111", lo="103", c="105")
        ten[2] = bar(at10+timedelta(minutes=2), o="106", h="107", lo="97", c="100")
        if fvg:
            ten[3] = bar(at10+timedelta(minutes=3), o="100", h="101", lo="94", c="95")
            ten[4] = bar(at10+timedelta(minutes=4), o="95", h="96", lo="92", c="93")
    return str(at9.astimezone(NY).date()), tuple(nine), tuple(ten)


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", ["LONG", "SHORT"])
def test_author_source_fvg_shape_does_not_emit_author_certified_trade(month, side):
    day, nine, ten = source_day(month=month, direction=side)
    r = audit_family_one_day(
        day=day, nine=nine, ten=ten, return_at=ten[2].closed_at,
    )
    assert r["first_qore_fvg_observed_before_source_invalidation"] is True
    assert r["qore_fvg_observations_asof"][0]["side"] == side
    assert r["four_source_families"]["FVG"] == (
        "QORE_3_M1_SHAPE_OBSERVED_NOT_AUTHOR_CERTIFIED"
    )
    assert r["four_source_families"]["ORDER_BLOCK"].startswith("NOT_IMPLEMENTED")
    assert r["four_source_families"]["BREAKER_BLOCK"].startswith("NOT_IMPLEMENTED")
    assert r["m4_certification"] == M4_NOT_CERTIFIED
    assert r["m5_causative_swing_stop_certification"] == M5_NOT_CERTIFIED
    assert r["cognitive_decision_emitted"] is False
    assert r["orders_fills_created"] == 0


def test_no_fvg_keeps_fvg_evidence_unobserved_not_universal_failure():
    day, nine, ten = source_day(fvg=False)
    r = audit_family_one_day(
        day=day, nine=nine, ten=ten, return_at=ten[2].closed_at,
    )
    assert not r["first_qore_fvg_observed_before_source_invalidation"]
    assert r["four_source_families"]["FVG"] == "QORE_3_M1_SHAPE_NOT_OBSERVED"
    assert not r["source_author_profile_certified"]


def test_contiguous_three_closed_m1_are_required_for_qore_fvg():
    day, nine, ten = source_day()
    fvg = confirmed_m1_fvg(
        session=SessionId.NY_AM, first=ten[2], middle=ten[3], third=ten[4],
    )
    assert fvg is not None
    assert fvg.side is Side.LONG
    assert fvg.confirmed_at == ten[4].closed_at
    with pytest.raises(ValueError, match="missing M1"):
        confirmed_m1_fvg(
            session=SessionId.NY_AM, first=ten[2], middle=ten[4], third=ten[5],
        )


def test_no_future_m1_can_justify_earlier_fvg_or_cognitive_state():
    day, nine, ten = source_day()
    baseline = audit_family_one_day(
        day=day, nine=nine, ten=ten, return_at=ten[2].closed_at,
    )
    changed = ten[:6] + tuple(
        bar(x.opened_at, o="100", h="109", lo="96", c="101")
        for x in ten[6:]
    )
    after = audit_family_one_day(
        day=day, nine=nine, ten=changed, return_at=ten[2].closed_at,
    )
    assert baseline["first_qore_fvg_asof"] == after["first_qore_fvg_asof"]
    assert baseline["qore_fvg_observations_asof"][0] == (
        after["qore_fvg_observations_asof"][0]
    )


def test_missing_h1_m1_never_promoted_to_source_family():
    day, nine, ten = source_day()
    with pytest.raises(ValueError, match="INCOMPLETE_H1"):
        audit_family_one_day(
            day=day, nine=nine[1:], ten=ten, return_at=ten[2].closed_at,
        )


def test_no_author_verified_swing_does_not_generate_numeric_stop_or_sizing():
    day, nine, ten = source_day()
    r = audit_family_one_day(
        day=day, nine=nine, ten=ten, return_at=ten[2].closed_at,
    )
    assert r["m5_causative_swing_stop_certification"] == M5_NOT_CERTIFIED
    assert "stop_price" not in r
    assert "risk" not in r
    assert "lot" not in r
    assert r["trader_certified"] is False


def test_fvg_confirmed_at_last_m1_cannot_authorize_after_11ny():
    at10 = datetime(2025, 7, 1, 10, 57, tzinfo=NY).astimezone(UTC)
    a = bar(at10, o="100", h="103", lo="98", c="101")
    b = bar(at10+timedelta(minutes=1), o="102", h="107", lo="101", c="106")
    c = bar(at10+timedelta(minutes=2), o="106", h="109", lo="104", c="108")
    g = confirmed_m1_fvg(
        session=SessionId.NY_AM, first=a, middle=b, third=c,
    )
    assert g is not None and g.confirmed_at.astimezone(NY).hour == 11
    # Geometric FVG after close at 11 does NOT confer a fresh 10AM entry.
