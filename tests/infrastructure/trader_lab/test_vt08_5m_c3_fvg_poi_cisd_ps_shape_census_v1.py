"""C3 POI/CISD/PS shape-only causal adversarial regression."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_5m_c3_fvg_poi_cisd_ps_shape_census_v1 import (
    _active_c2_fvgs,
    _first_c3_shape,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

NY = ZoneInfo("America/New_York")


def bar(
    t: datetime, op: str, hi: str, lo: str, cl: str
) -> Vt08B01Bar:
    return Vt08B01Bar(
        opened_at=t.astimezone(UTC),
        closed_at=(t + timedelta(minutes=15)).astimezone(UTC),
        open=Decimal(op),
        high=Decimal(hi),
        low=Decimal(lo),
        close=Decimal(cl),
    )


def test_c3_real_poi_touch_then_cisd_ps_then_next_m15_open() -> None:
    t = datetime(2026, 1, 7, 5, tzinfo=NY)
    c3 = (
        bar(t, "100.30", "100.50", "100.10", "100.40"),
        bar(t + timedelta(minutes=15), "100.20", "100.30", "99.60", "99.80"),
        bar(t + timedelta(minutes=30), "99.80", "100.50", "99.70", "100.40"),
        bar(t + timedelta(minutes=45), "100.35", "100.70", "100.10", "100.50"),
    )
    row = _first_c3_shape(
        c3,
        levels=((Decimal("99.80"), Decimal("100.20")),),
        side=DemoTradingSetupSide.LONG,
    )
    assert row is not None
    assert row["ps_cisd_confirmed_at"] == c3[2].closed_at.isoformat()
    assert row["hypothetical_next_m15_open_at"] == c3[3].opened_at.isoformat()
    assert row["causal_stop_oriented_geometry"] is True
    assert row["methodology_status"] == "SHAPE_ONLY_NOT_SOURCE_COMPLETE"
    assert row["trades_executed"] == 0


def test_no_pretend_fill_when_future_next_bar_missing() -> None:
    t = datetime(2026, 1, 7, 5, tzinfo=NY)
    c3 = (
        bar(t, "100.30", "100.50", "100.10", "100.40"),
        bar(t + timedelta(minutes=15), "100.20", "100.30", "99.60", "99.80"),
        bar(t + timedelta(minutes=30), "99.80", "100.50", "99.70", "100.40"),
    )
    row = _first_c3_shape(
        c3,
        levels=((Decimal("99.80"), Decimal("100.20")),),
        side=DemoTradingSetupSide.LONG,
    )
    assert row is not None
    assert row["causal_stop_oriented_geometry"] is False
    assert row["hypothetical_next_m15_open_at"] is None


def test_no_ps_confirmation_after_poi_is_not_a_candidate() -> None:
    t = datetime(2026, 1, 7, 5, tzinfo=NY)
    c3 = (
        bar(t, "99.50", "99.60", "99.30", "99.40"),
        bar(t + timedelta(minutes=15), "99.40", "100.10", "99.35", "100.00"),
        bar(t + timedelta(minutes=30), "100.00", "100.50", "99.90", "100.35"),
    )
    # The first bar touched the POI: test the signal still requires a
    # subsequent PS confirmation (existing swing needs close-through).
    assert _first_c3_shape(
        c3,
        levels=((Decimal("100.20"), Decimal("100.40")),),
        side=DemoTradingSetupSide.LONG,
    ) is None


def test_c2_fvg_confirmed_pre_anchor_and_invalidated_with_later_breach() -> None:
    t = datetime(2026, 1, 7, 1, tzinfo=NY)
    c2 = (
        bar(t, "100.00", "100.30", "99.80", "100.20"),
        bar(t + timedelta(minutes=15), "100.25", "100.50", "100.10", "100.45"),
        bar(t + timedelta(minutes=30), "100.80", "101.10", "100.70", "101.00"),
    )
    fvg = (Decimal("100.30"), Decimal("100.70"))
    assert _active_c2_fvgs(c2, side=DemoTradingSetupSide.LONG) == (fvg,)
    new = bar(t + timedelta(minutes=45), "100.40", "100.50", "100.10", "100.30")
    assert _active_c2_fvgs(c2 + (new,), side=DemoTradingSetupSide.LONG) == ()


def test_c2_short_fvg_side() -> None:
    t = datetime(2026, 1, 7, 1, tzinfo=NY)
    c2 = (
        bar(t, "100.70", "101.00", "100.50", "100.60"),
        bar(t + timedelta(minutes=15), "100.60", "100.80", "100.40", "100.50"),
        bar(t + timedelta(minutes=30), "99.90", "100.10", "99.60", "99.80"),
    )
    assert _active_c2_fvgs(
        c2, side=DemoTradingSetupSide.SHORT
    ) == ((Decimal("100.10"), Decimal("100.50")),)
