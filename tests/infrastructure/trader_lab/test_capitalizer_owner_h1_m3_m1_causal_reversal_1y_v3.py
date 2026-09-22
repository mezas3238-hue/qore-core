from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 import (
    ATR_MULTIPLIER,
    BODY_RATIO_MIN,
    IDENTITY,
    MATRIX_IDENTITY,
    M3MssEvent,
    _h1_hour_bounds,
    _stop_buffer,
)


def _bar(at: datetime, value: str) -> CapitalizerM1Bar:
    price = Decimal(value)
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=at,
        closed_at=at + timedelta(minutes=1),
        open=price,
        high=price,
        low=price,
        close=price,
    )


def test_contract_identity_and_thresholds() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_OWNER_H1_M3_M1_CAUSAL_REVERSAL_1Y_V3"
    assert MATRIX_IDENTITY.endswith("H1_M3_M1_CAUSAL_REVERSAL_1Y_V3")
    assert BODY_RATIO_MIN == Decimal("0.60")
    assert ATR_MULTIPLIER == Decimal("1.2")


def test_same_h1_window_is_exactly_one_hour() -> None:
    moment = datetime(2026, 9, 22, 13, 37, tzinfo=UTC)
    opened, deadline = _h1_hour_bounds(moment)
    assert deadline - opened == timedelta(hours=1)


def test_five_pip_buffer_is_deterministic_from_price_quantum() -> None:
    at = datetime(2026, 9, 22, 13, 0, tzinfo=UTC)
    bars = (
        _bar(at, "1.12345"),
        _bar(at + timedelta(minutes=1), "1.12346"),
    )
    assert _stop_buffer(bars) == Decimal("0.00050")


def test_m3_event_side_is_explicit() -> None:
    at = datetime(2026, 9, 22, 13, 0, tzinfo=UTC)
    event = M3MssEvent(
        side=CapitalizerSide.LONG,
        confirmed_at=at + timedelta(minutes=3),
        displacement_opened_at=at,
        displacement_closed_at=at + timedelta(minutes=3),
        broken_swing_price=Decimal("100"),
        cisd_boundary=Decimal("100.2"),
        body_ratio=Decimal("0.7"),
        atr14=Decimal("1"),
        displacement_range=Decimal("1.3"),
    )
    assert event.side is CapitalizerSide.LONG
