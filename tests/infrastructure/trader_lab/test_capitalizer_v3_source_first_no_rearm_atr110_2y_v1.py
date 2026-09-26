from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_no_rearm_atr110_2y_v1 as candidate,
)


def test_no_rearm_atr110_contract_is_frozen() -> None:
    assert candidate.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_NO_REARM_ATR110_2Y_V1"
    )
    assert candidate.FROZEN_ATR_MULTIPLIER == Decimal("1.10")
    assert candidate.ORIGINAL_ATR_MULTIPLIER == Decimal("1.20")
    assert candidate.BASELINE_MAX3 == 793
