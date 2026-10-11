"""P0 772: independent price benchmark, source-only 20 and future M1 tests."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_issue772_direction_source_forensic_v1 import (  # noqa: E501
    independently_closed_h1,
    sample_hash,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_issue772_source_census_aggregate_v1 import (
    sample20,
)

AT=datetime(2026,5,5,10,tzinfo=UTC)


def native(i:int)->CapitalizerM1Bar:
    t=AT+timedelta(minutes=i)
    p=Decimal(100)+Decimal(i)/Decimal(100)
    return CapitalizerM1Bar(
        symbol="USDJPY",opened_at=t,closed_at=t+timedelta(minutes=1),
        open=p,high=p+Decimal("0.1"),
        low=p-Decimal("0.1"),close=p,
        volume=100,digits=3,
    )


def test_completed_h1_uses_60_native_minutes_and_prefix_is_invariant() -> None:
    original=tuple(native(i) for i in range(180))
    h1=independently_closed_h1(original)
    assert len(h1)==3
    assert all(x.minute_count==60 for x in h1)
    altered=original+(native(180),)
    assert independently_closed_h1(altered)==h1


def test_missing_minute_refuses_partial_h1_close() -> None:
    m=tuple(native(i) for i in range(120) if i!=35)
    hourly=independently_closed_h1(m)
    assert len(hourly)==1
    assert hourly[0].opened_at==AT+timedelta(hours=1)
    # A gap cannot be hidden by use of a 3/4-covered candle.
    assert hourly[0].closed_at==AT+timedelta(hours=2)


def test_nonuniform_second_clock_does_not_create_synthetic_h1() -> None:
    m=tuple(native(i) for i in range(60))
    wrong=replace(m[20],opened_at=m[20].opened_at+timedelta(seconds=5),
                  closed_at=m[20].closed_at+timedelta(seconds=5))
    assert independently_closed_h1(m[:20]+(wrong,)+m[21:])==()


def test_sha256_sampling_is_deterministic_outcome_independent() -> None:
    def source(i:int)->dict:
        sid=f"source_id_{i:05d}"
        return {
            "source_opportunity_id":sid,
            "selection_rank_sha256":sample_hash(sid),
            "trigger_family":(
                "LIQUIDITY_SWEEP_CISD" if i%2 else "FVG_RETRACE_CISD"
            ),
            "h1_state_inherited":bool((i//2)%2),
        }

    sources=tuple(source(i) for i in range(2020))
    chosen=sample20(sources)
    assert len(chosen)==20
    assert len({x["source_opportunity_id"] for x in chosen})==20
    assert chosen==sample20(tuple(reversed(sources)))
    mutated=tuple({**x,"realized_future_R":str(i*10)} for i,x in enumerate(sources))
    assert tuple(x["source_opportunity_id"] for x in chosen)==tuple(
        x["source_opportunity_id"] for x in sample20(mutated)
    )
    with pytest.raises(ValueError,match="2020"):
        sample20(sources[:100])
