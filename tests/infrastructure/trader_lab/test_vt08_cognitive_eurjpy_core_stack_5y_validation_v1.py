from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_cognitive_eurjpy_core_stack_5y_validation_v1 import (
    MARKET,
    MAX_DD_R,
    MC_MAX_P95_DD_R,
    MC_MIN_POSITIVE,
    MIN_PF,
    MIN_SAMPLE,
    ROLLING_MAX_DD_R,
    ROLLING_MIN_PF,
    ROLLING_MIN_SAMPLE,
)


def test_eurjpy_5y_gates_are_frozen() -> None:
    assert MARKET == "EURJPY"
    assert MIN_SAMPLE == 100
    assert MIN_PF == Decimal("1.50")
    assert MAX_DD_R == Decimal("6")
    assert ROLLING_MIN_SAMPLE == 30
    assert ROLLING_MIN_PF == Decimal("1.20")
    assert ROLLING_MAX_DD_R == Decimal("8")
    assert MC_MIN_POSITIVE == Decimal("0.90")
    assert MC_MAX_P95_DD_R == Decimal("15")
