"""COG original LONG/SHORT parity with native Trader Lab simulated 32x clock."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.fast_forward import (
    TraderLabFastForwardSchedule,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    SessionId,
    Side,
)
from scripts.vt31_original_cog_traderlab_32x_long_short_20261015 import (
    bidirectional_dossier,
    case,
    mirror_long_history,
)
from scripts.vt31_original_g3_cog_short_sessions_qualitative_20261015 import (
    short_fixture,
)


@pytest.mark.parametrize("month", [1,7])
@pytest.mark.parametrize(
    "session", [SessionId.LONDON,SessionId.NY_AM,SessionId.NY_PM],
)
@pytest.mark.parametrize("side", [Side.LONG,Side.SHORT])
def test_genuine_original_g3_cog_mirrors_both_sides_1x_32x(
    month, session, side,
):
    original=case(session=session,month=month,side=side,no_mss=False)
    abstained=case(session=session,month=month,side=side,no_mss=True)
    target,pivot=(
        ("150","134") if side is Side.LONG else ("80","96")
    )
    assert original["original_cog_trace_before_and_after"][0]["action"]=="WAIT"
    end=original["original_cog_trace_before_and_after"][1]
    assert end["action"]==side.value
    assert end["target"]==target
    assert end["structure_level"]==pivot
    assert abstained["original_cog_trace_before_and_after"][1]["action"]=="WAIT"
    for row in (original,abstained):
        assert row["ff_canonical_source_and_trace_identical"]
        assert row["ff_acceleration_factor_simulated"]==32
        assert row["elapsed_normal_us"]==32*row["elapsed_simulated_ff_us"]
        assert row["ff_all_m1_closed_at_preserved"]
        assert not row["qualified_vt31_trader_lab_L3"]
        assert not row["certified_author_method"]
        assert not row["certified_cognition"]
        assert row["orders"]==row["trader_sizing"]==0


def test_long_source_reflection_only_transforms_prices_and_preserves_all_m1():
    original,_=short_fixture(session=SessionId.NY_AM,month=7)
    mirrored=mirror_long_history(original)
    assert len(original)==len(mirrored)
    assert all(
        s.opened_at==l.opened_at and s.closed_at==l.closed_at
        and s.open+l.open==Decimal("230")
        and s.close+l.close==Decimal("230")
        and s.low+l.high==Decimal("230")
        and s.high+l.low==Decimal("230")
        for s,l in zip(original,mirrored,strict=True)
    )
    assert all(isinstance(l,M1Bar) for l in mirrored)


def test_original_ny_synthetic_case_never_becomes_lab_l3_real_bidask():
    data=bidirectional_dossier()
    assert len(data["cases"])==24
    assert len({x["identity"] for x in data["cases"]})==24
    assert data["all_24_parity"] is True
    assert data["original_g3_code_sha"]["git_blob_sha1"]==(
        "d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9"
    )
    assert data["native_traderlab_schedule_used"] is True
    assert data["observed_CPU_speedup_32x"] is False
    assert data["qualified_real_vt31_L3"] is False
    assert data["methodology_certified"] is False
    assert data["cognition_certified"] is False
    assert data["dual_cog_ops_signatures_verified"] is False
    assert data["economic_metrics"] is None
    assert data["broker_orders"]==data["sizing"]==0
    assert data["live_authorized"] is False
    assert len([x for x in data["cases"] if x["side"]=="LONG"])==12
    assert len([x for x in data["cases"] if x["side"]=="SHORT"])==12
    assert len([
        x for x in data["cases"] if x["counterfactual_change_only_last_close"]
    ])==12
