"""Source-authored TTrades semantic building blocks; never certify trading."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    Side,
)
from scripts.vt31_m4_m5_author_semantics_bridge_20261015 import (
    AuthorShortTermSwing,
    ob_body_midpoint_status,
    short_term_swings,
    source_breaker_four_leg,
    source_ob_cisd,
)


def bar(at, o="100", h="102", low="98", c="100"):
    return M1Bar(
        at, at+timedelta(minutes=1),
        Decimal(o), Decimal(h), Decimal(low), Decimal(c),
    )


def clock():
    return datetime(2025, 7, 1, 14, tzinfo=UTC)


def test_ttrades_three_bar_short_term_high_and_low_need_right_close():
    t=clock()
    bars=(
        bar(t,h="103",low="96"),
        bar(t+timedelta(minutes=1),h="110",low="92"),
        bar(t+timedelta(minutes=2),h="103",low="96"),
    )
    events=short_term_swings(bars)
    assert {x.kind for x in events}=={"HIGH","LOW"}
    assert all(x.confirmed_at==bars[2].closed_at for x in events)
    assert all(x.source_author_geometry for x in events)
    assert all(not x.author_causative_for_displacement for x in events)
    assert short_term_swings(bars[:2])==()


def test_equal_neighbours_not_strict_short_term_swing():
    t=clock()
    bars=(bar(t,h="110"),bar(t+timedelta(minutes=1),h="110"),
          bar(t+timedelta(minutes=2),h="102"))
    assert short_term_swings(bars)==()


def test_gapped_m1_cannot_confirm_pivot_from_future_candle():
    t=clock()
    bars=(bar(t),bar(t+timedelta(minutes=1),h="110"),
          bar(t+timedelta(minutes=3)))
    assert short_term_swings(bars)==()


def swing(kind,price,i):
    t=clock()+timedelta(minutes=i)
    return AuthorShortTermSwing(
        kind,Decimal(price),t,t+timedelta(minutes=1),
    )


def test_bullish_breaker_requires_four_ordered_legs_and_hh_ll():
    legs=(
        swing("LOW","100",0),swing("HIGH","110",2),
        swing("LOW","90",4),swing("HIGH","115",6),
    )
    assert source_breaker_four_leg(
        legs,Side.LONG,as_of=legs[2].confirmed_at
    ) is None
    f=source_breaker_four_leg(
        legs,Side.LONG,as_of=legs[3].confirmed_at
    )
    assert f is not None and f.direction=="LONG"
    assert f.last_confirmed_at==legs[3].confirmed_at
    assert not f.breaker_zone_and_retest_verified
    assert not f.author_entry_valid


def test_bearish_breaker_requires_higher_high_and_lower_low():
    legs=(
        swing("HIGH","110",0),swing("LOW","90",2),
        swing("HIGH","115",4),swing("LOW","85",6),
    )
    assert source_breaker_four_leg(
        legs,Side.SHORT,as_of=legs[-1].confirmed_at
    ) is not None
    invalid=legs[:2]+(swing("HIGH","105",4),legs[-1])
    assert source_breaker_four_leg(
        invalid,Side.SHORT,as_of=invalid[-1].confirmed_at
    ) is None


def test_shorter_three_leg_does_not_form_breaker():
    legs=(swing("LOW","100",0),swing("HIGH","110",2),
          swing("LOW","90",4))
    assert source_breaker_four_leg(
        legs,Side.LONG,as_of=legs[-1].confirmed_at
    ) is None


def test_ob_cisd_bullish_closes_through_opposing_open_not_mss():
    t=clock()
    candidate=bar(t,o="100",h="101",low="96",c="97")
    confirm=bar(t+timedelta(minutes=1),o="98",h="105",low="97",c="104")
    e=source_ob_cisd(
        (candidate,confirm),Side.LONG,
        first_sweep_at=candidate.closed_at,
    )
    assert e is not None
    assert e.opposing_open==Decimal("100")
    assert e.opposing_body_midpoint==Decimal("98.5")
    assert e.confirmed_at==confirm.closed_at
    assert not e.author_displacement_validated
    assert not e.author_trade_ready


def test_ob_cisd_bearish_close_through_up_candle_open():
    t=clock()
    candidate=bar(t,o="100",h="104",low="99",c="103")
    confirm=bar(t+timedelta(minutes=1),o="102",h="103",low="96",c="97")
    e=source_ob_cisd(
        (candidate,confirm),Side.SHORT,
        first_sweep_at=candidate.closed_at,
    )
    assert e is not None and e.confirmed_at==confirm.closed_at
    assert e.side is Side.SHORT


def test_ob_cisd_not_validated_by_touch_without_close():
    t=clock()
    candidate=bar(t,o="100",h="101",low="96",c="97")
    second=bar(t+timedelta(minutes=1),o="98",h="101",low="96",c="99")
    assert source_ob_cisd(
        (candidate,second),Side.LONG,
        first_sweep_at=candidate.closed_at,
    ) is None


def test_ob_mean_body_threshold_retest_not_fill_and_closure_invalidates():
    t=clock()
    candidate=bar(t,o="100",h="101",low="96",c="97")
    confirm=bar(t+timedelta(minutes=1),o="98",h="105",low="97",c="104")
    e=source_ob_cisd(
        (candidate,confirm),Side.LONG,
        first_sweep_at=candidate.closed_at,
    )
    assert e is not None
    touch=bar(t+timedelta(minutes=2),o="101",h="105",low="98",c="102")
    assert ob_body_midpoint_status(
        evidence=e,subsequent=touch
    )=="OB_BODY_MID_TOUCHED_NOT_EXECUTION"
    bad=bar(t+timedelta(minutes=2),o="99",h="105",low="96",c="97")
    assert ob_body_midpoint_status(
        evidence=e,subsequent=bad
    )=="AMBIGUOUS_TOUCH_AND_INVALIDATION_SAME_M1_NO_FILL"
    with pytest.raises(ValueError,match="FUTURE_OB"):
        ob_body_midpoint_status(evidence=e,subsequent=candidate)


def test_author_elements_do_not_imply_cog_execution_or_sizing():
    e=swing("HIGH","110",1)
    assert e.author_causative_for_displacement is False
    assert source_breaker_four_leg(
        (e,),Side.SHORT,as_of=e.confirmed_at
    ) is None
