"""VT31 M3 V2 WAIT source-only COG fixtures; not author method certificates."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar
from scripts.vt31_m3_ttrades_cog_wait_v2_20261015 import (
    TTradesAmWaitCognitionV2,
)

NY = ZoneInfo("America/New_York")


def m1(at, o="100", h="102", lo="98", c="101"):
    return M1Bar(
        at, at+timedelta(minutes=1),
        Decimal(o), Decimal(h), Decimal(lo), Decimal(c),
    )


def fixture(month=7, side="LONG", no_late=False):
    d = 1 if month == 7 else 15
    start9 = datetime(2025, month, d, 9, tzinfo=NY).astimezone(UTC)
    start10 = datetime(2025, month, d, 10, tzinfo=NY).astimezone(UTC)
    nine = [m1(start9+timedelta(minutes=i)) for i in range(60)]
    nine[10] = m1(start9+timedelta(minutes=10), h="110")
    nine[20] = m1(start9+timedelta(minutes=20), lo="90")
    ten = [m1(start10+timedelta(minutes=i)) for i in range(60)]
    if side == "LONG":
        nine[57] = m1(start9+timedelta(minutes=57), h="104")
        ten[0] = m1(start10, o="100", c="100")
        ten[1] = m1(start10+timedelta(minutes=1), o="96", h="99", lo="89", c="95")
        ten[2] = m1(start10+timedelta(minutes=2), o="94", h="103", lo="93", c="100")
        ten[3] = (
            m1(start10+timedelta(minutes=3), o="100", h="102", lo="98", c="100")
            if no_late else
            m1(start10+timedelta(minutes=3), o="100", h="106", lo="99", c="105")
        )
    else:
        nine[57] = m1(start9+timedelta(minutes=57), lo="96")
        ten[0] = m1(start10, o="100", c="100")
        ten[1] = m1(start10+timedelta(minutes=1), o="104", h="111", lo="103", c="105")
        ten[2] = m1(start10+timedelta(minutes=2), o="106", h="107", lo="97", c="100")
        ten[3] = (
            m1(start10+timedelta(minutes=3), o="100", h="102", lo="98", c="100")
            if no_late else
            m1(start10+timedelta(minutes=3), o="100", h="101", lo="94", c="95")
        )
    if no_late:
        for i in range(4, 60):
            ten[i] = m1(start10+timedelta(minutes=i),
                        o="100", h="102", lo="98", c="100")
    return tuple(nine), tuple(ten)


def warmed(nine):
    cog = TTradesAmWaitCognitionV2()
    for bar in nine:
        snap = cog.observe_closed_m1(bar)
        assert not snap.cognitive_decision_emitted
    return cog


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", ["LONG", "SHORT"])
def test_v2_preserves_wait_and_detects_late_proxy_without_authorial_intent(month, side):
    nine, ten = fixture(month, side)
    cog = warmed(nine)
    first = cog.observe_closed_m1(ten[0])
    assert first.state == "WAIT_FOR_SWEEP"
    assert first.explicit_wait
    sweep = cog.observe_closed_m1(ten[1])
    assert sweep.state == "WAIT_FOR_RETURN"
    assert sweep.explicit_wait
    ret = cog.observe_closed_m1(ten[2])
    assert ret.state == "WAIT_FOR_CONFIRMATION"
    assert ret.explicit_wait
    assert ret.first_return_at == ten[2].closed_at
    late = cog.observe_closed_m1(ten[3])
    assert late.state == "QORE_PROXY_OBSERVED_AUTHOR_DISPLACEMENT_UNVERIFIED"
    assert late.first_qore_proxy_observed_at == ten[3].closed_at
    assert late.bias == side
    assert not late.cognitive_decision_emitted
    assert not late.entry_authorized
    assert not late.method_certified
    assert not late.cognition_certified
    assert cog.snapshot() == late


def test_post_return_opposite_raid_invalidates_first_raid():
    nine, ten = fixture()
    cog = warmed(nine)
    for bar in ten[:4]:
        cog.observe_closed_m1(bar)
    next_at = ten[4].opened_at
    snap = cog.observe_closed_m1(
        m1(next_at, o="100", h="111", lo="99", c="105"),
    )
    assert snap.state == "INVALIDATED_OPPOSITE_RAID"
    assert not snap.cognitive_decision_emitted
    assert not snap.entry_authorized
    another = cog.observe_closed_m1(ten[5])
    assert another.state == "INVALIDATED_OPPOSITE_RAID"


def test_ambiguous_double_sweep_rejects_reconstruction_of_high_low_sequence():
    nine, ten = fixture()
    cog = warmed(nine)
    cog.observe_closed_m1(ten[0])
    at = ten[1].opened_at
    a = cog.observe_closed_m1(m1(at, o="100", h="111", lo="89", c="100"))
    assert a.state == "UNKNOWN_INTRABAR_OR_SOURCE"
    for bar in ten[2:4]:
        s = cog.observe_closed_m1(bar)
        assert s.state == "UNKNOWN_INTRABAR_OR_SOURCE"


def test_no_late_confirmation_stays_wait_until_clock_expires():
    nine, ten = fixture(no_late=True)
    cog = warmed(nine)
    for bar in ten[:-1]:
        v = cog.observe_closed_m1(bar)
    assert v.state == "WAIT_FOR_CONFIRMATION"
    expired = cog.observe_closed_m1(ten[-1])
    assert expired.state == "EXPIRED"
    assert not expired.cognitive_decision_emitted


def test_h1_incomplete_is_unknown_and_not_filled_by_future():
    nine, ten = fixture()
    cog = warmed(nine[1:])
    s = cog.observe_closed_m1(ten[0])
    assert s.state == "UNKNOWN_INCOMPLETE_H1"
    assert not s.opposite_09h_dol_observed
    for bar in ten[1:4]:
        s = cog.observe_closed_m1(bar)
    assert s.state == "UNKNOWN_INCOMPLETE_H1"


def test_duplicate_backwards_and_cross_day_input_are_rejected():
    nine, ten = fixture()
    cog = warmed(nine)
    with pytest.raises(ValueError, match="DUPLICATED_OVERLAPPED"):
        cog.observe_closed_m1(nine[-1])
    fresh = warmed(nine)
    with pytest.raises(ValueError, match="FRESH_COG_INSTANCE"):
        fresh.observe_closed_m1(
            m1(nine[0].opened_at+timedelta(days=1)),
        )


def test_snapshot_is_readonly_and_no_method_sizing_or_orders():
    nine, ten = fixture()
    cog = warmed(nine)
    snap = cog.observe_closed_m1(ten[0])
    assert cog.snapshot() == snap
    assert snap.entry_authorized is False
    assert snap.cognitive_decision_emitted is False
    assert snap.qore_proxy_authorial_certified is False
