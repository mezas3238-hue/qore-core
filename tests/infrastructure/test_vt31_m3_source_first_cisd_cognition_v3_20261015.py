"""VT31 M3 COG V3: FIRST_OPEN source component, WAIT/revocation, no trade."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar
from scripts.vt31_m3_source_first_cisd_cognition_v3_20261015 import (
    TTradesAmSourceFirstCognitionV3,
)

NY = ZoneInfo("America/New_York")


def m1(at, o="100", h="115", lo="90", c="100"):
    return M1Bar(
        at,at+timedelta(minutes=1),
        Decimal(o),Decimal(h),Decimal(lo),Decimal(c),
    )


class FakeOriginalV2:
    """Control only: actual 483-case integration invokes UNMODIFIED V2."""

    def __init__(self, mode="LONG"):
        self.mode=mode
        self.sweep=None
        self.ret=None
        self.invalidate_on=None

    def observe_closed_m1(self, bar):
        local=bar.opened_at.astimezone(NY)
        if local.hour==9:
            return SimpleNamespace(
                as_of=bar.closed_at,state="UNKNOWN_INCOMPLETE_H1",
                first_sweep_at=None,first_return_at=None,bias=None,
            )
        if self.sweep is None:
            self.sweep=bar.closed_at
            self.ret=bar.closed_at
        state=("INVALIDATED_OPPOSITE_RAID" if bar.closed_at==self.invalidate_on
               else "WAIT_FOR_CONFIRMATION")
        return SimpleNamespace(
            as_of=bar.closed_at,state=state,first_sweep_at=self.sweep,
            first_return_at=self.ret,bias=self.mode,
        )


def build(mode="LONG"):
    c=TTradesAmSourceFirstCognitionV3()
    f=FakeOriginalV2(mode)
    c._source=f
    t=datetime(2025,7,1,9,tzinfo=NY).astimezone(UTC)
    for i in range(60):
        c.observe_closed_m1(m1(t+timedelta(minutes=i)))
    at=datetime(2025,7,1,10,tzinfo=NY).astimezone(UTC)
    return c,f,at


def test_stateful_wait_then_false_last_only_does_not_authorize():
    cog,f,t=build()
    first=cog.observe_closed_m1(m1(t,o="110",h="115",lo="105",c="108"))
    assert first.state=="WAIT_FOR_FIRST_OPEN_CISD"
    cog.observe_closed_m1(m1(t+timedelta(minutes=1),o="108",h="110",lo="104",c="106"))
    fake=cog.observe_closed_m1(
        m1(t+timedelta(minutes=2),o="106",h="114",lo="103",c="109")
    )
    assert fake.state=="QORE_LAST_OPEN_PREMATURE_WAIT"
    assert fake.first_author_cisd_at is None
    assert fake.first_legacy_last_only_at==t+timedelta(minutes=3)
    assert not fake.author_entry_ready and not fake.cognitive_decision_emitted
    assert not fake.trader_certified


def test_first_opposing_open_confirms_component_and_then_reverses_on_opposite_raid():
    cog,f,t=build()
    cog.observe_closed_m1(m1(t,o="110",h="115",lo="105",c="108"))
    cog.observe_closed_m1(m1(t+timedelta(minutes=1),o="108",h="110",lo="104",c="106"))
    correct=cog.observe_closed_m1(
        m1(t+timedelta(minutes=2),o="106",h="115",lo="103",c="112")
    )
    assert correct.state=="AUTHOR_FIRST_OPEN_CISD_COMPONENT_MSS_UNVERIFIED"
    assert correct.first_author_cisd_at==t+timedelta(minutes=3)
    assert correct.first_author_series_length==2
    assert not correct.author_entry_ready
    f.invalidate_on=t+timedelta(minutes=4)
    invalid=cog.observe_closed_m1(
        m1(t+timedelta(minutes=3),o="112",h="115",lo="108",c="113")
    )
    assert invalid.state=="INVALIDATED_OPPOSITE_RAID"
    assert invalid.first_author_cisd_at==correct.first_author_cisd_at
    assert not invalid.author_entry_ready


def test_target_consumed_revokes_previous_cisd_component():
    cog,f,t=build()
    cog.observe_closed_m1(m1(t,o="110",h="115",lo="105",c="108"))
    cog.observe_closed_m1(m1(t+timedelta(minutes=1),o="108",h="110",lo="104",c="106"))
    cog.observe_closed_m1(m1(t+timedelta(minutes=2),o="106",h="115",lo="103",c="112"))
    target=cog.observe_closed_m1(
        m1(t+timedelta(minutes=3),o="112",h="121",lo="109",c="118")
    )
    assert target.state=="TARGET_CONSUMED_NO_FRESH_INTENT"
    assert target.was_target_consumed
    assert target.first_author_cisd_at is not None
    assert target.cognitive_decision_emitted is False


def test_first_valid_component_stays_first_even_on_later_source_reconfirmations():
    cog,f,t=build()
    cog.observe_closed_m1(m1(t,o="110",h="115",lo="105",c="108"))
    cog.observe_closed_m1(m1(t+timedelta(minutes=1),o="108",h="110",lo="104",c="106"))
    a=cog.observe_closed_m1(m1(t+timedelta(minutes=2),o="106",h="115",lo="103",c="112"))
    cog.observe_closed_m1(m1(t+timedelta(minutes=3),o="112",h="114",lo="103",c="109"))
    cog.observe_closed_m1(m1(t+timedelta(minutes=4),o="109",h="111",lo="101",c="105"))
    b=cog.observe_closed_m1(m1(t+timedelta(minutes=5),o="105",h="115",lo="101",c="114"))
    assert b.first_author_cisd_at==a.first_author_cisd_at
    assert b.author_events_observed >= 2
    assert b.state=="AUTHOR_FIRST_OPEN_CISD_COMPONENT_MSS_UNVERIFIED"


def test_unknown_gap_never_authorizes_source_component():
    cog,f,t=build()
    cog.observe_closed_m1(m1(t,o="110",h="115",lo="105",c="108"))
    unknown=cog.observe_closed_m1(
        m1(t+timedelta(minutes=2),o="108",h="112",lo="104",c="111")
    )
    assert unknown.state=="UNKNOWN_SOURCE_GAP"
    assert unknown.first_author_cisd_at is None
    assert not unknown.author_entry_ready


def test_bearish_short_does_not_require_long_first_open():
    cog,f,t=build("SHORT")
    cog.observe_closed_m1(m1(t,o="95",h="110",lo="91",c="97"))
    cog.observe_closed_m1(m1(t+timedelta(minutes=1),o="97",h="110",lo="90",c="99"))
    a=cog.observe_closed_m1(m1(t+timedelta(minutes=2),o="99",h="110",lo="90",c="94"))
    assert a.state=="AUTHOR_FIRST_OPEN_CISD_COMPONENT_MSS_UNVERIFIED"
    assert a.first_author_cisd_at==t+timedelta(minutes=3)


def test_repeated_snapshot_is_pure_and_not_a_backdoor():
    cog,_,t=build()
    a=cog.observe_closed_m1(m1(t,o="105",h="110",lo="100",c="103"))
    assert cog.snapshot()==a
    assert cog.snapshot()==a
    with pytest.raises(ValueError,match="NO_CLOSED_M1"):
        TTradesAmSourceFirstCognitionV3().snapshot()


def test_source_identity_raid_or_return_mutation_aborts_cognitive_run():
    cog,f,t=build()
    cog.observe_closed_m1(m1(t,o="110",h="115",lo="105",c="108"))
    f.ret=f.ret+timedelta(minutes=1)
    with pytest.raises(AssertionError,match="BIAS_MUTATED"):
        cog.observe_closed_m1(m1(t+timedelta(minutes=1),o="108",h="110",lo="104",c="106"))


def test_expiry_outside_ny_window_is_not_entry_authority():
    cog,f,t=build()
    cog.observe_closed_m1(m1(t,o="110",h="115",lo="105",c="108"))
    end=cog.observe_closed_m1(
        m1(t+timedelta(minutes=59),o="108",h="112",lo="103",c="110")
    )
    assert end.state=="EXPIRED_11_NY"
    assert end.author_entry_ready is False and end.cognitive_decision_emitted is False
