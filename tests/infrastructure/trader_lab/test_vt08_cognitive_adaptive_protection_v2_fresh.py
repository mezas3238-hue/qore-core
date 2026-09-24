from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_cognitive_adaptive_protection_v2_fresh import (
    MIN_ADAPTIVE_PF,
    MIN_FRESH_TRADES,
)


def test_adaptive_v2_fresh_gates_are_frozen() -> None:
    assert MIN_FRESH_TRADES == 30
    assert MIN_ADAPTIVE_PF == Decimal("1.20")
