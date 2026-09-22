from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_owner_h1_m5_m3_1y_v1 import (
    ENTRY_IDENTITY,
    IDENTITY,
    MATRIX_IDENTITY,
    M5CisdEvent,
    StructureEvent,
    _m5_tspot,
    _zone_overlap,
)


def test_owner_contract_identity() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_OWNER_H1_M5_M3_1Y_V1"
    assert MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_OWNER_H1_M5_M3_1Y_MATRIX_V1"
    )
    assert "M5_CISD_MSS_TSPOT" in ENTRY_IDENTITY
    assert "M3_IFVG_OR_CISD" in ENTRY_IDENTITY
    assert "M3_MSS" not in ENTRY_IDENTITY


def test_tspot_is_causal_zone_between_cisd_and_protected_swing() -> None:
    now = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    cisd = M5CisdEvent(confirmed_at=now, boundary=Decimal("101"))
    mss = StructureEvent(
        confirmed_at=now + timedelta(minutes=5),
        break_price=Decimal("102"),
        protected_swing_price=Decimal("99"),
        timeframe="M5",
    )
    assert _m5_tspot(cisd=cisd, mss=mss) == (
        Decimal("99"),
        Decimal("101"),
    )


def test_zone_overlap_is_not_an_extra_gate() -> None:
    assert _zone_overlap(
        Decimal("100"),
        Decimal("102"),
        Decimal("101"),
        Decimal("103"),
    ) == (Decimal("101"), Decimal("102"))
    assert _zone_overlap(
        Decimal("100"),
        Decimal("101"),
        Decimal("102"),
        Decimal("103"),
    ) is None
