from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_m5_mss_m3_refinement_1y_v1 import (
    ENTRY_IDENTITY,
    IDENTITY,
    MATRIX_IDENTITY,
    M5CisdEvent,
    TFBar,
    _find_m5_cisd,
    _significant_tf_displacement,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
)


def _bar(at: datetime, o: str, h: str, low: str, c: str) -> TFBar:
    return TFBar(
        opened_at=at,
        closed_at=at + timedelta(minutes=5),
        source=CapitalizerSourceBar(
            open=Decimal(o),
            high=Decimal(h),
            low=Decimal(low),
            close=Decimal(c),
        ),
    )


def test_contract_is_m5_cisd_mss_then_m3() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_M5_MSS_M3_REFINEMENT_1Y_V1"
    assert MATRIX_IDENTITY.endswith("M5_MSS_M3_REFINEMENT_1Y_MATRIX_V1")
    assert "M5_CISD_MSS" in ENTRY_IDENTITY
    assert "M3_MSS_FVG_CE" in ENTRY_IDENTITY


def test_m5_cisd_confirms_after_opposing_delivery() -> None:
    t0 = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    bars = (
        _bar(t0, "101", "101.2", "99.8", "100"),
        _bar(t0 + timedelta(minutes=5), "100.5", "101.8", "100.2", "101.5"),
    )
    event = _find_m5_cisd(
        bars,
        after=t0 - timedelta(minutes=1),
        before=t0 + timedelta(minutes=20),
        side=CapitalizerSide.LONG,
    )
    assert isinstance(event, M5CisdEvent)
    assert event.boundary == Decimal("101")


def test_m3_displacement_uses_body_dominance_without_fitted_threshold() -> None:
    t0 = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    bar = TFBar(
        opened_at=t0,
        closed_at=t0 + timedelta(minutes=3),
        source=CapitalizerSourceBar(
            open=Decimal("100"),
            high=Decimal("103"),
            low=Decimal("99.8"),
            close=Decimal("102.8"),
        ),
    )
    assert _significant_tf_displacement(bar, side=CapitalizerSide.LONG) is True
