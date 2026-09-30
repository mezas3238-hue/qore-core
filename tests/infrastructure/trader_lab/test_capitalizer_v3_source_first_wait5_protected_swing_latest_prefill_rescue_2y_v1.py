from typing import cast

from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_protected_swing_latest_prefill_rescue_2y_v1 as rescue,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)


def test_latest_prefill_rescue_contract_is_frozen() -> None:
    assert rescue.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_"
        "PROTECTED_SWING_LATEST_PREFILL_RESCUE_2Y_V1"
    )
    assert rescue.EXPECTED_STOP_INVALID == 111
    assert rescue.WAIT5_BASELINE_MAX3 == 983


def test_latest_prefill_stop_hit_is_side_aware() -> None:
    from decimal import Decimal

    class Bar:
        low = Decimal("99")
        high = Decimal("101")

    bar = cast(CapitalizerM1Bar, Bar())
    assert rescue._stop_hit(bar, side="LONG", stop_price=Decimal("99.5")) is True
    assert rescue._stop_hit(bar, side="SHORT", stop_price=Decimal("100.5")) is True
