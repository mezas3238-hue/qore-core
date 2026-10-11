"""C0 fail-closed partial candle geometry and predecision integrity."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_issue772_c0_native_integrity_v1 import (  # noqa: E501
    bucket_key,
    bucketize,
)

START=datetime(2026,8,3,10,tzinfo=UTC)


def one_minute(i:int)->CapitalizerM1Bar:
    t=START+timedelta(minutes=i)
    n=Decimal(i)/Decimal(100)
    return CapitalizerM1Bar(
        symbol="AUDJPY",opened_at=t,closed_at=t+timedelta(minutes=1),
        open=100+n,high=101+n,low=99+n,close=100+n,
        volume=100,digits=3,
    )


def test_exact_complete_h1_m15_full_nominal_and_closed() -> None:
    bars=tuple(one_minute(i) for i in range(60))
    for minutes,needed in ((60,1),(15,4)):
        snapshots,full,count=bucketize(bars,minutes)
        assert len(full)==needed
        assert count["STRICT_COMPLETE"]==needed
        assert count["LEGACY_ACCEPTED_NONSTRICT"]==0
        assert all(v.strict_complete and not v.premature_close
                   for v in snapshots.values())
        assert all(x.closed_at.minute % minutes==0 for x in full)


def test_h1_45_and_m15_11_are_accepted_but_not_full() -> None:
    m1=tuple(one_minute(i) for i in range(45))
    buckets,strict,count=bucketize(m1,60)
    b=next(iter(buckets.values()))
    assert b.eligible_legacy and not b.strict_complete
    assert b.observed==45 and b.missing==15
    assert b.premature_close and b.trailing and not b.leading
    assert b.detail()["complete_at"]=="UNAVAILABLE"
    assert len(strict)==0
    assert count["LEGACY_ACCEPTED_NONSTRICT"]==1
    m2=tuple(one_minute(i) for i in range(11))
    buckets2,strict2,ct=bucketize(m2,15)
    assert next(iter(buckets2.values())).premature_close
    assert ct["LEGACY_ACCEPTED_NONSTRICT"]==1
    assert not strict2


def test_internal_provider_hole_no_fake_full_candle() -> None:
    m=tuple(one_minute(i) for i in range(60) if i!=23)
    b,strict,counts=bucketize(m,60)
    candle=next(iter(b.values()))
    assert candle.eligible_legacy
    assert candle.internal_gap and not candle.trailing
    assert not candle.strict_complete
    assert not candle.premature_close
    assert not strict
    assert counts["INTERNAL_GAP"]==1


def test_leading_gap_is_missing_not_late_source_confirmation() -> None:
    m=tuple(one_minute(i) for i in range(5,60))
    b,strict,count=bucketize(m,60)
    v=next(iter(b.values()))
    assert v.leading and not v.trailing
    assert not v.premature_close
    assert v.actual_first_open==START+timedelta(minutes=5)
    assert not strict
    assert count["LEADING_GAP"]==1


def test_wrong_m1_clock_and_duplicate_fail_closed() -> None:
    m=tuple(one_minute(i) for i in range(60))
    late=replace(m[11],opened_at=m[11].opened_at+timedelta(seconds=5),
                 closed_at=m[11].closed_at+timedelta(seconds=5))
    b,strict,counts=bucketize(m[:11]+(late,)+m[12:],60)
    assert not strict and counts["STRICT_INVALID"]==1
    duplicate=m+(one_minute(11),)
    b,strict,counts=bucketize(duplicate,60)
    assert not strict and counts["DUPLICATE"]==1
    assert b[START].observed==61


def test_below_legacy_three_quarters_is_not_source_candle() -> None:
    for minutes,count_min in ((60,44),(15,10)):
        m=tuple(one_minute(i) for i in range(count_min))
        b,strict,c=bucketize(m,minutes)
        assert not next(iter(b.values())).eligible_legacy
        assert not strict and c["LEGACY_REJECTED"]==1


def test_buckets_require_supported_timeframes() -> None:
    with pytest.raises(ValueError,match="only H1 M15"):
        bucketize((one_minute(1),),5)
    assert bucket_key(START+timedelta(minutes=26),15)==(
        START+timedelta(minutes=15)
    )
